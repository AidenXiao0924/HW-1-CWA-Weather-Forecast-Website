"""Presentation helpers: validated service rows -> Pandas, Folium, Altair."""
from html import escape
from pathlib import Path
import json
import numpy as np
import pandas as pd
import folium
import altair as alt
from branca.colormap import StepColormap
from folium.plugins import Fullscreen

OBS_COLUMNS = ['station_id','station_name','county','town','lat','lon','temperature_c','humidity_percent','pressure_hpa','wind_speed_mps','wind_direction_deg','precipitation_mm','observed_at']
FORECAST_COLUMNS = [
    'regionName','dataDate','mint','maxt','temperature_c','humidity_percent',
    'min_apparent_c','max_apparent_c','precipitation_probability','uv_index',
    'weather','weather_code','wind_speed_mps','wind_direction','comfort','description'
]
WARNING_COLUMNS = ['county','phenomenon','significance','start_time','end_time']
COUNTY_GEOJSON = Path(__file__).parent / 'assets' / 'taiwan-counties.geojson'

LAYER_CONFIG = {
    '氣溫': {
        'column': 'temperature_c', 'unit': '°C', 'label': '氣溫',
        'index': [-10, 10, 15, 20, 25, 30, 35, 45],
        'colors': ['#2b6cb0','#3182ce','#38a169','#ecc94b','#ed8936','#e53e3e','#9b2c2c'],
    },
    '相對濕度': {
        'column': 'humidity_percent', 'unit': '%', 'label': '相對濕度',
        'index': [0, 40, 55, 70, 80, 90, 100],
        'colors': ['#dbeafe','#93c5fd','#60a5fa','#3b82f6','#2563eb','#1e3a8a'],
    },
    '降雨量': {
        'column': 'precipitation_mm', 'unit': 'mm', 'label': '降雨量',
        'index': [0, .1, 1, 5, 15, 40, 100],
        'colors': ['#e5e7eb','#bae6fd','#60a5fa','#2563eb','#7c3aed','#581c87'],
    },
    '風速': {
        'column': 'wind_speed_mps', 'unit': 'm/s', 'label': '風速',
        'index': [0, 1.5, 3.4, 5.5, 8, 12, 25],
        'colors': ['#dcfce7','#86efac','#4ade80','#facc15','#fb923c','#dc2626'],
    },
}

def observations_frame(rows):
    return pd.DataFrame(rows).reindex(columns=OBS_COLUMNS)

def forecast_frame(rows, region):
    frame = pd.DataFrame(rows).reindex(columns=FORECAST_COLUMNS)
    return frame.loc[frame.regionName.eq(region)].sort_values('dataDate').head(7).reset_index(drop=True)

def warning_frame(rows, county='全台灣'):
    frame = pd.DataFrame(rows).reindex(columns=WARNING_COLUMNS)
    if county != '全台灣' and not frame.empty:
        frame = frame.loc[frame.county.eq(county)]
    return frame.reset_index(drop=True)

def filter_observations(frame, county='全台灣', search='', minimum=None):
    result = frame
    if county != '全台灣':
        result = result.loc[result.county.eq(county)]
    if search.strip():
        names = result[['station_name','county','town']].fillna('').agg(' '.join, axis=1)
        result = result.loc[names.str.contains(search.strip(), regex=False, case=False)]
    if minimum is not None:
        result = result.loc[result.temperature_c.ge(minimum)]
    return result.reset_index(drop=True)

def csv_bytes(frame):
    return frame.to_csv(index=False).encode('utf-8-sig')

def temperature_color(t):
    for upper, color in [(10,'#2b6cb0'),(15,'#3182ce'),(20,'#38a169'),(25,'#ecc94b'),(30,'#ed8936'),(35,'#e53e3e')]:
        if t < upper:
            return color
    return '#9b2c2c'

