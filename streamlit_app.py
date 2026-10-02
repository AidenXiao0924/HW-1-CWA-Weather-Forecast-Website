"""The sole supported web entrypoint; calls Python service directly."""
from html import escape
import streamlit as st
from streamlit_folium import st_folium
import os
import pandas as pd
import altair as alt
# Community Cloud secrets are loaded before importing the existing config/service.
try:
    for name in ('DATA_MODE','CWA_API_KEY','CWA_FORECAST_DATASET','CWA_OBSERVATION_DATASET','CWA_WARNING_DATASET','CACHE_TTL_SECONDS','WEATHER_CACHE_DIR'):
        if name in st.secrets:
            os.environ.setdefault(name, str(st.secrets[name]))
except FileNotFoundError:
    pass
import service
from config import MODE, REGIONS, REGION_COUNTIES
from dashboard import (observations_frame, filter_observations, forecast_frame, warning_frame,
    csv_bytes, station_map, forecast_chart, precipitation_chart, weather_icon, outing_advice,
    LAYER_CONFIG, layer_series, county_summary, county_ranking_chart, RANKING_METRICS,
    data_quality_summary, nearest_station_id)

st.set_page_config(page_title='台灣氣象觀測所', page_icon='🌤️', layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&family=Noto+Sans+TC:wght@400;500;600;700;800&display=swap');
:root {--ink:#f2f8ff;--muted:#c5d8e8;--soft:#abc5d9;--line:rgba(148,195,230,.22);--glass:rgba(9,26,43,.72);--cyan:#38bdf8;--blue:#2563eb;--amber:#fbbf24}
html,body,[class*="css"] {font-family:'Noto Sans TC','Inter',sans-serif}
.stApp {color:var(--ink);background:
 radial-gradient(circle at 83% 4%,rgba(14,165,233,.21),transparent 28rem),
 radial-gradient(circle at 12% 84%,rgba(37,99,235,.18),transparent 34rem),
 linear-gradient(145deg,#020817 0%,#071526 48%,#071b2c 100%);background-attachment:fixed}
.stApp:before {content:"";position:fixed;inset:0;pointer-events:none;opacity:.19;background-image:
 repeating-radial-gradient(ellipse at 90% 20%,transparent 0 28px,rgba(125,211,252,.16) 29px 30px,transparent 31px 50px)}
[data-testid="stHeader"] {background:transparent}
[data-testid="stSidebar"] {background:linear-gradient(180deg,rgba(5,15,29,.97),rgba(8,31,48,.96));border-right:1px solid var(--line)}
.block-container {max-width:1480px;padding-top:1.7rem;padding-bottom:4rem}
h1,h2,h3 {letter-spacing:-.02em;color:#f7fbff!important}
p,.stCaption,[data-testid="stCaptionContainer"] p,[data-testid="stWidgetLabel"] p,label {color:var(--muted)!important}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span {color:#c8dbea}
[data-testid="stAlert"] p,[data-testid="stAlert"] div {color:#deeffb!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] p {color:#d8e9f6!important}
div[data-testid="stMetric"] {height:100%;background:linear-gradient(145deg,rgba(17,45,68,.82),rgba(8,25,42,.76));border:1px solid var(--line);padding:1rem 1.15rem;border-radius:18px;box-shadow:0 16px 38px rgba(0,0,0,.18);transition:transform .2s ease,border-color .2s ease}
div[data-testid="stMetric"]:hover {transform:translateY(-3px);border-color:rgba(56,189,248,.42)}
div[data-testid="stMetricLabel"],div[data-testid="stMetricLabel"] p {color:#c8dceb!important} div[data-testid="stMetricValue"] {color:#fbfdff;font-family:'Inter','Noto Sans TC',sans-serif}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px;border-color:var(--line);background:rgba(9,27,44,.55)}
[data-baseweb="tab-list"] {gap:.35rem;padding:.35rem;background:rgba(8,25,42,.72);border:1px solid var(--line);border-radius:15px;backdrop-filter:blur(16px)}
[data-baseweb="tab"] {height:3rem;border-radius:11px;padding:0 1.2rem;color:#c9dbea}
[data-baseweb="tab"] p {color:inherit!important}
[aria-selected="true"][data-baseweb="tab"] {background:linear-gradient(135deg,rgba(14,165,233,.25),rgba(37,99,235,.3));color:#f8fbff}
[data-testid="stDataFrame"],iframe {border-radius:18px;overflow:hidden;box-shadow:0 18px 45px rgba(0,0,0,.18)}
.stButton>button,.stDownloadButton>button {border-radius:12px;border:1px solid rgba(56,189,248,.42);background:rgba(14,165,233,.13);color:#effaff;transition:all .2s ease}
.stButton>button p,.stDownloadButton>button p {color:#effaff!important}
.stButton>button:hover,.stDownloadButton>button:hover {border-color:#38bdf8;transform:translateY(-2px);box-shadow:0 10px 24px rgba(14,165,233,.18)}
.wx-hero {position:relative;overflow:hidden;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(230px,.7fr);gap:1.5rem;align-items:center;padding:2rem 2.2rem;margin-bottom:1.2rem;border:1px solid rgba(125,211,252,.2);border-radius:26px;background:linear-gradient(125deg,rgba(8,38,62,.9),rgba(14,81,120,.68));box-shadow:0 24px 70px rgba(0,0,0,.3);backdrop-filter:blur(18px);animation:rise .65s ease both}
.wx-hero.wx-night {background:linear-gradient(125deg,rgba(3,12,35,.96),rgba(30,58,138,.67))}.wx-hero.wx-hot {background:linear-gradient(125deg,rgba(56,24,18,.93),rgba(180,83,9,.68))}.wx-hero.wx-alert {background:linear-gradient(125deg,rgba(64,20,35,.94),rgba(146,64,14,.72))}
.wx-hero:after {content:"";position:absolute;width:280px;height:280px;right:-60px;top:-110px;border-radius:50%;background:radial-gradient(circle,#fde68a 0,#fbbf2470 28%,transparent 70%);filter:blur(2px);animation:breathe 6s ease-in-out infinite}
.wx-hero.wx-night:after {background:radial-gradient(circle,#e0f2fe 0,#93c5fd66 22%,transparent 68%)}.wx-hero.wx-alert:after {background:radial-gradient(circle,#fecaca 0,#fb718566 25%,transparent 68%)}.wx-scene {position:absolute;right:2rem;bottom:-.45rem;font-size:clamp(4rem,9vw,8rem);opacity:.10;filter:drop-shadow(0 12px 24px rgba(0,0,0,.3));transform:rotate(-8deg)}
.wx-eyebrow {font:700 .72rem/1.2 'Inter';letter-spacing:.2em;color:#7dd3fc;text-transform:uppercase}.wx-title {margin:.45rem 0 .55rem;font-size:clamp(2rem,4vw,3.6rem);font-weight:800;line-height:1.05;color:#fff}.wx-subtitle {color:#d0e2ef;font-size:1rem}.wx-live {display:inline-flex;align-items:center;gap:.45rem;margin-top:1rem;padding:.4rem .7rem;border-radius:999px;background:rgba(2,132,199,.16);border:1px solid rgba(56,189,248,.34);font-size:.78rem;color:#d9f3ff}.wx-live i {width:8px;height:8px;border-radius:50%;background:#34d399;box-shadow:0 0 0 5px rgba(52,211,153,.12);animation:pulse 2s infinite}.wx-hero-stat {position:relative;z-index:1;padding:1.1rem 1.25rem;border-radius:18px;background:rgba(2,15,29,.45);border:1px solid rgba(255,255,255,.14)}.wx-degree {font:800 clamp(2.5rem,5vw,4.8rem)/1 'Inter';color:#fff}.wx-meta {display:grid;grid-template-columns:1fr 1fr;gap:.65rem;margin-top:1rem}.wx-meta div {padding:.7rem;border-radius:12px;background:rgba(255,255,255,.08)}.wx-meta b {display:block;color:#fff}.wx-meta span {font-size:.75rem;color:#c0d5e5}
.section-kicker {margin:1.25rem 0 .7rem;color:#7dd3fc;font:700 .72rem/1.2 'Inter';letter-spacing:.16em;text-transform:uppercase}
.forecast-grid {display:grid;grid-template-columns:repeat(7,minmax(125px,1fr));gap:.75rem;margin:1rem 0 1.35rem}.forecast-card {position:relative;overflow:hidden;padding:1rem .85rem;border-radius:17px;background:linear-gradient(160deg,rgba(18,57,83,.82),rgba(8,26,43,.88));border:1px solid var(--line);text-align:center;transition:transform .22s ease,border-color .22s ease}.forecast-card:hover {transform:translateY(-5px);border-color:rgba(125,211,252,.5)}.forecast-card .day {font-weight:700;color:#eefaff}.forecast-card .date {font-size:.75rem;color:#bfd5e5}.forecast-card .icon {font-size:2.25rem;margin:.65rem 0;filter:drop-shadow(0 8px 12px rgba(0,0,0,.22))}.forecast-card .temps {font:700 1rem 'Inter';color:#fff}.forecast-card .rain {margin-top:.45rem;font-size:.75rem;color:#9bdfff}
.podium {display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;align-items:end;margin:1rem 0 1.4rem}.podium-card {position:relative;text-align:center;padding:1.25rem 1rem;border-radius:18px;background:rgba(12,37,58,.78);border:1px solid var(--line)}.podium-card.rank-1 {min-height:155px;background:linear-gradient(150deg,rgba(120,74,8,.54),rgba(20,37,50,.86));border-color:rgba(251,191,36,.42)}.podium-card.rank-2 {min-height:132px}.podium-card.rank-3 {min-height:118px;background:linear-gradient(150deg,rgba(124,45,18,.35),rgba(20,37,50,.86))}.podium-medal {font-size:1.6rem}.podium-city {font-size:1.05rem;font-weight:700;color:#fff}.podium-value {margin-top:.3rem;font:800 1.35rem 'Inter';color:#7dd3fc}
.ranking-highlights {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;margin:.2rem 0 1rem}.ranking-highlight {min-width:0;padding:1rem 1.15rem;border-radius:18px;background:linear-gradient(145deg,rgba(17,45,68,.82),rgba(8,25,42,.76));border:1px solid var(--line);box-shadow:0 16px 38px rgba(0,0,0,.18);transition:transform .2s ease,border-color .2s ease}.ranking-highlight:hover {transform:translateY(-3px);border-color:rgba(56,189,248,.42)}.ranking-label {font-size:.82rem;color:#c7dbea;white-space:nowrap}.ranking-city {margin-top:.55rem;color:#f8fbff;font-size:clamp(1.1rem,1.35vw,1.45rem);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ranking-number {margin-top:.2rem;color:#8bddff;font:800 clamp(1.35rem,1.75vw,1.8rem)/1.2 'Inter';white-space:nowrap}.ranking-unit {margin-left:.25rem;font-size:.72em;color:#c0dbea;font-weight:600}
.quality-highlights {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;margin:.2rem 0 1.4rem}.quality-highlight {min-width:0;padding:1rem 1.15rem;border-radius:18px;background:linear-gradient(145deg,rgba(17,45,68,.82),rgba(8,25,42,.76));border:1px solid var(--line);box-shadow:0 16px 38px rgba(0,0,0,.18)}.quality-highlight-label {font-size:.82rem;color:#c7dbea;white-space:nowrap}.quality-highlight-value {margin-top:.55rem;color:#fbfdff;font:800 clamp(1.45rem,2vw,2.15rem)/1.12 'Inter','Noto Sans TC';white-space:nowrap}.quality-highlight-date {margin-top:.5rem;color:#fbfdff;font:750 clamp(1.1rem,1.5vw,1.55rem)/1.2 'Inter';white-space:nowrap}.quality-highlight-date span {display:block;margin-top:.25rem;color:#8bddff;font-size:.85em}
.source-grid {display:grid;grid-template-columns:repeat(3,1fr);gap:.85rem;margin:.75rem 0 1.3rem}.source-card {padding:1rem 1.1rem;border-radius:16px;background:rgba(10,31,49,.8);border:1px solid var(--line)}.source-head {display:flex;justify-content:space-between;gap:.5rem;color:#f3f9ff;font-weight:700}.status-pill {font:700 .65rem 'Inter';padding:.28rem .5rem;border-radius:99px}.status-fresh,.status-demo {color:#6ee7b7;background:rgba(16,185,129,.14)}.status-stale {color:#fcd34d;background:rgba(245,158,11,.14)}.status-unavailable {color:#fca5a5;background:rgba(239,68,68,.14)}.source-detail {margin-top:.65rem;font-size:.78rem;color:#b8cfdf}.quality-list {display:grid;grid-template-columns:repeat(2,1fr);gap:.75rem}.quality-row {padding:.8rem 1rem;border-radius:14px;background:rgba(9,30,48,.7);border:1px solid var(--line)}.quality-label {display:flex;justify-content:space-between;font-size:.82rem;color:#d5e6f2}.quality-track {height:7px;margin-top:.55rem;border-radius:99px;background:rgba(148,163,184,.2);overflow:hidden}.quality-fill {height:100%;border-radius:99px;background:linear-gradient(90deg,#2563eb,#38bdf8,#34d399)}
@keyframes rise {from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}@keyframes breathe {50%{transform:scale(1.08);opacity:.82}}@keyframes pulse {50%{box-shadow:0 0 0 9px rgba(52,211,153,0)}}
@media (prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
@media (max-width:1100px){.ranking-highlights,.quality-highlights{grid-template-columns:repeat(2,1fr)}}
@media (max-width:900px){.wx-hero{grid-template-columns:1fr}.forecast-grid{grid-template-columns:repeat(4,1fr)}.source-grid{grid-template-columns:1fr}}
@media (max-width:640px){.block-container{padding-top:.8rem}.wx-hero{padding:1.35rem;border-radius:20px}.wx-title{font-size:2rem}.forecast-grid{grid-template-columns:repeat(2,1fr)}.ranking-highlights,.quality-highlights{grid-template-columns:1fr 1fr}.ranking-highlight,.quality-highlight{padding:.85rem}.ranking-city{font-size:1rem}.ranking-number,.quality-highlight-value{font-size:1.25rem}.quality-highlight-date{font-size:1rem}.podium{grid-template-columns:1fr;align-items:stretch}.podium-card{min-height:auto!important}.quality-list{grid-template-columns:1fr}div[data-testid="stMetricValue"]{font-size:1.25rem}}
</style>''',unsafe_allow_html=True)
st.sidebar.subheader('資料設定')
st.sidebar.info('Demo · 固定示範資料，非即時天氣' if MODE == 'demo' else 'Live · 中央氣象署真實測站與預報')
auto = st.sidebar.checkbox('每 5 分鐘自動檢查更新',value=True)
st.sidebar.caption('快取有效期預設 10 分鐘；手動更新仍有 30 秒防連點保護。')

def fmt(value, unit='', digits=1):
    return '—' if pd.isna(value) else f'{float(value):.{digits}f}{unit}'

def render_hero():
    obs_data=service.load('observations')
    warning_data=service.load('warnings')
    frame=observations_frame(obs_data['rows'])
    average=pd.to_numeric(frame.temperature_c,errors='coerce').mean() if not frame.empty else float('nan')
    latest=frame.observed_at.dropna().max() if not frame.empty else '尚未取得'
    live_label='即時資料連線正常' if obs_data['status']=='fresh' else f"資料狀態：{obs_data['status']}"
    try: hour=pd.Timestamp(latest).hour
    except (TypeError,ValueError): hour=12
    if warning_data['rows']:
        theme,scene,context='alert','⚠️','警特報監測中'
    elif pd.notna(average) and average>=30:
        theme,scene,context='hot','☀️','高溫觀測'
    elif hour<6 or hour>=18:
        theme,scene,context='night','🌙','夜間觀測'
    else:
        theme,scene,context='day','🌤️','日間觀測'
    st.markdown(f'''<section class="wx-hero wx-{theme}"><div class="wx-scene">{scene}</div>
      <div><div class="wx-eyebrow">Taiwan weather intelligence</div><div class="wx-title">台灣氣象觀測所</div>
      <div class="wx-subtitle">{context} · 從全台氣象測站，看懂此刻天氣與未來一週變化。</div><div class="wx-live"><i></i>{escape(live_label)}</div></div>
      <div class="wx-hero-stat"><div class="wx-degree">{fmt(average,'°')}</div><div class="wx-subtitle">全台測站平均氣溫</div>
      <div class="wx-meta"><div><b>{len(frame)}</b><span>觀測測站</span></div><div><b>{len(warning_data['rows'])}</b><span>有效警特報</span></div></div>
      <div class="source-detail">最新觀測 · {escape(str(latest))}</div></div></section>''',unsafe_allow_html=True)

def status(data):
    label = f"{data['source']} · {data['status'].upper()}"
    if data['status'] == 'unavailable': st.error(label + '：' + (data['message'] or '目前無可用資料'))
    elif data['status'] == 'stale': st.warning(label + '：' + (data['message'] or '資料已過期，顯示上次成功資料'))
    elif data['status'] == 'demo': st.info(label + '：固定教學示範，非即時資料')
    else: st.success(label)
    st.caption('最後擷取：' + str(data.get('fetched_at') or '尚未取得'))
    if data.get('note'): st.caption(data['note'])

def forecast_cards(frame):
    weekdays='一二三四五六日'
    cards=[]
    for row in frame.to_dict('records'):
        date=pd.Timestamp(row['dataDate'])
        pop=row.get('precipitation_probability')
        cards.append(f'''<article class="forecast-card"><div class="day">週{weekdays[date.weekday()]}</div>
          <div class="date">{date.strftime('%m/%d')}</div><div class="icon">{weather_icon(row.get('weather'))}</div>
          <div class="temps">{fmt(row.get('mint'),'°')} / {fmt(row.get('maxt'),'°')}</div>
          <div class="rain">💧 {fmt(pop,'% ',0)}降雨</div></article>''')
    st.markdown('<div class="section-kicker">7-day outlook</div><div class="forecast-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)

def podium(frame, metric):
    column,unit,_=RANKING_METRICS[metric]
    top=frame.dropna(subset=[column]).nlargest(3,column).reset_index(drop=True)
    if len(top)<3: return
    cards=[]
    for index,medal,rank in [(1,'🥈',2),(0,'🥇',1),(2,'🥉',3)]:
        row=top.iloc[index]
        cards.append(f'''<article class="podium-card rank-{rank}"><div class="podium-medal">{medal}</div>
          <div class="podium-city">{escape(str(row['county']))}</div><div class="podium-value">{row[column]:.1f} {unit}</div>
          <div class="source-detail">{metric} · {int(row['station_count'])} 個測站</div></article>''')
    st.markdown('<div class="section-kicker">Top three counties</div><div class="podium">'+''.join(cards)+'</div>',unsafe_allow_html=True)

def ranking_highlights(items):
    cards=[]
    for label,row,column,unit in items:
        cards.append(f'''<article class="ranking-highlight"><div class="ranking-label">{escape(label)}</div>
          <div class="ranking-city" title="{escape(str(row['county']))}">{escape(str(row['county']))}</div>
          <div class="ranking-number">{row[column]:.1f}<span class="ranking-unit">{escape(unit)}</span></div></article>''')
    st.markdown('<div class="ranking-highlights">'+''.join(cards)+'</div>',unsafe_allow_html=True)

def quality_sources(sources):
    cards=[]
    for row in sources.to_dict('records'):
        status_name=str(row['狀態']).lower()
        cards.append(f'''<article class="source-card"><div class="source-head"><span>{escape(str(row['資料來源']))}</span>
          <span class="status-pill status-{escape(status_name)}">{escape(status_name.upper())}</span></div>
          <div class="source-detail">{int(row['筆數'])} 筆 · {escape(str(row['資料集']))}<br>更新 {escape(str(row['最後擷取']))}</div></article>''')
    st.markdown('<div class="source-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)

def quality_progress(quality):
    rows=[]
    for row in quality.to_dict('records'):
        rate=max(0,min(100,float(row['完整率'])))
        rows.append(f'''<div class="quality-row"><div class="quality-label"><span>{escape(str(row['欄位']))}</span>
          <b>{rate:.1f}%</b></div><div class="quality-track"><div class="quality-fill" style="width:{rate:.1f}%"></div></div></div>''')
    st.markdown('<div class="quality-list">'+''.join(rows)+'</div>',unsafe_allow_html=True)

def quality_highlights(station_count,regions,dates,warning_count,latest):
    try:
        observed=pd.Timestamp(latest)
        date_text=observed.strftime('%Y/%m/%d')
        time_text=observed.strftime('%H:%M')
    except (TypeError,ValueError):
        date_text,time_text='尚未取得','—'
    st.markdown(f'''<div class="quality-highlights">
      <article class="quality-highlight"><div class="quality-highlight-label">觀測測站</div><div class="quality-highlight-value">{station_count}</div></article>
      <article class="quality-highlight"><div class="quality-highlight-label">預報涵蓋</div><div class="quality-highlight-value">{regions} 區域 / {dates} 天</div></article>
      <article class="quality-highlight"><div class="quality-highlight-label">有效警特報</div><div class="quality-highlight-value">{warning_count}</div></article>
      <article class="quality-highlight"><div class="quality-highlight-label">最新觀測</div><div class="quality-highlight-date">{escape(date_text)}<span>{escape(time_text)}</span></div></article>
    </div>''',unsafe_allow_html=True)

@st.fragment(run_every=300 if auto else None)
def warning_strip():
    data = service.load('warnings')
    if data['status'] == 'unavailable':
        st.warning('警特報暫時無法取得：' + (data['message'] or '請稍後再試'))
    elif data['rows']:
        names = '、'.join(sorted({row['phenomenon'] for row in data['rows']}))
        st.warning(f"⚠️ 目前有效警特報：{names}（影響 {len({row['county'] for row in data['rows']})} 個縣市）")
    else:
        st.success('✅ 目前沒有有效的縣市天氣警特報')

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
    map_cols = st.columns(3)
    layer = map_cols[0].selectbox('資料圖層',list(LAYER_CONFIG),key='map_layer')
    display_mode = map_cols[1].selectbox('地圖呈現',['漸層內插','縣市色塊','測站圓點'],key='map_display')
    opacity = map_cols[2].slider('圖層透明度',.25,.90,.70,.05,key='map_opacity',
        disabled=display_mode=='測站圓點')
    filtered = filter_observations(frame,county,search,None if threshold=='所有氣溫' else int(threshold[:2]))
    config = LAYER_CONFIG[layer]
    values = layer_series(filtered,layer).dropna()
    a,b,c = st.columns(3)
    a.metric('符合條件測站',len(filtered))
    b.metric(f"平均{config['label']}",f"{values.mean():.1f} {config['unit']}" if len(values) else '—')
    c.metric(f"最高{config['label']}",f"{values.max():.1f} {config['unit']}" if len(values) else '—')
    st.caption('觀測時間：'+str(frame.observed_at.max())+' · 各測站觀測時間請見明細')
    point_cols = st.columns(2)
    overlay_points = point_cols[0].checkbox('疊加測站圓點',value=False,key='markers',
        disabled=display_mode=='測站圓點')
    markers = display_mode=='測站圓點' or overlay_points
    labels = point_cols[1].checkbox('顯示數值標籤',key='labels',disabled=not markers)
    warning_rows=service.load('warnings')['rows']
    map_state=st_folium(station_map(filtered,layer,labels,markers,display_mode,opacity,warning_rows),height=520,width=None,
        returned_objects=['last_object_clicked'],key=f'station_map_{layer}_{display_mode}')
    if display_mode=='漸層內插':
        st.caption(f"目前圖層：{config['label']}（{config['unit']}）。色帶由 CWA 測站實測值以距離加權內插產生，供視覺判讀，不是 CWA 官方網格預報。")
    elif display_mode=='縣市色塊':
        method = '單站最大值' if layer=='降雨量' else '測站平均值'
        st.caption(f"目前圖層：{config['label']}（{config['unit']}）。縣市色塊代表各縣市{method}；邊界使用專案內附的台灣開放資料。")
    else:
        st.caption(f"目前圖層：{config['label']}（{config['unit']}）。圓點與圖例直接使用 CWA 測站實測值。")
    if filtered.empty:
        st.info('沒有符合條件的測站，請調整篩選。')
        return
    lookup=filtered.set_index('station_id')
    if st.session_state.get('station') not in lookup.index:
        st.session_state.pop('station',None)
    clicked=(map_state or {}).get('last_object_clicked') if markers else None
    if clicked:
        clicked_id=nearest_station_id(filtered,clicked.get('lat'),clicked.get('lng'))
        if clicked_id in lookup.index:
            st.session_state['station']=clicked_id
    sid=st.selectbox('測站詳細資料',filtered.station_id.tolist(),format_func=lambda sid:f"{lookup.loc[sid,'station_name']} · {sid}",key='station')
    row=lookup.loc[sid]
    st.markdown(f"### 📍 {escape(str(row['station_name']))}｜{escape(str(row['county']))}{escape(str(row['town']))}")
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
    forecast_cards(frame)
    alert_data = service.load('warnings')
    regional_warnings = [row for row in alert_data['rows'] if row['county'] in REGION_COUNTIES[region]]
    selected_date = st.selectbox('查看日期',frame.dataDate.tolist(),format_func=lambda value:pd.Timestamp(value).strftime('%m/%d（%a）'),key='forecast_date')
    selected = frame.loc[frame.dataDate.eq(selected_date)].iloc[0]
    with st.container(border=True):
        left,right=st.columns([1,4])
        left.markdown(f"# {weather_icon(selected.get('weather'))}")
        right.subheader(str(selected.get('weather') or '天氣預報'))
        if pd.notna(selected.get('description')): right.caption(str(selected['description']))
        for message in outing_advice(selected,regional_warnings): right.write(message)
    a,b,c=st.columns(3)
    a.metric('預報最低溫',f'{frame.mint.min():.1f} °C')
    b.metric('預報最高溫',f'{frame.maxt.max():.1f} °C')
    c.metric('預報涵蓋',f'{len(frame)} 天')
    details=st.columns(5)
    detail_values=[
        ('降雨機率','precipitation_probability','%'),('最高體感','max_apparent_c','°C'),
        ('相對濕度','humidity_percent','%'),('紫外線','uv_index',''),('最大風速','wind_speed_mps','m/s')]
    for col,(label,key,unit) in zip(details,detail_values):
        value=selected.get(key)
        col.metric(label,'—' if pd.isna(value) else f'{value:g} {unit}'.strip())
    if len(frame)<7: st.warning('目前資料不足七天，僅顯示可用日期。')
    st.subheader('一週溫度趨勢')
    st.altair_chart(forecast_chart(frame),width="stretch")
    if frame.precipitation_probability.notna().any():
        st.subheader('一週降雨機率')
        st.altair_chart(precipitation_chart(frame),width='stretch')
    display=frame.assign(日夜溫差=frame.maxt-frame.mint).rename(columns={
        'dataDate':'日期','mint':'最低溫','maxt':'最高溫','weather':'天氣','precipitation_probability':'降雨機率 %',
        'min_apparent_c':'最低體感','max_apparent_c':'最高體感','humidity_percent':'濕度 %','uv_index':'紫外線',
        'wind_speed_mps':'風速 m/s','wind_direction':'風向'})
    visible=[column for column in ['日期','天氣','最低溫','最高溫','最低體感','最高體感','降雨機率 %','濕度 %','紫外線','風速 m/s','風向','日夜溫差'] if column in display and display[column].notna().any()]
    st.dataframe(display[visible],hide_index=True,width="stretch")
    st.download_button('下載此區 CSV',csv_bytes(frame),file_name=f'{region}-forecast.csv',mime='text/csv',key='forecast_csv')

@st.fragment(run_every=300 if auto else None)
def warning_panel():
    force=st.button('重新整理警特報',key='refresh_warnings')
    data=service.load('warnings',force=force)
    status(data)
    counties=['全台灣']+sorted({row['county'] for row in data['rows']})
    county=st.selectbox('警特報地區',counties,key='warning_county')
    frame=warning_frame(data['rows'],county)
    if frame.empty:
        st.success('目前沒有符合條件的有效警特報。')
        return
    st.metric('有效警特報',len(frame))
    for row in frame.to_dict('records'):
        with st.container(border=True):
            st.subheader(f"⚠️ {row['county']}｜{row['phenomenon']}{row['significance']}")
            st.caption(f"有效時間：{row.get('start_time') or '—'} ～ {row.get('end_time') or '—'}")
    st.caption('警特報資訊來自中央氣象署 W-C0033-001；實際防災行動請依中央氣象署及地方政府公告。')

@st.fragment(run_every=300 if auto else None)
def ranking_panel():
    obs_data = service.load('observations')
    warning_data = service.load('warnings')
    frame = county_summary(observations_frame(obs_data['rows']),warning_data['rows'])
    if frame.empty:
        st.info('目前沒有足夠的測站資料可建立縣市排行榜。')
        return
    hottest = frame.loc[frame.avg_temperature.idxmax()]
    coolest = frame.loc[frame.avg_temperature.idxmin()]
    rainiest = frame.loc[frame.max_precipitation.idxmax()]
    windiest = frame.loc[frame.max_wind_speed.idxmax()]
    ranking_highlights([
        ('平均最熱',hottest,'avg_temperature','°C'),('平均最涼',coolest,'avg_temperature','°C'),
        ('單站雨量最高',rainiest,'max_precipitation','mm'),('單站風速最高',windiest,'max_wind_speed','m/s')])
    st.subheader('縣市快速比較')
    county_names=frame.county.tolist()
    preferred=[name for name in ['臺北市','臺中市','高雄市'] if name in county_names]
    selected_counties=st.multiselect('選擇 2～3 個縣市',county_names,default=preferred[:3],max_selections=3,key='compare_counties')
    if selected_counties:
        compare=frame.set_index('county').loc[selected_counties]
        for col,(name,row) in zip(st.columns(len(compare)),compare.iterrows()):
            with col.container(border=True):
                st.markdown(f"### {name}")
                st.metric('平均氣溫',fmt(row.avg_temperature,' °C'))
                st.metric('平均濕度',fmt(row.avg_humidity,' %'))
                st.metric('最大雨量',fmt(row.max_precipitation,' mm'))
                st.metric('最大風速',fmt(row.max_wind_speed,' m/s'))
                st.caption(f"{int(row.station_count)} 個測站 · {int(row.warning_count)} 則警特報")
    else:
        st.info('請選擇縣市以建立比較卡。')
    metric = st.selectbox('排行榜項目',list(RANKING_METRICS),key='ranking_metric')
    podium(frame,metric)
    st.altair_chart(county_ranking_chart(frame,metric),width='stretch')
    display=frame.rename(columns={'county':'縣市','station_count':'測站數','avg_temperature':'平均氣溫 °C',
        'min_temperature':'最低氣溫 °C','max_temperature':'最高氣溫 °C','avg_humidity':'平均濕度 %',
        'max_precipitation':'最大雨量 mm','max_wind_speed':'最大風速 m/s','warning_count':'警特報數'})
    st.dataframe(display,hide_index=True,width='stretch')
    st.download_button('下載縣市彙整 CSV',csv_bytes(display),file_name='county-weather-ranking.csv',mime='text/csv',key='ranking_csv')
    st.caption('縣市數值由目前可用的 CWA 測站彙整；極值代表該縣市單一測站的目前最高觀測。')

@st.fragment(run_every=300 if auto else None)
def quality_panel():
    observation_data=service.load('observations')
    forecast_data=service.load('forecast')
    warning_data=service.load('warnings')
    sources,quality=data_quality_summary(observation_data,forecast_data,warning_data)
    obs_frame=observations_frame(observation_data['rows'])
    forecast_all=pd.DataFrame(forecast_data['rows'])
    latest=obs_frame.observed_at.dropna().max() if not obs_frame.empty else '—'
    regions=forecast_all.regionName.nunique() if 'regionName' in forecast_all else 0
    dates=forecast_all.dataDate.nunique() if 'dataDate' in forecast_all else 0
    quality_highlights(len(obs_frame),regions,dates,len(warning_data['rows']),latest)
    st.subheader('資料來源狀態')
    quality_sources(sources)
    st.subheader('觀測欄位完整率')
    quality_progress(quality)
    chart=alt.Chart(quality).mark_bar(color='#0ea5e9',cornerRadiusEnd=4).encode(
        x=alt.X('完整率:Q',title='完整率（%）',scale=alt.Scale(domain=[0,100])),
        y=alt.Y('欄位:N',title=None,sort='-x'),tooltip=['欄位:N','完整筆數:Q','總筆數:Q',alt.Tooltip('完整率:Q',format='.1f')]
    ).properties(height=280)
    st.altair_chart(chart,width='stretch')
    with st.expander('查看完整資料表'):
        st.dataframe(sources,hide_index=True,width='stretch')
        st.dataframe(quality,hide_index=True,width='stretch')
    st.info('fresh 代表目前快取有效；stale 代表上游暫時失敗並顯示上次成功資料；unavailable 代表目前沒有可用資料。')

render_hero()
warning_strip()
obs,forecast,rankings,warnings,quality=st.tabs(['即時氣象觀測','完整天氣預報','縣市排行榜','天氣警特報','資料品質'])
with obs: observation_panel()
with forecast: forecast_panel()
with rankings: ranking_panel()
with warnings: warning_panel()
with quality: quality_panel()
