import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import random
from datetime import datetime,timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="HamurLabs Operasyon Paneli",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# --- CSS: BUTONLARI EŞİT KARTLARA DÖNÜŞTÜRME ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100% !important;
        height: 120px !important;
        background-color: white;
        color: #495057;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        white-space: pre-wrap; 
        line-height: 1.4;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        border-color: #28a745;
        color: #28a745;
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        background-color: #f8f9fa;
    }
    div.stButton > button p {
        font-size: 16px; 
    }
</style>
""", unsafe_allow_html=True)


# Şimdiki zamanı al
simdi = datetime.now()

# Bugünün başlangıcı (Saat 00:00:00)
bugun_baslangic = simdi.replace(hour=0, minute=0, second=0, microsecond=0)

# Bugünün sonu (Saat 23:59:59)
bugun_bitis = simdi.replace(hour=23, minute=59, second=59, microsecond=0)

# --- YENİ KISIM: 1 Hafta Öncesini Hesapla ---
bir_hafta_once = bugun_baslangic - timedelta(days=7)

# API'nin istediği string formatına ("Yıl-Ay-Gün Saat:Dakika:Saniye") çevir
start_str = bugun_baslangic.strftime("%Y-%m-%d %H:%M:%S")
end_str = bugun_bitis.strftime("%Y-%m-%d %H:%M:%S")
created_start_str = bir_hafta_once.strftime("%Y-%m-%d %H:%M:%S") # 1 hafta öncesi


# --- SABİTLER ---
HAMURLABS_URL = "http://dgn.hamurlabs.io/api/order/v2/search/"
HAMURLABS_HEADERS = {
    "Authorization": "Basic c2VsaW0uc2FyaWtheWE6NDMxMzQyNzhDY0A=",
    "Content-Type": "application/json"
}
PAGE_SIZE = 50

DEPO_MAP = {
    "4216": "Ereğli", "27005": "Karataş", "27004": "Gazikent", "6101": "Trabzon",
    "27003": "İpekyolu", "4215": "Meram", "46002": "Binevler", "TOM": "TOM",
    "27001": "Sanko", "4203": "Kampüs", "46001": "Piazza", "4200": "Merkez Ayakkabı",
    "4201": "Merkez Giyim", "4210": "Novada", "4214": "Fabrika Satış", "46012": "Oniki Şubat",
    "27000": "Gazimuhtar", "27002": "Suburcu", "4207": "BosnaMix", "4212": "Real",
    "4206": "Plus", "M": "Aykent Depo", "4202": "Sportive"
}

STATUS_MAP = {
    "Shipped": "Kargolanmış", "Waiting": "Bekliyor", "Cancelled": "İptal",
    "Invoiced": "Faturalanmış", "Loaded Delivery": "Teslimata Yüklenmiş",
    "Picked": "Paketlendi", "Packed": "Paketlendi", "Created": "Oluşturuldu"
}

# --- POPUP FONKSİYONU ---
@st.dialog("📋 Sipariş Detay Listesi", width="large")
def open_order_popup(status_name, df_data):
    st.info(f"**{status_name}** durumundaki siparişler listelenmektedir.")
    base_filtered = df_data[df_data['Durum'] == status_name]
    search_query = st.text_input("🔍 Sipariş No veya Müşteri Ara", placeholder="Örn: 1025 veya Ahmet...")
    
    if search_query:
        final_filtered = base_filtered[
            base_filtered['Sipariş No'].str.contains(search_query, case=False, na=False) |
            base_filtered['Müşteri'].str.contains(search_query, case=False, na=False)
        ]
    else:
        final_filtered = base_filtered

    if not final_filtered.empty:
        st.dataframe(
            final_filtered, use_container_width=True, hide_index=True,
            column_config={
                "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                "Adet": st.column_config.ProgressColumn("Adet", min_value=0, max_value=10)
            }
        )
        st.caption(f"Toplam {len(base_filtered)} kayıttan {len(final_filtered)} tanesi gösteriliyor.")
    else:
        st.warning("Kayıt bulunamadı.")

# --- YARDIMCI FONKSİYONLAR ---
def resolve_warehouse_names(code_str):
    if not code_str: return "-"
    codes = [c.strip() for c in str(code_str).split(',')]
    names = [DEPO_MAP.get(c, c) for c in codes]
    return ", ".join(names)

def fetch_all_orders(use_demo_data=False):
    all_orders = []
    if use_demo_data:
        shops = ["Trendyol", "Hepsiburada", "Shopify", "Amazon", "Flo"]
        statuses = ["Invoiced", "Shipped", "Loaded Delivery", "Picked", "Waiting", "Cancelled"]
        all_codes = list(DEPO_MAP.keys())
        for i in range(1, 150):
            status_name = random.choice(statuses)
            pool_codes = random.sample(all_codes, k=random.randint(1, 3))
            warehouses_str = ",".join(pool_codes)
            actual_wh_code = random.choice(pool_codes) if status_name != "Waiting" else None
            all_orders.append({
                "order_id": 1000 + i, "shop": random.choice(shops),
                "customer_name": f"Müşteri {i}", "status": status_name, 
                "warehouses": warehouses_str, "warehouse_code": actual_wh_code,
                "created_at": "2024-06-03 14:25:56", "total_quantity": random.randint(1, 5),
                "items": [{"product_name": f"Ürün {i}", "selling_price": 150, "quantity": 1}]
            })
        return all_orders

    start = 0; total_records = 1; status_text = st.sidebar.empty(); progress_bar = st.sidebar.progress(0)
    try:
        while len(all_orders) < total_records:
            payload = {
                "company_id": "1",
                "updated_at__start": start_str, # Tarihleri dinamik yapabilirsin
                "updated_at__end": end_str,
                "created_at__start": created_start_str,
                "created_at__end": end_str,
                "size": PAGE_SIZE,
                "start": start,
                "order_types": ["selling"]
            }
            response = requests.post(HAMURLABS_URL, headers=HAMURLABS_HEADERS, json=payload, timeout=20)
            if response.status_code != 200: break
            data = response.json()
            batch_data = data.get("data", [])
            total_records = data.get("total", 0)
            if not batch_data: break
            all_orders.extend(batch_data)
            fetched_count = len(all_orders)
            if total_records > 0: progress_bar.progress(min(fetched_count / total_records, 1.0))
            status_text.text(f"Veri Çekiliyor: {fetched_count}/{total_records}")
            start += PAGE_SIZE
            if fetched_count >= total_records: break
        status_text.empty(); progress_bar.empty()
        return all_orders
    except Exception as e: st.error(f"Hata: {e}"); return []

def process_data(orders):
    if not orders: return pd.DataFrame()
    processed = []
    for o in orders:
        total_price = sum([item.get('selling_price', 0) * item.get('quantity', 0) for item in o.get('items', [])])
        raw_status = o.get('status')
        tr_status = STATUS_MAP.get(raw_status, raw_status)
        readable_code = DEPO_MAP.get(str(o.get('warehouse_code')).strip(), o.get('warehouse_code')) if o.get('warehouse_code') else "Henüz Atanmadı"
        
        processed.append({
            "Sipariş No": str(o.get('tracker_code', o.get('order_id'))),
            "Mağaza": o.get('shop', 'Bilinmiyor'),
            "Potansiyel Depolar": resolve_warehouse_names(o.get('warehouses')),
            "İşlemi Yapan": readable_code,
            "Durum": tr_status, "Müşteri": o.get('customer_name'),
            "Adet": o.get('total_quantity', 0), "Tutar": total_price
        })
    return pd.DataFrame(processed)

# --- ARAYÜZ ---
st.title("📊 E-Ticaret Operasyon Merkezi")
with st.sidebar:
    st.header("Veri Kaynağı")
    use_demo = st.checkbox("Demo Veri Kullan", value=True)
    if st.button("Verileri Yenile", type="primary"):
        with st.spinner("Veriler güncelleniyor..."):
            st.session_state['orders_raw'] = fetch_all_orders(use_demo)
        st.rerun()

if 'orders_raw' not in st.session_state: st.info("👈 Verileri görmek için soldaki butona basınız."); st.stop()
df = process_data(st.session_state['orders_raw'])
if df.empty: st.warning("Veri bulunamadı."); st.stop()

# --- KPI ALANI ---
st.markdown("### 📈 Özet Tablo")

total_orders = len(df)
total_revenue = f"{df['Tutar'].sum():,.0f} ₺"
cnt_waiting = len(df[df['Durum'] == 'Bekliyor'])
cnt_invoiced = len(df[df['Durum'] == 'Faturalanmış'])
cnt_loaded = len(df[df['Durum'] == 'Teslimata Yüklenmiş'])
cnt_shipped = len(df[df['Durum'] == 'Kargolanmış'])
cnt_cancelled = len(df[df['Durum'] == 'İptal'])
active_depots = df[df['İşlemi Yapan'] != "Henüz Atanmadı"]['İşlemi Yapan'].nunique()

c1, c2, c3, c4 = st.columns(4)
with c1: st.button(f"TOPLAM SİPARİŞ\n{total_orders}", key="kpi1", use_container_width=True)
with c2: st.button(f"TOPLAM CİRO\n{total_revenue}", key="kpi2", use_container_width=True)
with c3:
    if st.button(f"BEKLİYOR\n{cnt_waiting}", key="kpi3", use_container_width=True):
        open_order_popup("Bekliyor", df)
with c4:
    if st.button(f"FATURALANMIŞ\n{cnt_invoiced}", key="kpi4", use_container_width=True):
        open_order_popup("Faturalanmış", df)

c5, c6, c7, c8 = st.columns(4)
with c5:
    if st.button(f"TESLİMAT YÜKL.\n{cnt_loaded}", key="kpi5", use_container_width=True):
        open_order_popup("Teslimata Yüklenmiş", df)
with c6:
    if st.button(f"KARGOLANAN\n{cnt_shipped}", key="kpi6", use_container_width=True):
        open_order_popup("Kargolanmış", df)
with c7:
    if st.button(f"İPTAL\n{cnt_cancelled}", key="kpi7", use_container_width=True):
        open_order_popup("İptal", df)
with c8: st.button(f"AKTİF DEPO\n{active_depots}", key="kpi8", use_container_width=True)

st.markdown("---")

# --- GRAFİKLER ---
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("🛍️ Pazaryeri")
    # Veriyi önce bir değişkene atayalım ki okuması kolay olsun
    marketplace_data = df['Mağaza'].value_counts().reset_index()
    
    # Grafiği oluştururken 'text' parametresini ekliyoruz
    fig_market = px.bar(
        marketplace_data, 
        x='Mağaza', 
        y='count', 
        color='Mağaza', 
        text='count'  # <-- BU SATIR RAKAMLARI GETİRİR
    )
    
    # Rakamların sütunun üzerinde (dışında) durması ve formatı için ayar
    fig_market.update_traces(textposition='outside', textfont_size=12)
    
    # Grafiği çizdir
    st.plotly_chart(fig_market, use_container_width=True)
with c2:
    st.subheader("📦 Durumlar")
    st.plotly_chart(px.pie(df['Durum'].value_counts().reset_index(), values='count', names='Durum', hole=0.4), use_container_width=True)

# *** GÜNCELLENEN KISIM: TREEMAP ÜZERİNE RAKAM EKLEME ***
with c3:
    st.subheader("🏆 Şube Performansı")
    df_assigned = df[df['İşlemi Yapan'] != "Henüz Atanmadı"]
    if not df_assigned.empty:
        perf_counts = df_assigned['İşlemi Yapan'].value_counts().reset_index()
        perf_counts.columns = ['Şube', 'Sipariş']
        
        # Treemap grafiği
        fig_perf = px.treemap(
            perf_counts, 
            path=['Şube'], 
            values='Sipariş', 
            color='Sipariş',
            color_continuous_scale='Viridis'
        )
        
        # BU SATIR EKLENDİ: Kutuların üzerinde hem İSİM hem DEĞER yazar
        fig_perf.update_traces(textinfo="label+value")
        
        st.plotly_chart(fig_perf, use_container_width=True)

st.markdown("### 🏢 Mağaza Karnesi")
target_statuses = ["Faturalanmış", "Teslimata Yüklenmiş", "Kargolanmış"]
df_pivot_source = df[(df['Durum'].isin(target_statuses)) & (df['İşlemi Yapan'] != "Henüz Atanmadı")]
if not df_pivot_source.empty:
    pivot_table = pd.pivot_table(df_pivot_source, index='İşlemi Yapan', columns='Durum', values='Sipariş No', aggfunc='count', fill_value=0)
    for status in target_statuses:
        if status not in pivot_table.columns: pivot_table[status] = 0
    pivot_table = pivot_table[target_statuses]
    pivot_table['Toplam İşlem'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table.sort_values(by='Toplam İşlem', ascending=False)
    st.dataframe(pivot_table, use_container_width=True, column_config={
        "İşlemi Yapan": st.column_config.TextColumn("Şube Adı"),
        "Faturalanmış": st.column_config.ProgressColumn("Faturalanmış", format="%d", min_value=0, max_value=int(pivot_table['Faturalanmış'].max())),
        "Teslimata Yüklenmiş": st.column_config.ProgressColumn("Teslimata Yüklenmiş", format="%d", min_value=0, max_value=int(pivot_table['Teslimata Yüklenmiş'].max())),
        "Kargolanmış": st.column_config.ProgressColumn("Kargolanmış", format="%d", min_value=0, max_value=int(pivot_table['Kargolanmış'].max())),
        "Toplam İşlem": st.column_config.NumberColumn("Toplam", format="%d")
    })
else: st.info("Veri yok.")

st.markdown("### 📋 Tüm Siparişler")
f1, f2, f3 = st.columns(3)
with f1: sel_status = st.multiselect("Durum Filtrele", df['Durum'].unique())
with f2: sel_actor = st.multiselect("Şube Filtrele", df['İşlemi Yapan'].unique())
with f3: search_term = st.text_input("Sipariş Ara")
df_show = df.copy()
if sel_status: df_show = df_show[df_show['Durum'].isin(sel_status)]
if sel_actor: df_show = df_show[df_show['İşlemi Yapan'].isin(sel_actor)]
if search_term: df_show = df_show[df_show['Sipariş No'].str.contains(search_term, case=False) | df_show['Müşteri'].str.contains(search_term, case=False)]
st.dataframe(df_show, use_container_width=True, hide_index=True, column_config={
    "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
    "Adet": st.column_config.ProgressColumn("Adet", format="%f", min_value=0, max_value=10)
})
