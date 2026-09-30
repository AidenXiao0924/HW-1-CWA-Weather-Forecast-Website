"""Presentation helpers: validated service rows -> Pandas, Folium, Altair."""
from html import escape
import pandas as pd
import folium
import altair as alt

OBS_COLUMNS = ['station_id','station_name','county','town','lat','lon','temperature_c','humidity_percent','pressure_hpa','wind_speed_mps','wind_direction_deg','precipitation_mm','observed_at']
FORECAST_COLUMNS = ['regionName','dataDate','mint','maxt']

def observations_frame(rows):
    return pd.DataFrame(rows).reindex(columns=OBS_COLUMNS)

def forecast_frame(rows, region):
    frame = pd.DataFrame(rows).reindex(columns=FORECAST_COLUMNS)
    return frame.loc[frame.regionName.eq(region)].sort_values('dataDate').head(7).reset_index(drop=True)

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

def station_map(frame, labels=False, markers=True):
    result = folium.Map(location=[23.7,121], zoom_start=7, tiles='OpenStreetMap', prefer_canvas=True)
    if markers:
        for row in frame.to_dict('records'):
            title = escape(str(row['station_name']))
            details = '<br>'.join(f'{escape(str(k))}: {escape(str(v))}' for k,v in row.items())
            folium.CircleMarker([row['lat'],row['lon']], radius=6, color='white', weight=1,
                fill=True, fill_color=temperature_color(row['temperature_c']), fill_opacity=.9,
                tooltip=folium.Tooltip(f"{title} {row['temperature_c']}°C", permanent=labels),
                popup=folium.Popup(details,max_width=320)).add_to(result)
    return result

def forecast_chart(frame):
    data = frame.melt(id_vars=['dataDate'],value_vars=['mint','maxt'],var_name='項目',value_name='溫度')
    data['項目'] = data['項目'].map({'mint':'最低溫','maxt':'最高溫'})
    return alt.Chart(data).mark_line(point=True).encode(
        x=alt.X('dataDate:T',title='日期',axis=alt.Axis(format='%m/%d')),
        y=alt.Y('溫度:Q',title='溫度 °C',scale=alt.Scale(zero=False)),
        color=alt.Color('項目:N',scale=alt.Scale(domain=['最低溫','最高溫'],range=['#2589ce','#e57b55'])),
        tooltip=[alt.Tooltip('dataDate:T',title='日期',format='%Y-%m-%d'),'項目:N',alt.Tooltip('溫度:Q',format='.1f')]
    ).properties(height=320)
