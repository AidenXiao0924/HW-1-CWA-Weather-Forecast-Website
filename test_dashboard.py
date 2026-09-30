from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pandas as pd
from streamlit.testing.v1 import AppTest
from dashboard import observations_frame, filter_observations, forecast_frame, csv_bytes, station_map, forecast_chart
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
    spec=forecast_chart(forecast_frame(parse_forecast(forecast()),'中部地區')).to_dict()
    assert 'tooltip' in spec['encoding'] and spec['mark']['type']=='line'

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
    assert len(app.tabs)==2
    app.selectbox(key='region').select('中部地區').run()
    assert not app.exception
    assert any(len(item.value)==7 and 'regionName' in item.value for item in app.dataframe)
    app.text_input(key='search').set_value('no-such-station').run()
    assert not app.exception
    assert any('沒有符合' in item.value for item in app.info)

def test_unavailable_ui(monkeypatch):
    monkeypatch.setattr(service,'MODE','live')
    def fail(_): raise RuntimeError('upstream unavailable')
    monkeypatch.setattr(service,'fetch_dataset',fail)
    app=AppTest.from_file('streamlit_app.py',default_timeout=30).run()
    assert not app.exception and len(app.error)==2
