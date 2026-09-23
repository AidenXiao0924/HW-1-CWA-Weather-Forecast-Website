import threading
from datetime import datetime, timezone
from config import MODE, FORECAST_ID, OBSERVATION_ID, CACHE_TTL, FORECAST_NOTE
import database as db
from fetch_weather import fetch_dataset
from parse_weather import parse_forecast, parse_observations

_locks={name:threading.Lock() for name in ('forecast','observations')}
_attempts={}
_errors={}

def load(kind, force=False):
    read=db.get_forecast if kind=='forecast' else db.get_stations
    with _locks[kind]:
        rows,meta=read(),db.get_meta(kind)
        now=datetime.now(timezone.utc)
        try:
            age=(now-datetime.fromisoformat(meta['fetched_at'])).total_seconds()
        except (ValueError,KeyError,TypeError):
            age=float('inf')
        should_fetch=force or not rows or age>=CACHE_TTL
        # Avoid storms, including repeated manual refreshes after upstream failure.
        if should_fetch and (now.timestamp()-_attempts.get(kind,0))>=30:
            _attempts[kind]=now.timestamp()
            try:
                if MODE=='demo':
                    import demo_data
                    payload=demo_data.forecast() if kind=='forecast' else demo_data.observations()
                else:
                    payload=fetch_dataset(FORECAST_ID if kind=='forecast' else OBSERVATION_ID)
                parsed=(parse_forecast if kind=='forecast' else parse_observations)(payload)
                if not parsed:
                    raise ValueError('資料格式不符或沒有有效資料；保留上次成功資料。')
                if kind=='forecast':
                    from config import REGIONS
                    if set(r['regionName'] for r in parsed) != set(REGIONS):
                        raise ValueError('預報缺少六大區域；請確認預報資料集格式。')
                meta={'dataset':FORECAST_ID if kind=='forecast' else OBSERVATION_ID,'note':FORECAST_NOTE if kind=='forecast' and FORECAST_ID=='F-D0047-091' and MODE=='live' else None,'source':'DEMO' if MODE=='demo' else 'CWA','fetched_at':now.isoformat(),'status':'demo' if MODE=='demo' else 'fresh'}
                (db.save_forecast if kind=='forecast' else db.save_stations)(parsed,meta)
                rows=read(); _errors.pop(kind,None)
            except (RuntimeError,ValueError) as exc:
                _errors[kind]=str(exc)
        status='demo' if MODE=='demo' and rows else ('stale' if rows and (kind in _errors or age>=CACHE_TTL and should_fetch and meta.get('fetched_at')!=now.isoformat()) else 'fresh' if rows else 'unavailable')
        return {'source':meta.get('source','CWA' if MODE=='live' else 'DEMO'),'status':status,'fetched_at':meta.get('fetched_at'),'note':meta.get('note'),'dataset':meta.get('dataset'),'message':_errors.get(kind),'rows':rows}
