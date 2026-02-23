import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. Konfigurācija
st.set_page_config(page_title="NordTech Diagnostika", layout="wide")

# Vizuālais stils no parauga
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
def load_data_from_github():
    # Meklējam failus tekošajā mapē
    o_p = next((f for f in os.listdir('.') if 'orders_raw' in f.lower()), None)
    r_p = next((f for f in os.listdir('.') if 'returns_messy' in f.lower()), None)
    
    if not o_p or not r_p:
        return None

    # Ielādējam datus
    try:
        df = pd.read_csv(o_p, sep=None, engine='python')
        rdf = pd.read_excel(r_p) if r_p.endswith('.xlsx') else pd.read_csv(r_p)
        
        # Kolonnu tīrīšana
        df.columns = [c.strip() for c in df.columns]
        rdf.columns = [c.strip() for c in rdf.columns]
        
        # Dinamiska kolonnu meklēšana
        oid = next(c for c in df.columns if any(k in c.lower() for k in ['order_id', 'id']))
        rid = next(c for c in rdf.columns if any(k in c.lower() for k in ['original_tx_id', 'tx_id', 'id']))
        cat_col = next(c for c in df.columns if 'category' in c.lower())
        p_col = next(c for c in df.columns if 'price' in c.lower())
        d_col = next(c for c in df.columns if 'date' in c.lower())
        
        # Datumu un cenu sakārtošana
        df['Date_Clean'] = pd.to_datetime(df[d_col], errors='coerce')
        df[cat_col] = df[cat_col].astype(str).str.strip()
        df[oid] = df[oid].astype(str).str.strip()
        rdf[rid] = rdf[rid].astype(str).str.strip()
        
        # Apvienošana
        master = pd.merge(df, rdf, left_on=oid, right_on=rid, how='left')
        master['Price_Clean'] = pd.to_numeric(master[p_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
        
        return master, cat_col, oid
    except Exception as e:
        st.error(f"Kļūda datu ielādē: {e}")
        return None

# --- Dashboard izpilde ---
result = load_data_from_github()

if result:
    data, cat_col, oid = result

    # SĀNJOSLA
    st.sidebar.header("🔍 Filtri")
    u_cats = sorted(data[cat_col].unique())
    selected = st.sidebar.multiselect("Kategorijas:", u_cats, default=u_cats)
    f_df = data[data[cat_col].isin(selected)]

    st.title("🛡️ NordTech Biznesa Diagnostika")

    # KPI Rinda
    c1, c2, c3 = st.columns(3)
    c1.metric("Kopējie ieņēmumi", f"{f_df['Price_Clean'].sum():,.2f} EUR")
    c2.metric("Pasūtījumu skaits", len(f_df))
    # Atgriešanas aprēķins
    ret_rate = (len(f_df[f_df['Status'].notnull()]) / len(f_df) * 100) if len(f_df) > 0 else 0
    c3.metric("Atgriešanu %", f"{ret_rate:.1f}%")

    # IEŅĒMUMU DINAMIKA (Līniju grafiks)
    st.subheader("📈 Ieņēmumu dinamika")
    daily = f_df.groupby('Date_Clean')['Price_Clean'].sum().reset_index()
    fig_line = px.line(daily, x='Date_Clean', y='Price_Clean', markers=True, template="plotly_dark")
    st.plotly_chart(fig_line, use_container_width=True)

    # Citi vizuāļi
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Ieņēmumi pa kategorijām")
        fig_pie = px.pie(f_df.groupby(cat_col)['Price_Clean'].sum().reset_index(), names=cat_col, values='Price_Clean', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_r:
        st.subheader("Datu tabula")
        st.dataframe(f_df[[oid, cat_col, 'Price_Clean']].head(10), use_container_width=True)
else:
    st.warning("⚠️ Lūdzu, augšupielādē 'orders_raw.csv' un 'returns_messy.csv' savā GitHub repozitorijā!")
