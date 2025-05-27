import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from supabase import create_client, Client
import warnings
warnings.filterwarnings('ignore')

# ========================
# CONFIGURAZIONE PAGINA
# ========================
st.set_page_config(
    page_title="🏥 Dashboard Medica Interattiva",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# SUPABASE CONNECTION
# ========================
@st.cache_resource
def init_supabase():
    """Connessione Supabase"""
    SUPABASE_URL = "https://ruvibhbknamrqttwrzqm.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1dmliaGJrbmFtcnF0dHdyenFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzMzQ0NjYsImV4cCI6MjA2MzkxMDQ2Nn0.Eh_ccS35jzf77NRxewk2axWyU1uwJITNCfti88wLAug"
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        st.error(f"❌ Errore connessione Supabase: {e}")
        return None

@st.cache_data(ttl=300)  # Cache 5 minuti
def load_medical_data():
    """Carica tutti i dati medici"""
    supabase = init_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table('medical_data').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Conversioni
            df['data_operazione'] = pd.to_datetime(df['data_operazione'])
            df['uploaded_at'] = pd.to_datetime(df['uploaded_at'])
            # Colonne aggiuntive per analisi
            df['mese'] = df['data_operazione'].dt.strftime('%Y-%m')
            df['anno'] = df['data_operazione'].dt.year
            df['trimestre'] = df['data_operazione'].dt.quarter
            df['giorno_settimana'] = df['data_operazione'].dt.day_name()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Errore caricamento dati: {e}")
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
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .dashboard-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# ========================
# SIDEBAR FILTRI
# ========================
def create_sidebar_filters(df):
    """Crea filtri interattivi nella sidebar"""
    st.sidebar.header("🎛️ Filtri Interattivi")
    
    if df.empty:
        st.sidebar.warning("Nessun dato per filtri")
        return df
    
    # Filtro data
    st.sidebar.subheader("📅 Periodo")
    date_range = st.sidebar.date_input(
        "Seleziona range date",
        value=(df['data_operazione'].min().date(), df['data_operazione'].max().date()),
        min_value=df['data_operazione'].min().date(),
        max_value=df['data_operazione'].max().date()
    )
    
    if len(date_range) == 2:
        df = df[
            (df['data_operazione'].dt.date >= date_range[0]) &
            (df['data_operazione'].dt.date <= date_range[1])
        ]
    
    # Filtro operatori
    st.sidebar.subheader("👨‍⚕️ Operatori")
    all_operators = df['operatore'].unique().tolist()
    selected_operators = st.sidebar.multiselect(
        "Seleziona operatori",
        options=all_operators,
        default=all_operators
    )
    df = df[df['operatore'].isin(selected_operators)]
    
    # Filtro status
    st.sidebar.subheader("🎯 Status")
    status_filter = st.sidebar.radio(
        "Filtra per status",
        options=['Tutte', 'Solo Eseguite', 'Solo Non Eseguite']
    )
    
    if status_filter == 'Solo Eseguite':
        df = df[df['status_operazione'] == 'ESEGUITA']
    elif status_filter == 'Solo Non Eseguite':
        df = df[df['status_operazione'] == 'NON ESEGUITA']
    
    # Filtro importo
    st.sidebar.subheader("💰 Importo")
    min_importo, max_importo = st.sidebar.slider(
        "Range importo (€)",
        min_value=0,
        max_value=int(df['importo_scontato'].max()) if not df.empty else 1000,
        value=(0, int(df['importo_scontato'].max()) if not df.empty else 1000)
    )
    df = df[(df['importo_scontato'] >= min_importo) & (df['importo_scontato'] <= max_importo)]
    
    # Info dataset filtrato
    st.sidebar.markdown("---")
    st.sidebar.markdown("📊 **Info Dataset Filtrato**")
    st.sidebar.metric("Record mostrati", len(df))
    if not df.empty:
        st.sidebar.metric("Periodo effettivo", 
                         f"{df['data_operazione'].min().strftime('%d/%m/%Y')} - {df['data_operazione'].max().strftime('%d/%m/%Y')}")
    
    # Pulsante refresh
    if st.sidebar.button("🔄 Aggiorna Dati"):
        st.cache_data.clear()
        st.rerun()
    
    return df

# ========================
# KPI CARDS
# ========================
def show_kpi_cards(df):
    """Mostra KPI principali"""
    if df.empty:
        st.warning("⚠️ Nessun dato disponibile per i KPI")
        return
    
    # Calcola KPI
    total_ops = len(df)
    completed_ops = len(df[df['status_operazione'] == 'ESEGUITA'])
    completion_rate = (completed_ops / total_ops * 100) if total_ops > 0 else 0
    total_revenue = df['importo_scontato'].sum()
    unique_patients = df['patient_id'].nunique()
    
    # Layout a 4 colonne
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏥 Operazioni Totali",
            value=f"{total_ops:,}",
            delta=f"+{total_ops}" if total_ops > 0 else None
        )
    
    with col2:
        st.metric(
            label="✅ Tasso Completamento",
            value=f"{completion_rate:.1f}%",
            delta=f"{completed_ops}/{total_ops}"
        )
    
    with col3:
        st.metric(
            label="💰 Fatturato Totale",
            value=f"€{total_revenue:,.0f}",
            delta=f"€{total_revenue/total_ops:.0f} media" if total_ops > 0 else None
        )
    
    with col4:
        st.metric(
            label="👥 Pazienti Unici",
            value=f"{unique_patients:,}",
            delta=f"{total_ops/unique_patients:.1f} op/paziente" if unique_patients > 0 else None
        )

