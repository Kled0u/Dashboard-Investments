# main.py
import streamlit as st
import pandas as pd
import os
import glob
import numpy as np

# Importer les onglets
from tabs import onglet_investisseurs, onglet_analyse

# --- Vos fonctions 'format_eur', 'load_and_process_all_data', 'apply_fees_and_taxes' ---
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
        st.error(f"Fichier manquant : {e.filename}."); return None, None, None
        
    start_date = df_apports['Date'].min(); end_date = pd.to_datetime('today')
    date_range = pd.date_range(start_date, end_date, freq='D')
    df_global_value = pd.DataFrame(index=date_range)
    
    sources = df_apports['SourcePlacement'].unique()
    df_global_value['PEA'] = df_pea_value['PEA'].reindex(date_range, method='ffill')
    for source in sources:
        if source.upper() != 'PEA':
            apports_source = df_apports[df_apports['SourcePlacement'] == source]
            inflows_source = apports_source.pivot_table(index='Date', values='Montant', aggfunc='sum')['Montant']
            df_global_value[source] = inflows_source.cumsum().reindex(date_range, method='ffill').fillna(0)
    df_global_value.fillna(0, inplace=True)

    df_global_value['PortfolioValue_Global'] = df_global_value[sources].sum(axis=1)
    
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
    return df_final, df_apports, df_global_value

def apply_fees_and_taxes(df_perf, df_apports):
    df_net = df_perf.copy()
    investors = df_apports['NomInvestisseur'].unique().tolist()
    df_net['year'] = df_net['Date'].dt.year
    df_net['day_of_year'] = df_net['Date'].dt.dayofyear
    df_net['days_in_year'] = df_net['Date'].dt.is_leap_year.map({True: 366, False: 365})
    for investor in investors:
        df_net[f'gain_brut_{investor}'] = df_net[f'valeur_part_{investor}'] - df_net[f'capital_{investor}']
        df_net[f'taxe_latente_{investor}'] = df_net[f'gain_brut_{investor}'].clip(lower=0) * 0.30
        df_net[f'valeur_debut_annee_{investor}'] = df_net.groupby('year')[f'valeur_part_{investor}'].transform('first')
        df_net[f'capital_debut_annee_{investor}'] = df_net.groupby('year')[f'capital_{investor}'].transform('first')
        inflows_annee = df_net[f'capital_{investor}'] - df_net[f'capital_debut_annee_{investor}']
        gain_valeur_annee = df_net[f'valeur_part_{investor}'] - df_net[f'valeur_debut_annee_{investor}']
        profit_annee = gain_valeur_annee - inflows_annee
        FEE_RATE = 0.02
        annual_fee_base = profit_annee.clip(lower=0) * FEE_RATE
        df_net[f'frais_gestion_{investor}'] = annual_fee_base * (df_net['day_of_year'] / df_net['days_in_year'])
        df_net[f'valeur_part_nette_{investor}'] = df_net[f'valeur_part_{investor}'] - df_net[f'taxe_latente_{investor}'] - df_net[f'frais_gestion_{investor}']
    cols_to_drop = [col for col in df_net.columns if 'debut_annee' in col]
    df_net.drop(columns=cols_to_drop, inplace=True)
    return df_net

# --- Interface Streamlit ---
st.set_page_config(layout="wide", page_title="Dashboard de Portefeuille")
st.title("Dashboard de Suivi d'Investissements")
st.sidebar.title("Navigation")

selection = st.sidebar.radio(
    "Aller à",
    ["Analyse par Investisseur", "Analyse de Portefeuille"]
)

try:
    gross_data, df_apports, df_global_value = load_and_process_all_data()
    if gross_data is not None and df_apports is not None and df_global_value is not None:
        if selection == "Analyse par Investisseur":
            final_data_net = apply_fees_and_taxes(gross_data, df_apports)
            onglet_investisseurs.display_tab(final_data_net, df_apports)
        
        elif selection == "Analyse de Portefeuille":
            df_portfolio_history = df_global_value.reset_index().rename(columns={'index': 'Date'})
            onglet_analyse.display_tab(df_portfolio_history)

except Exception as e:
    st.error(f"Une erreur critique est survenue lors du chargement ou du traitement des données.")
    st.exception(e)