def layer_series(frame, layer='氣溫'):
    config = LAYER_CONFIG[layer]
    return pd.to_numeric(frame[config['column']], errors='coerce')

def _layer_colormap(layer):
    config = LAYER_CONFIG[layer]
    return StepColormap(
        colors=config['colors'], index=config['index'],
        vmin=config['index'][0], vmax=config['index'][-1],
        caption=f"CWA 測站{config['label']}（{config['unit']}）",
    )

def _rgba_gradient(frame, layer, opacity=.72):
    """Create an IDW raster and fade pixels far from any observation station."""
    config=LAYER_CONFIG[layer]
    points=frame[['lat','lon',config['column']]].copy()
    for column in points.columns:
        points[column]=pd.to_numeric(points[column],errors='coerce')
    points=points.dropna().to_numpy(dtype=np.float32)
    if len(points)<2:
        return None
    south,north,west,east=21.75,25.45,119.25,122.15
    height,width=180,150
    lats=np.linspace(north,south,height,dtype=np.float32)
    lons=np.linspace(west,east,width,dtype=np.float32)
    lon_grid,lat_grid=np.meshgrid(lons,lats)
    targets=np.column_stack([lat_grid.ravel(),lon_grid.ravel()])
    interpolated=np.empty(len(targets),dtype=np.float32)
    nearest=np.empty(len(targets),dtype=np.float32)
    station_lat=points[:,0]
    station_lon=points[:,1]
    station_value=points[:,2]
    neighbours=min(12,len(points))
    for start in range(0,len(targets),1200):
        chunk=targets[start:start+1200]
        distance2=(chunk[:,None,0]-station_lat[None,:])**2+((chunk[:,None,1]-station_lon[None,:])*.92)**2
        indexes=np.argpartition(distance2,neighbours-1,axis=1)[:,:neighbours]
        selected=np.take_along_axis(distance2,indexes,axis=1)
        weights=1/(selected+1e-5)
        values=station_value[indexes]
        interpolated[start:start+len(chunk)]=(values*weights).sum(axis=1)/weights.sum(axis=1)
        nearest[start:start+len(chunk)]=np.sqrt(distance2.min(axis=1))
    colors=np.array([[int(color[i:i+2],16) for i in (1,3,5)] for color in config['colors']],dtype=np.float32)
    stops=np.array(config['index'][:-1],dtype=np.float32)
    rgba=np.zeros((len(targets),4),dtype=np.uint8)
    for channel in range(3):
        rgba[:,channel]=np.interp(interpolated,stops,colors[:,channel]).astype(np.uint8)
    fade=np.clip((.24-nearest)/.10,0,1)
    rgba[:,3]=(fade*255*float(opacity)).astype(np.uint8)
    return rgba.reshape(height,width,4),[[south,west],[north,east]]

def _add_gradient(result, frame, layer, opacity):
    raster=_rgba_gradient(frame,layer,opacity)
    if raster is None:
        return
    image,bounds=raster
    folium.raster_layers.ImageOverlay(
        image=image,bounds=bounds,opacity=1,interactive=False,cross_origin=False,
        zindex=1,name=f'{layer}漸層內插').add_to(result)

def _add_county_areas(result, frame, layer, opacity, colormap):
    if not COUNTY_GEOJSON.exists():
        return
    config=LAYER_CONFIG[layer]
    working=frame[['county',config['column']]].copy()
    working[config['column']]=pd.to_numeric(working[config['column']],errors='coerce')
    aggregation='max' if layer=='降雨量' else 'mean'
    values=getattr(working.groupby('county')[config['column']],aggregation)().to_dict()
    geojson=json.loads(COUNTY_GEOJSON.read_text(encoding='utf-8'))
    for feature in geojson['features']:
        county=feature['properties'].get('county')
        value=values.get(county)
        feature['properties']['layer_value']=None if pd.isna(value) else round(float(value),1)
        feature['properties']['layer_display']='無可用資料' if pd.isna(value) else f"{value:.1f} {config['unit']}"
    folium.GeoJson(
        geojson,name=f'縣市{config["label"]}',
        style_function=lambda feature:{
            'fillColor':'#334155' if feature['properties']['layer_value'] is None else colormap(feature['properties']['layer_value']),
            'color':'rgba(226,232,240,.8)','weight':1.2,'fillOpacity':float(opacity),
        },
        highlight_function=lambda _:{'weight':2.5,'color':'#ffffff','fillOpacity':min(1,float(opacity)+.12)},
        tooltip=folium.GeoJsonTooltip(fields=['county','layer_display'],aliases=['縣市','代表值'],sticky=False),
    ).add_to(result)

