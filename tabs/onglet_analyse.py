# tabs/onglet_analyse.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob

def get_latest_positions_file(directory="data/Positions"):
    """Trouve le fichier de positions le plus récent dans le dossier spécifié."""
    try:
        list_of_files = glob.glob(os.path.join(directory, '*.csv'))
        if not list_of_files: return None
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception:
        return None

def display_tab(df_portfolio_history):
    """
    Affiche l'analyse globale du portefeuille avec le détail des positions.
    """
    st.header("Analyse Globale du Portefeuille")

    last_day_data = df_portfolio_history.iloc[-1]
    
    asset_columns = [
        col for col in df_portfolio_history.columns 
        if col not in ['Date', 'PortfolioValue_Global']
    ]
    
    st.subheader("Situation Actuelle")
    
    valeur_pea_total = last_day_data.get('PEA', 0)
    valeur_actions_investies = 0
    df_positions = None
    liquidite_pea = 0
    
    positions_file = get_latest_positions_file()
    if positions_file:
        try:
            df_positions = pd.read_csv(positions_file, delimiter=';', encoding='utf-8-sig', decimal=',')
            df_positions.columns = [col.strip() for col in df_positions.columns]
            df_positions['quantity'] = pd.to_numeric(df_positions['quantity'])
            df_positions['lastPrice'] = pd.to_numeric(df_positions['lastPrice'])
            df_positions['Valeur'] = df_positions['quantity'] * df_positions['lastPrice']
            valeur_actions_investies = df_positions['Valeur'].sum()
        except Exception:
            df_positions = None

    liquidite_pea = valeur_pea_total - valeur_actions_investies
    liquidite_pea = max(0, liquidite_pea)

    kpi_cols = st.columns(len(asset_columns) + 2)
    kpi_cols[0].metric("Valeur Totale", f"{last_day_data['PortfolioValue_Global']:,.2f} €".replace(",", " "))
    for i, asset in enumerate(asset_columns):
        kpi_cols[i+1].metric(f"Part {asset}", f"{last_day_data[asset]:,.2f} €".replace(",", " "))
    kpi_cols[len(asset_columns) + 1].metric("Liquidité (Cash PEA)", f"{liquidite_pea:,.2f} €".replace(",", " "), help="Valeur totale du PEA moins la valeur des actions détenues.")

    st.subheader("Évolution par Classe d'Actifs")
    fig_area = px.area(
        df_portfolio_history, x='Date', y=asset_columns,
        title="Historique de la Valeur par Classe d'Actifs"
    )
    st.plotly_chart(fig_area, use_container_width=True)

    st.subheader("Répartition Détaillée des Actifs Actuels")
    asset_data = []

    if df_positions is not None:
        for index, row in df_positions.iterrows():
            asset_data.append({'Actif': row['name'], 'Type': 'Action PEA', 'Valeur': row['Valeur']})

    if liquidite_pea > 0.01:
        asset_data.append({'Actif': 'Liquidité (Cash PEA)', 'Type': 'Cash', 'Valeur': liquidite_pea})

    for asset in asset_columns:
        if asset != 'PEA':
             asset_data.append({'Actif': asset, 'Type': 'Autre', 'Valeur': last_day_data[asset]})

    if asset_data:
        df_assets = pd.DataFrame(asset_data).dropna(subset=['Valeur'])
        df_assets = df_assets[df_assets['Valeur'].abs() > 0.01]
        df_assets = df_assets.sort_values('Valeur', ascending=False)

        # --- LIGNES MODIFIÉES ---
        fig_bar = px.bar(
            df_assets, 
            x='Actif', 
            y='Valeur',
            title='Détail de la Valeur Actuelle par Actif',
            text_auto='.2s', 
            color='Valeur', # La couleur est maintenant basée sur la valeur de la barre
            color_continuous_scale='Blues' # Utilisation d'un dégradé de bleu
        )
        fig_bar.update_traces(textposition='outside')
        # On cache l'échelle de couleur qui apparaît avec un dégradé
        fig_bar.update_layout(coloraxis_showscale=False) 
        # --------------------
        
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Aucune donnée d'actif disponible pour afficher la répartition.")