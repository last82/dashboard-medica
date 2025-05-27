import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ========================
# CONFIGURAZIONE PAGINA
# ========================
st.set_page_config(
    page_title="🏥 Dashboard Medica - Multi Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# SUPABASE CONNECTION
# ========================
@st.cache_resource
def init_supabase():
    SUPABASE_URL = "https://ruvibhbknamrqttwrzqm.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1dmliaGJrbmFtcnF0dHdyenFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzMzQ0NjYsImV4cCI6MjA2MzkxMDQ2Nn0.Eh_ccS35jzf77NRxewk2axWyU1uwJITNCfti88wLAug"
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        st.error(f"❌ Errore connessione: {e}")
        return None

@st.cache_data(ttl=300)
def load_medical_data():
    supabase = init_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table('medical_data').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['data_operazione'] = pd.to_datetime(df['data_operazione'])
            df['anno'] = df['data_operazione'].dt.year
            df['mese'] = df['data_operazione'].dt.month
            df['mese_nome'] = df['data_operazione'].dt.strftime('%B')
            df['anno_mese'] = df['data_operazione'].dt.strftime('%Y-%m')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Errore caricamento: {e}")
        return pd.DataFrame()

# ========================
# CUSTOM CSS
# ========================
def apply_custom_css():
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    
    .pivot-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0px 24px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px 15px 0 0;
        font-weight: bold;
        font-size: 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    </style>
    """, unsafe_allow_html=True)

# ========================
# SIDEBAR FILTRI GLOBALI
# ========================
def create_global_filters(df):
    st.sidebar.header("🎛️ Filtri Globali")
    
    if df.empty:
        return df, []
    
    # Filtro anni
    available_years = sorted(df['anno'].unique(), reverse=True)
    current_year = datetime.now().year
    default_years = [y for y in available_years if y >= current_year - 3]  # Ultimi 4 anni
    
    selected_years = st.sidebar.multiselect(
        "📅 Seleziona Anni",
        options=available_years,
        default=default_years if default_years else available_years[-4:]
    )
    
    # Filtro operatori
    operators = ['Tutti'] + sorted(df['operatore'].unique().tolist())
    selected_operator = st.sidebar.selectbox("👨‍⚕️ Operatore", operators)
    
    # Applica filtri
    df_filtered = df[df['anno'].isin(selected_years)] if selected_years else df
    
    if selected_operator != 'Tutti':
        df_filtered = df_filtered[df_filtered['operatore'] == selected_operator]
    
    # Info dataset
    st.sidebar.markdown("---")
    st.sidebar.markdown("📊 **Dataset Info**")
    st.sidebar.metric("Record totali", len(df))
    st.sidebar.metric("Record filtrati", len(df_filtered))
    
    return df_filtered, selected_years

# ========================
# TAB 1: ANALISI ESEGUITO
# ========================
def create_eseguito_analysis(df, selected_years):
    st.header("💰 Analisi Fatturato Eseguito")
    
    # Filtra solo operazioni eseguite
    df_eseguito = df[df['status_operazione'] == 'ESEGUITA'].copy()
    
    if df_eseguito.empty:
        st.warning("⚠️ Nessuna operazione eseguita trovata")
        return
    
    # Metriche summary
    col1, col2, col3, col4 = st.columns(4)
    
    total_eseguito = df_eseguito['importo_scontato'].sum()
    ops_eseguite = len(df_eseguito)
    media_per_op = total_eseguito / ops_eseguite if ops_eseguite > 0 else 0
    anni_analizzati = len(df_eseguito['anno'].unique())
    
    with col1:
        st.metric("💰 Fatturato Eseguito", f"€{total_eseguito:,.0f}")
    with col2:
        st.metric("✅ Operazioni Eseguite", f"{ops_eseguite:,}")
    with col3:
        st.metric("📊 Media per Operazione", f"€{media_per_op:.0f}")
    with col4:
        st.metric("📅 Anni Analizzati", anni_analizzati)
    
    st.markdown("---")
    
    # Layout affiancato: Pivot + Grafici
    col_left, col_right = st.columns([1, 1])
    
    # ========================
    # PIVOT TABLE 1: VALORI MENSILI
    # ========================
    with col_left:
        st.subheader("📊 Pivot: Fatturato Mensile")
        
        # Crea pivot mensile
        df_eseguito['mese_num'] = df_eseguito['data_operazione'].dt.month
        df_eseguito['mese_nome'] = df_eseguito['data_operazione'].dt.strftime('%m-%b')
        
        pivot_mensile = df_eseguito.pivot_table(
            index='mese_nome',
            columns='anno',
            values='importo_scontato',
            aggfunc='sum',
            fill_value=0
        )
        
        # Ordina per mese
        mesi_ordinati = [f"{i:02d}-{pd.to_datetime(f'2024-{i:02d}-01').strftime('%b')}" 
                        for i in range(1, 13)]
        pivot_mensile = pivot_mensile.reindex(mesi_ordinati, fill_value=0)
        
        # Formatta per visualizzazione
        pivot_display = pivot_mensile.copy()
        for col in pivot_display.columns:
            pivot_display[col] = pivot_display[col].apply(lambda x: f"€{x:,.0f}" if x > 0 else "€0")
        
        st.dataframe(
            pivot_display,
            use_container_width=True,
            height=400
        )
        
        # Export CSV
        csv_mensile = pivot_mensile.to_csv()
        st.download_button(
            "📥 Download Pivot Mensile",
            csv_mensile,
            "fatturato_mensile.csv",
            "text/csv"
        )
    
    # ========================
    # GRAFICO 1: LINEE MENSILI
    # ========================
    with col_right:
        st.subheader("📈 Trend Mensile per Anno")
        
        # Prepara dati per grafico
        fig_mensile = go.Figure()
        
        colors = ['#667eea', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4']
        
        for i, anno in enumerate(sorted(pivot_mensile.columns)):
            fig_mensile.add_trace(go.Scatter(
                x=pivot_mensile.index,
                y=pivot_mensile[anno],
                mode='lines+markers',
                name=f'Anno {anno}',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8),
                hovertemplate=f'<b>Anno {anno}</b><br>' +
                             'Mese: %{x}<br>' +
                             'Fatturato: €%{y:,.0f}<extra></extra>'
            ))
        
        fig_mensile.update_layout(
            title="Confronto Fatturato Mensile",
            xaxis_title="Mese",
            yaxis_title="Fatturato (€)",
            height=400,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_mensile, use_container_width=True)
    
    st.markdown("---")
    
    # ========================
    # SECONDA RIGA: RUNNING TOTALS
    # ========================
    col_left2, col_right2 = st.columns([1, 1])
    
    # ========================
    # PIVOT TABLE 2: RUNNING TOTALS
    # ========================
    with col_left2:
        st.subheader("📊 Pivot: Running Totals")
        
        # Calcola running totals
        pivot_running = pivot_mensile.cumsum()
        
        # Formatta per visualizzazione
        pivot_running_display = pivot_running.copy()
        for col in pivot_running_display.columns:
            pivot_running_display[col] = pivot_running_display[col].apply(lambda x: f"€{x:,.0f}" if x > 0 else "€0")
        
        st.dataframe(
            pivot_running_display,
            use_container_width=True,
            height=400
        )
        
        # Export CSV
        csv_running = pivot_running.to_csv()
        st.download_button(
            "📥 Download Running Totals",
            csv_running,
            "running_totals.csv",
            "text/csv"
        )
    
    # ========================
    # GRAFICO 2: LINEE RUNNING TOTALS
    # ========================
    with col_right2:
        st.subheader("📈 Running Totals per Anno")
        
        fig_running = go.Figure()
        
        for i, anno in enumerate(sorted(pivot_running.columns)):
            fig_running.add_trace(go.Scatter(
                x=pivot_running.index,
                y=pivot_running[anno],
                mode='lines+markers',
                name=f'Anno {anno}',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8),
                fill='tonexty' if i > 0 else None,
                hovertemplate=f'<b>Anno {anno}</b><br>' +
                             'Mese: %{x}<br>' +
                             'Running Total: €%{y:,.0f}<extra></extra>'
            ))
        
        fig_running.update_layout(
            title="Running Totals Confronto",
            xaxis_title="Mese",
            yaxis_title="Running Total (€)",
            height=400,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_running, use_container_width=True)

# ========================
# TAB 2: ANALISI GENERALE (PLACEHOLDER)
# ========================
def create_general_analysis(df):
    st.header("📊 Analisi Generale")
    st.info("🚧 Sezione in sviluppo - Aggiungeremo altre analisi qui")
    
    # Placeholder per altre analisi
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance Operatori")
        if not df.empty:
            ops_perf = df.groupby('operatore')['importo_scontato'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=ops_perf.values,
                y=ops_perf.index,
                orientation='h',
                title="Fatturato per Operatore"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Status Operazioni")
        if not df.empty:
            status_counts = df['status_operazione'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Distribuzione Status"
            )
            st.plotly_chart(fig, use_container_width=True)

# ========================
# TAB 3: ANALISI OPERAZIONI (PLACEHOLDER)
# ========================
def create_operations_analysis(df):
    st.header("🦷 Analisi Operazioni")
    st.info("🚧 Sezione in sviluppo - Analisi dettagliate operazioni")
    
    if not df.empty:
        st.subheader("🔝 Top 10 Operazioni più Frequenti")
        top_ops = df['operazione'].value_counts().head(10)
        
        fig = px.bar(
            x=top_ops.values,
            y=top_ops.index,
            orientation='h',
            title="Operazioni più Eseguite"
        )
        st.plotly_chart(fig, use_container_width=True)

# ========================
# MAIN APP
# ========================
def main():
    # CSS personalizzato
    apply_custom_css()
    
    # Header principale
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                color: white; border-radius: 15px; margin-bottom: 2rem;">
        <h1 style="margin: 0; font-size: 3rem;">🏥 Dashboard Medica Multi-Analysis</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Replica Google Sheet con Pivot Tables e Grafici Interattivi
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carica dati
    with st.spinner("🔄 Caricamento dati da Supabase..."):
        df = load_medical_data()
    
    if df.empty:
        st.error("❌ Nessun dato trovato. Verifica la connessione a Supabase.")
        st.stop()
    
    # Filtri globali
    df_filtered, selected_years = create_global_filters(df)
    
    # Refresh button
    if st.sidebar.button("🔄 Aggiorna Dati"):
        st.cache_data.clear()
        st.rerun()
    
    # ========================
    # TABS PRINCIPALI
    # ========================
    tab1, tab2, tab3 = st.tabs([
        "💰 Analisi Eseguito", 
        "📊 Analisi Generale", 
        "🦷 Analisi Operazioni"
    ])
    
    with tab1:
        create_eseguito_analysis(df_filtered, selected_years)
    
    with tab2:
        create_general_analysis(df_filtered)
    
    with tab3:
        create_operations_analysis(df_filtered)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🔒 Dashboard sicura e anonima • ☁️ Powered by Streamlit & Supabase</p>
        <p>📊 Aggiornamento automatico ogni 5 minuti • 🎯 Replica fedele Google Sheet</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