def _add_warning_boundaries(result, warnings):
    if not COUNTY_GEOJSON.exists() or not warnings:
        return
    grouped={}
    for item in warnings:
        county=item.get('county')
        phenomenon=item.get('phenomenon')
        if county and phenomenon:
            grouped.setdefault(county,set()).add(str(phenomenon))
    if not grouped:
        return
    geojson=json.loads(COUNTY_GEOJSON.read_text(encoding='utf-8'))
    geojson['features']=[feature for feature in geojson['features'] if feature['properties'].get('county') in grouped]
    for feature in geojson['features']:
        county=feature['properties']['county']
        feature['properties']['warning']='、'.join(sorted(grouped[county]))
    folium.GeoJson(
        geojson,name='有效警特報縣市',
        style_function=lambda _:{'fillOpacity':.04,'fillColor':'#fb7185','color':'#fb7185','weight':3,'dashArray':'7 5'},
        highlight_function=lambda _:{'fillOpacity':.14,'color':'#fecdd3','weight':4},
        tooltip=folium.GeoJsonTooltip(fields=['county','warning'],aliases=['警戒縣市','警特報'],sticky=False),
    ).add_to(result)

def nearest_station_id(frame, lat, lon, maximum_distance=.03):
    """Return the closest station for a marker click, ignoring unrelated map clicks."""
    if frame.empty or lat is None or lon is None:
        return None
    points=frame[['station_id','lat','lon']].copy()
    points['lat']=pd.to_numeric(points['lat'],errors='coerce')
    points['lon']=pd.to_numeric(points['lon'],errors='coerce')
    points=points.dropna(subset=['station_id','lat','lon'])
    if points.empty:
        return None
    distance=(points.lat-float(lat))**2+((points.lon-float(lon))*.92)**2
    index=distance.idxmin()
    return str(points.loc[index,'station_id']) if float(distance.loc[index]) <= maximum_distance**2 else None

def station_map(frame, layer='氣溫', labels=False, markers=True, display_mode='漸層內插', opacity=.72, warnings=None):
    config = LAYER_CONFIG[layer]
    colormap = _layer_colormap(layer)
    result = folium.Map(location=[23.7,121], zoom_start=7, tiles='OpenStreetMap', prefer_canvas=True)
    if display_mode=='漸層內插':
        _add_gradient(result,frame,layer,opacity)
    elif display_mode=='縣市色塊':
        _add_county_areas(result,frame,layer,opacity,colormap)
    _add_warning_boundaries(result,warnings or [])
    if markers:
        for row in frame.to_dict('records'):
            value = pd.to_numeric(pd.Series([row.get(config['column'])]), errors='coerce').iloc[0]
            if pd.isna(value) or pd.isna(row.get('lat')) or pd.isna(row.get('lon')):
                continue
            title = escape(str(row['station_name']))
            details = '<br>'.join(f'{escape(str(k))}: {escape(str(v))}' for k,v in row.items())
            folium.CircleMarker([row['lat'],row['lon']], radius=6, color='white', weight=1,
                fill=True, fill_color=colormap(value), fill_opacity=.9,
                tooltip=folium.Tooltip(f"{title} {value:g}{config['unit']}", permanent=labels),
                popup=folium.Popup(details,max_width=320)).add_to(result)
    colormap.add_to(result)
    Fullscreen(position='topright',title='全螢幕地圖',title_cancel='離開全螢幕',force_separate_button=True).add_to(result)
    return result

