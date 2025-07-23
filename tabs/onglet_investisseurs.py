# tabs/onglet_investisseurs.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def format_eur(val):
    if pd.isna(val) or not isinstance(val, (int, float, complex)): return val
    return f"{val:,.2f} €".replace(",", " ").replace(".00", "")

def display_tab(df_perf, df_apports):
    """
    Affiche l'analyse détaillée pour un investisseur sélectionné.
    """
    st.header("Analyse par Investisseur")

    # --- Sélection de l'investisseur ---
    investors = sorted(df_apports['NomInvestisseur'].unique().tolist())
    selected_investor = st.selectbox('Sélectionnez un investisseur :', investors)

    if selected_investor:
        # --- Préparation des noms de colonnes ---
        capital_col = f'capital_{selected_investor}'
        gain_brut_col = f'gain_brut_{selected_investor}'
        valeur_brute_col = f'valeur_part_{selected_investor}'
        valeur_nette_col = f'valeur_part_nette_{selected_investor}'
        frais_col = f'frais_gestion_{selected_investor}'
        taxe_col = f'taxe_latente_{selected_investor}'
        
        # --- Données du dernier jour ---
        last_day_data = df_perf.iloc[-1]
        capital = last_day_data[capital_col]
        gain_brut = last_day_data[gain_brut_col]
        gain_net = last_day_data[valeur_nette_col] - capital
        
        # Calculs des pourcentages pour les KPIs
        gain_brut_perc = (gain_brut / capital) * 100 if capital > 0 else 0
        gain_net_perc = (gain_net / capital) * 100 if capital > 0 else 0

        # --- KPIs de la situation actuelle (AVEC COULEURS) ---
        st.subheader(f"Situation Actuelle pour {selected_investor}")
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Capital Apporté", format_eur(capital))
        kpi2.metric("Valeur Brute", format_eur(last_day_data[valeur_brute_col]))
        kpi3.metric("Gain Brut", format_eur(gain_brut))

        # KPI pour Gain Brut en % avec couleur
        color_brut = 'green' if gain_brut_perc >= 0 else 'red'
        kpi4.markdown(f'**Gain Brut (%)**<p style="color:{color_brut}; font-size: 1.75rem; font-weight: 600;">{gain_brut_perc:.2f} %</p>', unsafe_allow_html=True)
        
        # KPI pour Gain Net en % avec couleur
        color_net = 'green' if gain_net_perc >= 0 else 'red'
        kpi5.markdown(f'**Gain Net Estimé (%)**<p style="color:{color_net}; font-size: 1.75rem; font-weight: 600;">{gain_net_perc:.2f} %</p>', unsafe_allow_html=True)
        
        # --- Détail du calcul Net ---
        with st.expander("Voir le détail du calcul de la performance nette"):
            st.markdown(f"""
            | Description | Montant |
            | :--- | ---: |
            | Valeur Brute de la part | **{format_eur(last_day_data[valeur_brute_col])}** |
            | Moins : Frais de gestion accumulés | {format_eur(-last_day_data[frais_col])} |
            | Moins : Impôt latent estimé (30%) | {format_eur(-last_day_data[taxe_col])} |
            | **Égal : Valeur Nette Estimée** | **{format_eur(last_day_data[valeur_nette_col])}** |
            | | |
            | Moins : Capital Total Apporté | {format_eur(-capital)} |
            | **Égal : Gain Net Estimé** | **{format_eur(gain_net)}** |
            """)

        st.markdown("---")

        # --- GRAPHIQUE DE PERFORMANCE EN % (NETTE) ---
        st.subheader("Performance Nette en Pourcentage du Capital Apporté")

        gain_net_col = f'gain_net_{selected_investor}'
        perc_net_gain_col = f'perc_net_gain_{selected_investor}'
        df_perf[gain_net_col] = df_perf[valeur_nette_col] - df_perf[capital_col]
        df_perf.loc[df_perf[capital_col] > 0, perc_net_gain_col] = (df_perf[gain_net_col] / df_perf[capital_col]) * 100
        df_perf[perc_net_gain_col] = df_perf[perc_net_gain_col].fillna(0)
        
        df_perf['gain_area'] = df_perf[perc_net_gain_col].where(df_perf[perc_net_gain_col] >= 0)
        df_perf['loss_area'] = df_perf[perc_net_gain_col].where(df_perf[perc_net_gain_col] < 0)

        fig_perc = go.Figure()
        fig_perc.add_trace(go.Scatter(
            x=df_perf['Date'], y=df_perf['gain_area'], fill='tozeroy', mode='none',
            fillcolor='rgba(40, 167, 69, 0.3)', name='Gain Net'
        ))
        fig_perc.add_trace(go.Scatter(
            x=df_perf['Date'], y=df_perf['loss_area'], fill='tozeroy', mode='none',
            fillcolor='rgba(220, 53, 69, 0.3)', name='Perte Nette'
        ))
        fig_perc.add_trace(go.Scatter(
            x=df_perf['Date'], y=df_perf[perc_net_gain_col], mode='lines',
            line=dict(color='black', width=2), name='Performance Nette (%)'
        ))
        fig_perc.update_layout(
            title_text=f"Évolution de la Plus-Value Nette en % du Capital pour {selected_investor}",
            yaxis_title="Plus-Value Nette (%)", yaxis_tickformat=".2f", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_perc.add_hline(y=0, line_dash="dash", line_color="grey")
        st.plotly_chart(fig_perc, use_container_width=True)

        st.markdown("---")

        # --- GRAPHIQUE DE PERFORMANCE EN VALEUR ---
        st.subheader("Performance en Valeur Absolue")
        fig_abs = px.line(
            df_perf, x='Date', y=[capital_col, valeur_brute_col],
            title=f"Évolution du Capital Apporté vs. Valeur Brute pour {selected_investor}",
            labels={'value': 'Montant en €', 'variable': 'Légende'}
        )
        fig_abs.for_each_trace(lambda t: t.update(name=t.name.replace(capital_col, 'Capital Apporté')))
        fig_abs.for_each_trace(lambda t: t.update(name=t.name.replace(valeur_brute_col, 'Valeur Brute')))
        st.plotly_chart(fig_abs, use_container_width=True)

        with st.expander("Voir le détail des apports"):
            st.dataframe(df_apports[df_apports['NomInvestisseur'] == selected_investor])