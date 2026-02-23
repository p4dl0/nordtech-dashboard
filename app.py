import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. Konfigurācija
st.set_page_config(page_title="NordTech Diagnostika", layout="wide")

# Tumšais stils metriku kartītēm
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 10px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_and_fix_data():
    # Atrodam failus
    o_p = next((os.path.join(r, n) for r, d, f in os.walk('.') for n in f if 'orders_raw' in n.lower()), None)
    r_p = next((os.path.join(r, n) for r, d, f in os.walk('.') for n in f if 'returns_messy' in n.lower()), None)
    
    if not o_p or not r_p: return None

    df = pd.read_csv(o_p, sep=None, engine='python')
    rdf = pd.read_excel(r_p) if r_p.endswith('.xlsx') else pd.read_csv(r_p)
    
    # Kolonnu un datu tīrīšana
    df.columns = [c.strip() for c in df.columns]
    rdf.columns = [c.strip() for c in rdf.columns]
    
    # Atrodam kolonnas
    oid = next(c for c in df.columns if any(k in c.lower() for k in ['order_id', 'id']))
    rid = next(c for c in rdf.columns if any(k in c.lower() for k in ['original_tx_id', 'tx_id', 'id']))
    cat_col = next(c for c in df.columns if 'category' in c.lower())
    p_col = next(c for c in df.columns if 'price' in c.lower())
    d_col = next(c for c in df.columns if 'date' in c.lower())
    issue_col = next((c for c in rdf.columns if any(k in c.lower() for k in ['issue', 'reason', 'category'])), None)

    # Iztīrām dublikātus filtrā un sagatavojam datumus
    df[cat_col] = df[cat_col].astype(str).str.strip()
    df['Date_Clean'] = pd.to_datetime(df[d_col], errors='coerce')
    df = df.dropna(subset=['Date_Clean'])
    
    # Apvienojam datus
    df[oid] = df[oid].astype(str).str.strip()
    rdf[rid] = rdf[rid].astype(str).str.strip()
    master = pd.merge(df, rdf, left_on=oid, right_on=rid, how='left')

    # Finanšu tīrīšana
    master['Price_Clean'] = pd.to_numeric(master[p_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    master['Issue_Final'] = master[issue_col].fillna('Nav sūdzību') if issue_col else 'Nav sūdzību'
    
    return master, cat_col, oid

result = load_and_fix_data()

if result:
    data, cat_col, oid = result

    # --- SIDEBAR FILTRI ---
    st.sidebar.header("🔍 Filtri")
    unique_categories = sorted(data[cat_col].unique())
    selected_cats = st.sidebar.multiselect("Produktu kategorijas:", unique_categories, default=unique_categories)
    f_df = data[data[cat_col].isin(selected_cats)]

    st.title("🛡️ NordTech Biznesa Diagnostika")

    # --- KPI RINDA ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Kopējie ieņēmumi", f"{f_df['Price_Clean'].sum():,.2f} EUR")
    ret_rate = (f_df[f_df['Status'] == 'Processed'].shape[0] / len(f_df) * 100) if len(f_df) > 0 else 0
    m2.metric("Atgriešanu %", f"{ret_rate:.2f}%")
    m3.metric("Sūdzību skaits", f_df[f_df['Issue_Final'] != 'Nav sūdzību'].shape[0])

    st.markdown("---")

    # --- 1. IEŅĒMUMU DINAMIKA (Tas, kas trūka) ---
    st.subheader("📈 Ieņēmumu dinamika (Revenue Over Time)")
    # Grupējam pēc datuma
    daily_revenue = f_df.groupby('Date_Clean')['Price_Clean'].sum().reset_index()
    fig_line = px.line(daily_revenue, x='Date_Clean', y='Price_Clean', 
                       title="Dienas ieņēmumi", labels={'Price_Clean': 'Ieņēmumi (EUR)', 'Date_Clean': 'Datums'},
                       template="plotly_dark", markers=True)
    fig_line.update_traces(line_color='#00ff00')
    st.plotly_chart(fig_line, use_container_width=True)

    # --- 2. PĀRĒJIE VIZUĀĻI ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sūdzību iemesli")
        iss_df = f_df[f_df['Issue_Final'] != 'Nav sūdzību']
        if not iss_df.empty:
            fig_bar = px.bar(iss_df['Issue_Final'].value_counts().reset_index(), 
                            y='Issue_Final', x='count', orientation='h', 
                            color='Issue_Final', template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)
        else: st.info("Sūdzību nav.")

    with col2:
        st.subheader("Ieņēmumi pa kategorijām")
        comp_df = f_df.groupby(cat_col)['Price_Clean'].sum().reset_index()
        fig_cat = px.pie(comp_df, names=cat_col, values='Price_Clean', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig_cat, use_container_width=True)

    # --- 3. TABULA ---
    st.subheader("⚠️ Problemātiskie pasūtījumi")
    st.dataframe(f_df[f_df['Issue_Final'] != 'Nav sūdzību'].head(10), use_container_width=True)

else:
    st.error("Dati nav atrasti!")