def county_summary(frame, warnings=None):
    """Aggregate current station observations into county-level comparison rows."""
    columns = ['county','station_count','avg_temperature','min_temperature','max_temperature',
        'avg_humidity','max_precipitation','max_wind_speed','warning_count']
    if frame.empty:
        return pd.DataFrame(columns=columns)
    numeric = frame.copy()
    for name in ['temperature_c','humidity_percent','precipitation_mm','wind_speed_mps']:
        numeric[name] = pd.to_numeric(numeric[name], errors='coerce')
    numeric = numeric.dropna(subset=['county'])
    summary = numeric.groupby('county', as_index=False).agg(
        station_count=('station_id','nunique'),
        avg_temperature=('temperature_c','mean'),
        min_temperature=('temperature_c','min'),
        max_temperature=('temperature_c','max'),
        avg_humidity=('humidity_percent','mean'),
        max_precipitation=('precipitation_mm','max'),
        max_wind_speed=('wind_speed_mps','max'),
    )
    alert_frame = warning_frame(warnings or [])
    if alert_frame.empty:
        summary['warning_count'] = 0
    else:
        counts = alert_frame.groupby('county').size().rename('warning_count')
        summary = summary.merge(counts, on='county', how='left')
        summary['warning_count'] = summary.warning_count.fillna(0).astype(int)
    number_columns = [column for column in columns if column not in {'county','station_count','warning_count'}]
    summary[number_columns] = summary[number_columns].round(1)
    return summary.reindex(columns=columns)

RANKING_METRICS = {
    '平均氣溫': ('avg_temperature','°C','#ef4444'),
    '最高氣溫': ('max_temperature','°C','#f97316'),
    '最大雨量': ('max_precipitation','mm','#3b82f6'),
    '最大風速': ('max_wind_speed','m/s','#8b5cf6'),
    '平均濕度': ('avg_humidity','%','#0891b2'),
}

def county_ranking_chart(summary, metric='平均氣溫'):
    column, unit, color = RANKING_METRICS[metric]
    data = summary.dropna(subset=[column]).sort_values(column, ascending=False)
    return alt.Chart(data).mark_bar(color=color, cornerRadiusEnd=4).encode(
        x=alt.X(f'{column}:Q', title=f'{metric}（{unit}）'),
        y=alt.Y('county:N', title='縣市', sort='-x'),
        tooltip=[alt.Tooltip('county:N', title='縣市'), alt.Tooltip(f'{column}:Q', title=metric, format='.1f'),
            alt.Tooltip('station_count:Q', title='測站數')],
    ).properties(height=max(360, len(data) * 25))

def data_quality_summary(observation_data, forecast_data, warning_data):
    """Return source-level status and observation field completeness for the quality UI."""
    sources = []
    for label, payload in [('即時觀測',observation_data),('天氣預報',forecast_data),('警特報',warning_data)]:
        sources.append({
            '資料來源': label, '狀態': payload.get('status','unavailable'),
            '筆數': len(payload.get('rows',[])), '最後擷取': payload.get('fetched_at') or '—',
            '資料集': payload.get('dataset') or '—',
        })
    frame = observations_frame(observation_data.get('rows',[]))
    fields = {
        '座標': ['lat','lon'], '氣溫': ['temperature_c'], '濕度': ['humidity_percent'],
        '氣壓': ['pressure_hpa'], '風速': ['wind_speed_mps'], '風向': ['wind_direction_deg'],
        '降雨量': ['precipitation_mm'], '觀測時間': ['observed_at'],
    }
    quality = []
    for label, columns in fields.items():
        complete = frame[columns].notna().all(axis=1).sum() if not frame.empty else 0
        total = len(frame)
        quality.append({'欄位':label,'完整筆數':int(complete),'總筆數':total,
            '完整率':round(complete / total * 100,1) if total else 0.0})
    return pd.DataFrame(sources), pd.DataFrame(quality)

