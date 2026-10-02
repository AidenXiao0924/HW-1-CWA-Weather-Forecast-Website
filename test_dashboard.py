from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pandas as pd
from streamlit.testing.v1 import AppTest
from dashboard import (observations_frame, filter_observations, forecast_frame, warning_frame,
    csv_bytes, station_map, forecast_chart, precipitation_chart, outing_advice,
    county_summary, county_ranking_chart, data_quality_summary, nearest_station_id)
from demo_data import observations, forecast
from parse_weather import parse_observations, parse_forecast
import service
import database
import pytest

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setattr(service,'MODE','demo')
    service._attempts.clear(); service._errors.clear()

def test_frames_filters_csv():
    frame=observations_frame(service.load('observations')['rows'])
    assert len(frame)==12
    assert len(filter_observations(frame,county='臺北市'))==1
    assert len(filter_observations(frame,search='阿里山'))==1
    assert filter_observations(frame,search='[').empty
    assert filter_observations(frame,minimum=35).empty
    selected=forecast_frame(service.load('forecast')['rows'],'中部地區')
    decoded=pd.read_csv(BytesIO(csv_bytes(selected)))
    assert len(decoded)==7 and decoded.regionName.unique().tolist()==['中部地區']
    assert csv_bytes(selected).startswith(b'\xef\xbb\xbf')
    assert forecast_frame([], '中部地區').empty

def test_folium_chart_without_windy(monkeypatch):
    monkeypatch.delenv('WINDY_API_KEY',raising=False)
    frame=observations_frame(parse_observations(observations()))
    frame.loc[0,'station_name']='<script>alert(1)</script>'
    html=station_map(frame).get_root().render()
    assert 'openstreetmap.org' in html and html.count('L.circleMarker(')==12
    assert '<script>alert(1)</script>' not in html
    assert 'L.circleMarker(' not in station_map(frame,markers=False).get_root().render()
    assert 'L.imageOverlay(' in station_map(frame,markers=False,display_mode='漸層內插').get_root().render()
    county_html=station_map(frame,markers=False,display_mode='縣市色塊').get_root().render()
    assert 'L.geoJson(' in county_html and r'\u81fa\u6771\u7e23' in county_html
    points_html=station_map(frame,display_mode='測站圓點').get_root().render()
    assert 'L.circleMarker(' in points_html and 'L.imageOverlay(' not in points_html
    assert 'L.control.fullscreen(' in points_html
    warning_html=station_map(frame,warnings=[{'county':'臺北市','phenomenon':'大雨'}]).get_root().render()
    assert r'\u5927\u96e8' in warning_html
    first=frame.iloc[0]
    assert nearest_station_id(frame,first.lat,first.lon)==first.station_id
    assert nearest_station_id(frame,0,0) is None
    assert r'\u76f8\u5c0d\u6fd5\u5ea6' in station_map(frame,'相對濕度').get_root().render()
    assert r'\u964d\u96e8\u91cf' in station_map(frame,'降雨量').get_root().render()
    assert r'\u98a8\u901f' in station_map(frame,'風速').get_root().render()
    spec=forecast_chart(forecast_frame(parse_forecast(forecast()),'中部地區')).to_dict()
    assert 'tooltip' in spec['encoding'] and spec['mark']['type']=='line'
    rain=precipitation_chart(forecast_frame(parse_forecast(forecast()),'中部地區')).to_dict()
    assert rain['mark']['type']=='bar'

def test_warning_filter_and_outing_advice():
    alerts=[{'county':'臺北市','phenomenon':'高溫','significance':'特報','start_time':'a','end_time':'b'}]
    assert len(warning_frame(alerts,'臺北市'))==1
    row={'precipitation_probability':80,'uv_index':9,'max_apparent_c':36,'humidity_percent':85,'wind_speed_mps':11}
    advice=outing_advice(row,alerts)
    assert any('雨具' in item for item in advice)
    assert any('紫外線' in item for item in advice)
    assert any('高溫' in item for item in advice)

def test_county_ranking_and_data_quality():
    obs_data=service.load('observations')
    warning_data={'status':'fresh','rows':[{'county':'臺北市','phenomenon':'高溫','significance':'特報','start_time':'a','end_time':'b'}],
        'fetched_at':'now','dataset':'warnings'}
    summary=county_summary(observations_frame(obs_data['rows']),warning_data['rows'])
    taipei=summary.loc[summary.county.eq('臺北市')].iloc[0]
    assert taipei.station_count==1 and taipei.warning_count==1
    assert county_ranking_chart(summary,'最大雨量').to_dict()['mark']['type']=='bar'
    sources,quality=data_quality_summary(obs_data,service.load('forecast'),warning_data)
    assert len(sources)==3 and {'欄位','完整率'}.issubset(quality.columns)
    assert quality['完整率'].between(0,100).all()

def test_storm_and_concurrent_sessions(monkeypatch):
    monkeypatch.setattr(service,'MODE','live')
    calls=[]
    def fetch(_):
        calls.append(1)
        return forecast()
    monkeypatch.setattr(service,'fetch_dataset',fetch)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda _: service.load('forecast',True),range(5)))
    assert len(calls)==1 and all(len(r['rows'])==42 for r in results)

def test_old_observations_stale_after_success(monkeypatch):
    monkeypatch.setattr(service,'MODE','live')
    monkeypatch.setattr(service,'fetch_dataset',lambda _:observations())
    assert service.load('observations')['status']=='stale'

def test_forecast_failure_retains_cache(monkeypatch):
    service.load('forecast')
    monkeypatch.setattr(service,'MODE','live')
    service._attempts.clear()
    def fail(_): raise RuntimeError('upstream unavailable')
    monkeypatch.setattr(service,'fetch_dataset',fail)
    data=service.load('forecast',True)
    assert data['status']=='stale' and len(data['rows'])==42

def test_streamlit_navigation_and_empty_filter(monkeypatch):
    monkeypatch.delenv('WINDY_API_KEY',raising=False)
    app=AppTest.from_file('streamlit_app.py',default_timeout=30).run()
    assert not app.exception
    assert len(app.tabs)==5
    assert len(app.multiselect)==1 and len(app.multiselect(key='compare_counties').value)>=2
    assert app.selectbox(key='map_display').value=='漸層內插'
    app.selectbox(key='map_display').select('縣市色塊').run()
    assert not app.exception
    app.selectbox(key='map_display').select('測站圓點').run()
    assert not app.exception
    app.selectbox(key='region').select('中部地區').run()
    assert not app.exception
    assert any(len(item.value)==7 and '日期' in item.value for item in app.dataframe)
    app.text_input(key='search').set_value('no-such-station').run()
    assert not app.exception
    assert any('沒有符合' in item.value for item in app.info)

def test_unavailable_ui(monkeypatch):
    monkeypatch.setattr(service,'MODE','live')
    def fail(_): raise RuntimeError('upstream unavailable')
    monkeypatch.setattr(service,'fetch_dataset',fail)
    app=AppTest.from_file('streamlit_app.py',default_timeout=30).run()
    assert not app.exception and len(app.error)==3
