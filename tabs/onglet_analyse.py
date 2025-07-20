# tabs/onglet_analyse.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import glob

def get_latest_positions_file(directory="data/Positions"):
    """Trouve le fichier de positions le plus récent dans le dossier spécifié."""
    try:
        mois_map = {
            'janvier': 1, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
            'juillet': 7, 'aout': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12
        }
        list_of_files = glob.glob(os.path.join(directory, '*.csv'))
        if not list_of_files: return None
        
        latest_file = None
        latest_date = datetime.min
        
        for file_path in list_of_files:
            try:
                file_name = os.path.basename(file_path)
                mois_str, annee_str = file_name.replace('.csv', '').split('_')
                file_date = datetime(int(annee_str), mois_map[mois_str.lower()], 1)
                if file_date > latest_date:
                    latest_date, latest_file = file_date, file_path
            except (ValueError, KeyError):
                continue
        return latest_file
    except Exception:
        return None

def display_tab():
    """Affiche la composition du portefeuille à partir du dernier fichier CSV."""
    
    st.header("Composition Actuelle du Portefeuille")
    
    positions_file = get_latest_positions_file()
    
    if positions_file:
        st.info(f"Fichier de positions chargé : `{os.path.basename(positions_file)}`")
        try:
            # --- LA CORRECTION EST ICI ---
            # On ajoute 'decimal=',' pour que pandas comprenne les nombres avec des virgules.
            df_positions = pd.read_csv(
                positions_file, 
                delimiter=';', 
                encoding='utf-8-sig',
                decimal=',' 
            )
            # ---------------------------

            df_positions.columns = df_positions.columns.str.strip()

            col_nom = 'name'
            col_quantite = 'quantity'
            col_prix = 'lastPrice'
            
            # Calcul de la valeur de chaque position
            df_positions['Valeur'] = df_positions[col_quantite] * df_positions[col_prix]
            
            total_value = df_positions['Valeur'].sum()
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Valeur Totale du Portefeuille", f"{total_value:,.2f} €".replace(",", " "))
                st.dataframe(df_positions[[col_nom, 'Valeur']].rename(columns={col_nom: 'Action'}).style.format({'Valeur': '{:,.2f} €'}), hide_index=True)
            with col2:
                fig_pie = px.pie(
                    df_positions,
                    names=col_nom,
                    values='Valeur',
                    title='Poids de chaque action dans le portefeuille'
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

        except Exception as e:
            st.error(f"Une erreur est survenue lors du traitement du fichier : {e}")
            st.info("Veuillez vérifier que les colonnes 'quantity' et 'lastPrice' ne contiennent que des nombres (avec une virgule comme séparateur décimal si besoin).")

    else:
        st.error("Aucun fichier de positions trouvé dans `data/Positions/`. Vérifiez le nommage (ex: 'Juillet_2025.csv').")