def forecast_chart(frame):
    data = frame.melt(id_vars=['dataDate'],value_vars=['mint','maxt'],var_name='項目',value_name='溫度')
    data['項目'] = data['項目'].map({'mint':'最低溫','maxt':'最高溫'})
    return alt.Chart(data).mark_line(point=True).encode(
        x=alt.X('dataDate:T',title='日期',axis=alt.Axis(format='%m/%d')),
        y=alt.Y('溫度:Q',title='溫度 °C',scale=alt.Scale(zero=False)),
        color=alt.Color('項目:N',scale=alt.Scale(domain=['最低溫','最高溫'],range=['#2589ce','#e57b55'])),
        tooltip=[alt.Tooltip('dataDate:T',title='日期',format='%Y-%m-%d'),'項目:N',alt.Tooltip('溫度:Q',format='.1f')]
    ).properties(height=320)

def precipitation_chart(frame):
    data = frame.dropna(subset=['precipitation_probability'])
    return alt.Chart(data).mark_bar(color='#4da3d9',cornerRadiusTopLeft=4,cornerRadiusTopRight=4).encode(
        x=alt.X('dataDate:T',title='日期',axis=alt.Axis(format='%m/%d')),
        y=alt.Y('precipitation_probability:Q',title='降雨機率 %',scale=alt.Scale(domain=[0,100])),
        tooltip=[alt.Tooltip('dataDate:T',title='日期',format='%Y-%m-%d'),alt.Tooltip('precipitation_probability:Q',title='降雨機率',format='.0f')]
    ).properties(height=220)

def weather_icon(weather):
    text = str(weather or '')
    if '雷' in text: return '⛈️'
    if '雨' in text: return '🌧️'
    if '陰' in text: return '☁️'
    if '雲' in text: return '⛅'
    if '晴' in text: return '☀️'
    return '🌤️'

def outing_advice(row, warnings=None):
    """Create explainable, rule-based advice from one forecast row."""
    warnings = warnings or []
    advice = []
    pop = row.get('precipitation_probability')
    uvi = row.get('uv_index')
    apparent = row.get('max_apparent_c', row.get('maxt'))
    humidity = row.get('humidity_percent')
    wind = row.get('wind_speed_mps')
    if pd.notna(pop):
        if pop >= 70: advice.append('☔ 降雨機率高，建議攜帶雨具並預留交通時間。')
        elif pop >= 30: advice.append('🌂 有短暫雨機會，帶一把摺疊傘較安心。')
    if pd.notna(uvi):
        if uvi >= 8: advice.append('🧴 紫外線偏高，建議防曬、戴帽並避免長時間曝曬。')
        elif uvi >= 6: advice.append('🕶️ 紫外線較強，外出請做好基本防曬。')
    if pd.notna(apparent) and apparent >= 35: advice.append('🥤 體感炎熱，請補充水分並留意熱傷害。')
    elif pd.notna(apparent) and apparent <= 15: advice.append('🧥 體感偏涼，建議攜帶薄外套。')
    if pd.notna(humidity) and humidity >= 80: advice.append('💧 濕度偏高，建議穿著透氣衣物。')
    if pd.notna(wind) and wind >= 10: advice.append('💨 風勢較強，請固定隨身物品並注意行車安全。')
    if warnings:
        names = '、'.join(sorted({item['phenomenon'] for item in warnings}))
        advice.insert(0, f'⚠️ 此區目前有「{names}」，外出前請留意警特報。')
    return advice or ['✅ 目前沒有明顯不利條件，仍請留意即時天氣變化。']