# ========================
# GRAFICI
# ========================
def create_timeline_chart(df):
    """Timeline operazioni e fatturato"""
    if df.empty:
        return
    
    # Raggruppa per mese
    df_monthly = df.groupby('mese').agg({
        'id': 'count',
        'importo_scontato': 'sum'
    }).reset_index()
    
    # Grafico combinato
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('📈 Operazioni per Mese', '💰 Fatturato per Mese'),
        vertical_spacing=0.1
    )
    
    # Operazioni
    fig.add_trace(
        go.Scatter(
            x=df_monthly['mese'],
            y=df_monthly['id'],
            mode='lines+markers',
            name='Operazioni',
            line=dict(color='#667eea', width=3),
            marker=dict(size=8)
        ),
        row=1, col=1
    )
    
    # Fatturato
    fig.add_trace(
        go.Bar(
            x=df_monthly['mese'],
            y=df_monthly['importo_scontato'],
            name='Fatturato €',
            marker_color='#764ba2'
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def create_status_pie(df):
    """Pie chart status operazioni"""
    if df.empty:
        return
    
    status_counts = df['status_operazione'].value_counts()
    colors = ['#10b981', '#f59e0b']
    
    fig = go.Figure(data=[
        go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent+value'
        )
    ])
    
    fig.update_layout(
        title="🎯 Distribuzione Status Operazioni",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def create_operators_performance(df):
    """Performance operatori"""
    if df.empty:
        return
    
    ops_perf = df.groupby('operatore').agg({
        'id': 'count',
        'importo_scontato': 'sum',
        'status_operazione': lambda x: (x == 'ESEGUITA').sum()
    }).reset_index()
    
    ops_perf.columns = ['operatore', 'tot_operazioni', 'fatturato', 'completate']
    ops_perf['tasso_completamento'] = (ops_perf['completate'] / ops_perf['tot_operazioni'] * 100).round(1)
    ops_perf = ops_perf.sort_values('fatturato', ascending=False)
    
    fig = go.Figure(data=[
        go.Bar(
            x=ops_perf['operatore'],
            y=ops_perf['fatturato'],
            marker_color='#667eea',
            text=ops_perf['fatturato'].apply(lambda x: f'€{x:,.0f}'),
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="💰 Fatturato per Operatore",
        xaxis_title="Operatore",
        yaxis_title="Fatturato (€)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella dettagli
    st.subheader("📊 Dettaglio Performance")
    st.dataframe(
        ops_perf,
        use_container_width=True,
        hide_index=True,
        column_config={
            "operatore": "Operatore",
            "tot_operazioni": st.column_config.NumberColumn("Tot. Operazioni"),
            "fatturato": st.column_config.NumberColumn("Fatturato", format="€%.0f"),
            "completate": st.column_config.NumberColumn("Completate"),
            "tasso_completamento": st.column_config.NumberColumn("Tasso %", format="%.1f%%")
        }
    )

def create_top_operations(df):
    """Top operazioni più frequenti"""
    if df.empty:
        return
    
    top_ops = df['operazione'].value_counts().head(15)
    
    fig = go.Figure(data=[
        go.Bar(
            y=top_ops.index[::-1],
            x=top_ops.values[::-1],
            orientation='h',
            marker=dict(
                color=top_ops.values[::-1],
                colorscale='Viridis'
            ),
            text=top_ops.values[::-1],
            textposition='inside'
        )
    ])
    
    fig.update_layout(
        title="🦷 Top 15 Operazioni più Frequenti",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

# ========================
# PIVOT TABLE CONFIGURABILE
# ========================
def create_configurable_pivot(df):
    """Pivot table configurabile dall'utente"""
    if df.empty:
        st.warning("Nessun dato per pivot table")
        return
    
    st.subheader("📋 Pivot Table Personalizzabile")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pivot_index = st.selectbox(
            "🔽 Righe (Index)",
            options=['operatore', 'operazione', 'status_operazione', 'mese', 'anno']
        )
    
    with col2:
        pivot_columns = st.selectbox(
            "➡️ Colonne",
            options=['status_operazione', 'operatore', 'mese', 'anno', 'trimestre']
        )
    
    with col3:
        pivot_values = st.selectbox(
            "📊 Valori",
            options=['importo_scontato', 'id']
        )
    
    with col4:
        pivot_aggfunc = st.selectbox(
            "🔢 Aggregazione",
            options=['sum', 'count', 'mean', 'max', 'min']
        )
    
    try:
        pivot_table = df.pivot_table(
            index=pivot_index,
            columns=pivot_columns,
            values=pivot_values,
            aggfunc=pivot_aggfunc,
            fill_value=0
        )
        
        st.dataframe(pivot_table, use_container_width=True)
        
        # Export CSV
        csv = pivot_table.to_csv()
        st.download_button(
            label="📥 Scarica Pivot CSV",
            data=csv,
            file_name=f'pivot_{pivot_index}_{pivot_columns}.csv',
            mime='text/csv'
        )
        
    except Exception as e:
        st.error(f"Errore creazione pivot: {e}")

# ========================
# MAIN APP
# ========================
def main():
    # CSS personalizzato
    apply_custom_css()
    
    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1 style="margin: 0; font-size: 3rem;">🏥 Dashboard Medica Interattiva</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Analytics Operazioni Dentali - Dati Anonimi GDPR Compliant
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carica dati
    with st.spinner("🔄 Caricamento dati da Supabase..."):
        df = load_medical_data()
    
    if df.empty:
        st.error("❌ Nessun dato trovato. Verifica la connessione a Supabase.")
        st.stop()
    
    # Applica filtri (sidebar)
    df_filtered = create_sidebar_filters(df)
    
    # KPI Cards
    st.markdown("## 📈 Indicatori Principali")
    show_kpi_cards(df_filtered)
    
    # Grafici principali
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 Trend Temporale")
        create_timeline_chart(df_filtered)
    
    with col2:
        st.markdown("### 🎯 Status Operazioni")
        create_status_pie(df_filtered)
    
    # Performance operatori
    st.markdown("## 👨‍⚕️ Performance Operatori")
    create_operators_performance(df_filtered)
    
    # Top operazioni
    st.markdown("## 🦷 Operazioni più Frequenti")
    create_top_operations(df_filtered)
    
    # Pivot table configurabile
    create_configurable_pivot(df_filtered)
    
    # Dati grezzi
    with st.expander("🔍 Visualizza Dati Grezzi"):
        st.dataframe(df_filtered, use_container_width=True)
        
        # Export dati filtrati
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Scarica Dati Filtrati",
            data=csv,
            file_name='dati_medici_filtrati.csv',
            mime='text/csv'
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🔒 Dashboard sicura e anonima • ☁️ Powered by Streamlit & Supabase</p>
        <p>📊 Aggiornamento automatico ogni 5 minuti</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
