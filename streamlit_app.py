"""The sole supported web entrypoint; calls Python service directly."""
import streamlit as st
from streamlit_folium import st_folium
import os
# Community Cloud secrets are loaded before importing the existing config/service.
try:
    for name in ('DATA_MODE','CWA_API_KEY','CWA_FORECAST_DATASET','CWA_OBSERVATION_DATASET','CACHE_TTL_SECONDS','WEATHER_CACHE_DIR'):
        if name in st.secrets:
            os.environ.setdefault(name, str(st.secrets[name]))
except FileNotFoundError:
    pass
import service
from config import MODE, REGIONS
from dashboard import observations_frame, filter_observations, forecast_frame, csv_bytes, station_map, forecast_chart

st.set_page_config(page_title='台灣氣象觀測所', page_icon='🌤️', layout='wide')
st.title('台灣氣象觀測所')
st.caption('Taiwan Weather Forecast · CWA × Pandas × SQLite × Streamlit')
st.sidebar.subheader('資料設定')
st.sidebar.info('Demo · 固定示範資料，非即時天氣' if MODE == 'demo' else 'Live · 中央氣象署真實測站與預報')
auto = st.sidebar.checkbox('每 5 分鐘自動檢查更新',value=True)
st.sidebar.caption('快取有效期預設 10 分鐘；手動更新仍有 30 秒防連點保護。')

def status(data):
    label = f"{data['source']} · {data['status'].upper()}"
    if data['status'] == 'unavailable': st.error(label + '：' + (data['message'] or '目前無可用資料'))
    elif data['status'] == 'stale': st.warning(label + '：' + (data['message'] or '資料已過期，顯示上次成功資料'))
    elif data['status'] == 'demo': st.info(label + '：固定教學示範，非即時資料')
    else: st.success(label)
    st.caption('最後擷取：' + str(data.get('fetched_at') or '尚未取得'))
    if data.get('note'): st.caption(data['note'])

@st.fragment(run_every=300 if auto else None)
def observation_panel():
    force = st.button('重新整理觀測',key='refresh_obs')
    data = service.load('observations',force=force)
    status(data)
    frame = observations_frame(data['rows'])
    if frame.empty: return
    cols = st.columns(3)
    county = cols[0].selectbox('縣市',['全台灣']+sorted(frame.county.dropna().unique().tolist()),key='county')
    search = cols[1].text_input('搜尋測站或鄉鎮',key='search')
    threshold = cols[2].selectbox('氣溫篩選',['所有氣溫','20°C 以上','30°C 以上','35°C 以上'],key='threshold')
    filtered = filter_observations(frame,county,search,None if threshold=='所有氣溫' else int(threshold[:2]))
    a,b = st.columns(2)
    a.metric('符合條件測站',len(filtered))
    b.metric('測站平均氣溫',f'{filtered.temperature_c.mean():.1f} °C' if len(filtered) else '—')
    st.caption('觀測時間：'+str(frame.observed_at.max())+' · 各測站觀測時間請見明細')
    labels = st.checkbox('顯示溫度標籤',key='labels')
    markers = st.checkbox('顯示測站',value=True,key='markers')
    st_folium(station_map(filtered,labels,markers),height=520,width=None,returned_objects=[],key='station_map')
    st.caption('色階 °C：<10 藍 / 10–15 淺藍 / 15–20 綠 / 20–25 黃 / 25–30 橙 / 30–35 紅 / ≥35 深紅。底圖 OpenStreetMap；圓點是 CWA 實測，不是模型圖層。')
    if filtered.empty:
        st.info('沒有符合條件的測站，請調整篩選。')
        return
    lookup=filtered.set_index('station_id')
    sid=st.selectbox('測站詳細資料',filtered.station_id.tolist(),format_func=lambda sid:f"{lookup.loc[sid,'station_name']} · {sid}",key='station')
    row=lookup.loc[sid]
    fields={'氣溫 °C':'temperature_c','濕度 %':'humidity_percent','氣壓 hPa':'pressure_hpa','風速 m/s':'wind_speed_mps','風向 °':'wind_direction_deg','降雨 mm':'precipitation_mm'}
    for col,(label,key) in zip(st.columns(6),fields.items()):
        import pandas as pd
        col.metric(label,'—' if pd.isna(row[key]) else str(row[key]))
    st.caption(f"{row['county']} · {row['town']} · 觀測 {row['observed_at']}")
    st.dataframe(filtered,hide_index=True,width="stretch")

@st.fragment(run_every=300 if auto else None)
def forecast_panel():
    force = st.button('重新整理預報',key='refresh_forecast')
    data=service.load('forecast',force=force)
    status(data)
    region=st.selectbox('預報地區',REGIONS,key='region')
    frame=forecast_frame(data['rows'],region)
    if frame.empty:
        st.info('此區目前沒有可用預報。')
        return
    a,b,c=st.columns(3)
    a.metric('預報最低溫',f'{frame.mint.min():.1f} °C')
    b.metric('預報最高溫',f'{frame.maxt.max():.1f} °C')
    c.metric('預報涵蓋',f'{len(frame)} 天')
    if len(frame)<7: st.warning('目前資料不足七天，僅顯示可用日期。')
    st.altair_chart(forecast_chart(frame),width="stretch")
    st.dataframe(frame.assign(日夜溫差=frame.maxt-frame.mint),hide_index=True,width="stretch")
    st.download_button('下載此區 CSV',csv_bytes(frame),file_name=f'{region}-forecast.csv',mime='text/csv',key='forecast_csv')

obs,forecast=st.tabs(['即時氣象觀測','七日天氣預報'])
with obs: observation_panel()
with forecast: forecast_panel()
