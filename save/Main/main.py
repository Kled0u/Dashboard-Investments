# main.py
import streamlit as st
import pandas as pd
import os
import glob
import numpy as np

# Importer l'onglet
from tabs import onglet_investisseurs

# --- Fonctions de formatage et de calcul ---
def format_eur(val):
    if pd.isna(val) or not isinstance(val, (int, float, complex)): return val
    return f"{val:,.2f} €".replace(",", " ").replace(".00", "")

@st.cache_data
def load_and_process_all_data():
    try:
        apports_file = 'data/apports_investisseurs.xlsx'
        df_apports = pd.read_excel(apports_file); df_apports.columns = ['Date', 'NomInvestisseur', 'Montant', 'SourcePlacement']
        df_apports['Date'] = pd.to_datetime(df_apports['Date'])
        investors = df_apports['NomInvestisseur'].unique().tolist()
        pea_perf_file = 'data/performance_pea.xlsx'
        df_pea_value = pd.read_excel(pea_perf_file, usecols=[0, 1]); df_pea_value.columns = ['Date', 'PEA']
        df_pea_value['Date'] = pd.to_datetime(df_pea_value['Date']); df_pea_value.set_index('Date', inplace=True)
    except FileNotFoundError as e:
        st.error(f"Fichier manquant : {e.filename}."); return None, None

    start_date = df_apports['Date'].min(); end_date = pd.to_datetime('today')
    date_range = pd.date_range(start_date, end_date, freq='D')
    df_global_value = pd.DataFrame(index=date_range); df_global_value['PEA'] = df_pea_value['PEA'].reindex(date_range, method='ffill')
    sources = df_apports['SourcePlacement'].unique()
    for source in sources:
        if source.upper() != 'PEA':
            apports_source = df_apports[df_apports['SourcePlacement'] == source]
            inflows_source = apports_source.pivot_table(index='Date', values='Montant', aggfunc='sum')['Montant']
            df_global_value[source] = inflows_source.cumsum().reindex(date_range, method='ffill').fillna(0)
    df_global_value.fillna(0, inplace=True); df_global_value['PortfolioValue_Global'] = df_global_value[sources].sum(axis=1)
    df_final = df_global_value[['PortfolioValue_Global']].copy()
    daily_inflows_total = df_apports.pivot_table(index='Date', columns='NomInvestisseur', values='Montant', aggfunc='sum')
    df_final = df_final.join(daily_inflows_total).fillna(0)
    df_final['NAV_per_Unit'] = 1.0; df_final['Total_Units'] = 0.0
    for investor in investors:
        df_final[f'units_{investor}'] = 0.0; df_final[f'capital_{investor}'] = df_final[investor].cumsum()
    for i in range(len(df_final)):
        nav_yesterday = df_final.iloc[i-1]['NAV_per_Unit'] if i > 0 else 1.0
        units_yesterday = df_final.iloc[i-1]['Total_Units'] if i > 0 else 0
        new_units_today = 0
        for investor in investors:
            inflow_today = df_final.iloc[i][investor]
            new_units = inflow_today / nav_yesterday if nav_yesterday > 0 else inflow_today
            df_final.iloc[i, df_final.columns.get_loc(f'units_{investor}')] = (df_final.iloc[i-1][f'units_{investor}'] if i > 0 else 0) + new_units
            new_units_today += new_units
        total_units_today = units_yesterday + new_units_today
        df_final.iloc[i, df_final.columns.get_loc('Total_Units')] = total_units_today
        if total_units_today > 0:
            df_final.iloc[i, df_final.columns.get_loc('NAV_per_Unit')] = df_final.iloc[i]['PortfolioValue_Global'] / total_units_today
        elif i > 0:
             df_final.iloc[i, df_final.columns.get_loc('NAV_per_Unit')] = nav_yesterday
    for investor in investors:
        df_final[f'valeur_part_{investor}'] = df_final[f'units_{investor}'] * df_final['NAV_per_Unit']
    df_final.reset_index(inplace=True); df_final.rename(columns={'index':'Date'}, inplace=True)
    return df_final, df_apports

def apply_fees_and_taxes(df_perf, df_apports):
    """
    Applique les frais de gestion et l'impôt avec la logique de bénéfice annuel corrigée.
    """
    df_net = df_perf.copy()
    investors = df_apports['NomInvestisseur'].unique().tolist()

    df_net['year'] = df_net['Date'].dt.year
    df_net['day_of_year'] = df_net['Date'].dt.dayofyear
    df_net['days_in_year'] = df_net['Date'].dt.is_leap_year.map({True: 366, False: 365})
    
    for investor in investors:
        df_net[f'gain_brut_{investor}'] = df_net[f'valeur_part_{investor}'] - df_net[f'capital_{investor}']
        df_net[f'taxe_latente_{investor}'] = df_net[f'gain_brut_{investor}'].clip(lower=0) * 0.30

        # --- CORRECTION FINALE DE LA LOGIQUE DES FRAIS DE GESTION ---
        
        # 1. Obtenir les valeurs de début d'année pour le capital et la part
        df_net[f'valeur_debut_annee_{investor}'] = df_net.groupby('year')[f'valeur_part_{investor}'].transform('first')
        df_net[f'capital_debut_annee_{investor}'] = df_net.groupby('year')[f'capital_{investor}'].transform('first')
        
        # 2. Calculer les apports durant l'année
        inflows_annee = df_net[f'capital_{investor}'] - df_net[f'capital_debut_annee_{investor}']
        
        # 3. Calculer la variation de valeur de la part durant l'année
        gain_valeur_annee = df_net[f'valeur_part_{investor}'] - df_net[f'valeur_debut_annee_{investor}']
        
        # 4. Le vrai bénéfice de l'année = Variation de valeur MOINS les nouveaux apports
        profit_annee = gain_valeur_annee - inflows_annee
        
        # 5. Appliquer la condition sur ce bénéfice corrigé
        annual_fee_base = np.where(
            profit_annee > 0,                     # Condition: y a-t-il un vrai bénéfice cette année?
            profit_annee * 0.02,                  # Si oui: 2% du bénéfice
            df_net[f'capital_{investor}'] * 0.02  # Si non: 2% du capital total
        )
        
        # 6. Proratiser les frais annuels au jour le jour
        df_net[f'frais_gestion_{investor}'] = annual_fee_base * (df_net['day_of_year'] / df_net['days_in_year'])
        # --- FIN DE LA MODIFICATION ---

        # Calcul de la valeur nette finale
        df_net[f'valeur_part_nette_{investor}'] = df_net[f'valeur_part_{investor}'] - df_net[f'taxe_latente_{investor}'] - df_net[f'frais_gestion_{investor}']

    return df_net

# --- Interface Streamlit ---
st.set_page_config(layout="wide", page_title="Dashboard de Portefeuille")
st.title("Dashboard de Suivi d'Investissements")
try:
    gross_data, df_apports = load_and_process_all_data()
    if gross_data is not None:
        final_data = apply_fees_and_taxes(gross_data, df_apports)
        st.header("Analyse par Investisseur (Après Frais et Impôts)")
        onglet_investisseurs.display_tab(final_data, df_apports)
except Exception as e:
    st.error(f"Une erreur critique est survenue."); st.exception(e)