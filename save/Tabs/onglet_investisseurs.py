# tabs/onglet_investisseurs.py
import streamlit as st
import pandas as pd

def format_eur(val):
    if pd.isna(val) or not isinstance(val, (int, float, complex)):
        return val
    return f"{val:,.2f} €".replace(",", " ").replace(".00", "")

def display_tab(df_perf_net, df_apports):
    """Affiche l'onglet de l'analyse par investisseur avec le détail brut/net."""
    
    # --- CORRECTION ICI ---
    # On récupère la liste des investisseurs directement depuis le fichier d'apports,
    # qui est la source de vérité. C'est plus propre et évite les erreurs.
    investors = sorted(df_apports['NomInvestisseur'].unique().tolist())
    # --- FIN DE LA CORRECTION ---
    
    selected_investor = st.selectbox("Sélectionnez un investisseur", investors)
    
    if selected_investor:
        
        # Extraire les dernières valeurs disponibles
        last_day = df_perf_net.iloc[-1]
        
        capital = last_day[f'capital_{selected_investor}']
        valeur_brute = last_day[f'valeur_part_{selected_investor}']
        frais = last_day[f'frais_gestion_{selected_investor}']
        taxe = last_day[f'taxe_latente_{selected_investor}']
        valeur_nette = last_day[f'valeur_part_nette_{selected_investor}']
        gain_net = valeur_nette - capital

        st.subheader(f"Situation Nette pour {selected_investor}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Apporté", format_eur(capital))
        col2.metric("Valeur Nette Estimée", format_eur(valeur_nette), help="Valeur brute après déduction des frais de gestion et de l'impôt latent estimé.")
        col3.metric("Gain/Perte Net Final", format_eur(gain_net), delta_color="off")
        
        # Détail du calcul
        with st.expander("Voir le détail du calcul de la valeur nette"):
            st.markdown(f"""
            | Description | Montant |
            | :--- | ---: |
            | Valeur Brute de la part | **{format_eur(valeur_brute)}** |
            | Moins: Frais de gestion accumulés | {format_eur(-frais)} |
            | Moins: Impôt latent estimé (30%) | {format_eur(-taxe)} |
            | **Égal: Valeur Nette Estimée** | **{format_eur(valeur_nette)}** |
            """)

        st.subheader("Évolution de la valeur Brute vs Nette")
        
        df_chart = df_perf_net[['Date', f'capital_{selected_investor}', f'valeur_part_{selected_investor}', f'valeur_part_nette_{selected_investor}']].copy()
        df_chart.rename(columns={
            f'capital_{selected_investor}': 'Total Apporté',
            f'valeur_part_{selected_investor}': 'Valeur Brute',
            f'valeur_part_nette_{selected_investor}': 'Valeur Nette'
        }, inplace=True)
        
        st.line_chart(df_chart.set_index('Date'))
        
        with st.expander("Voir le détail des apports"):
            st.dataframe(df_apports[df_apports['NomInvestisseur'] == selected_investor])