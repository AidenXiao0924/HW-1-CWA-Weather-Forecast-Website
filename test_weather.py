from copy import deepcopy
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from demo_data import forecast, observations
from parse_weather import parse_forecast, parse_observations, number
import database
import service

@pytest.fixture(autouse=True)
def isolated_db(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setattr(service,'MODE','demo')
    service._attempts.clear(); service._errors.clear()

@pytest.mark.parametrize('value',[None,'X','-99','-999','NaN','Infinity','-21','51'])
def test_invalid_numbers(value):
    assert number(value) is None

def test_forecast_daily_aggregation():
    raw=forecast()
    elements=raw['records']['locations']['location'][0]['weatherElement']
    low=deepcopy(elements[0]['time'][0]);low['elementValue'][0]['value']='18'
    high=deepcopy(elements[1]['time'][0]);high['elementValue'][0]['value']='35'
    elements[0]['time'].append(low);elements[1]['time'].append(high)
    rows=parse_forecast(raw)
    assert len(rows)==42
    first=next(r for r in rows if r['regionName']=='北部地區' and r['dataDate']=='2026-09-23')
    assert (first['mint'],first['maxt'])==(18,35)

def test_missing_pair_is_excluded():
    raw=forecast();raw['records']['locations']['location'][0]['weatherElement'][0]['time'][0]['elementValue'][0]['value']='-99'
    assert len(parse_forecast(raw))==41

def test_observation_validation_and_wgs84():
    raw=observations()
    first=raw['records']['Station'][0]
    first['GeoInfo']['Coordinates'].insert(0,{'CoordinateName':'TWD67','StationLatitude':0,'StationLongitude':0})
    raw['records']['Station'][1]['WeatherElement']['AirTemperature']='NaN'
    raw['records']['Station'][2]['ObsTime']['DateTime']='invalid'
    rows=parse_observations(raw)
    assert len(rows)==10
    assert rows[0]['lat']==25.03

def test_sql_idempotency_and_parameterization():
    rows=parse_forecast(forecast());database.save_forecast(rows,{});database.save_forecast(rows,{})
    assert len(database.get_forecast())==42
    assert len(database.get_forecast('中部地區'))==7
    assert database.get_forecast("' OR 1=1 --")==[]
    with pytest.raises(ValueError): database.save_forecast([],{})
    assert len(database.get_forecast())==42

def test_failure_preserves_real_cache(monkeypatch):
    database.save_stations(parse_observations(observations()),{'source':'CWA','fetched_at':datetime.now(timezone.utc).isoformat()})
    monkeypatch.setattr(service,'MODE','live')
    def fail(_): raise RuntimeError('upstream failed')
    monkeypatch.setattr(service,'fetch_dataset',fail)
    result=service.load('observations',True)
    assert result['status']=='stale' and len(result['rows'])==12
    assert service.load('observations')['status']=='stale'

def test_live_failure_never_uses_demo(monkeypatch):
    monkeypatch.setattr(service,'MODE','live')
    def fail(_): raise RuntimeError('missing key')
    monkeypatch.setattr(service,'fetch_dataset',fail)
    result=service.load('forecast',True)
    assert result['status']=='unavailable' and result['rows']==[]

def test_endpoints():
    from backend import app
    with TestClient(app) as client:
        latest=client.get('/api/temperature/latest').json()
        assert latest['source']=='DEMO' and latest['count']==12
        geo=client.get('/api/temperature/geojson').json()
        assert geo['features'][0]['geometry']['coordinates']==[121.51,25.03]
        assert client.get('/api/temperature/stations/DEMO001').status_code==200
        assert client.get('/api/temperature/stations/no-such-station').status_code==404
        assert len(client.get('/api/forecast',params={'region':'中部地區'}).json()['rows'])==7
        assert 'CWA_API_KEY' not in client.get('/api/config').text
        assert client.get('/').status_code==200

def test_county_aggregation_and_partial_day():
    raw={'records':{'Locations':[{'Location':[]}]}}
    for county,low,high in [('臺北市',20,29),('新北市',18,31)]:
        elems=[]
        for key,value in [('最低溫度',low),('最高溫度',high)]:
            times=[]
            for day,hour in [(23,18),(24,6),(24,18)]:
                times.append({'StartTime':f'2026-09-{day}T{hour:02}:00:00+08:00','ElementValue':[{'MinTemperature' if key=='最低溫度' else 'MaxTemperature':str(value)}]})
            elems.append({'ElementName':key,'Time':times})
        raw['records']['Locations'][0]['Location'].append({'LocationName':county,'WeatherElement':elems})
    rows=parse_forecast(raw)
    assert rows==[{'regionName':'北部地區','dataDate':'2026-09-24','mint':18.0,'maxt':31.0}]
