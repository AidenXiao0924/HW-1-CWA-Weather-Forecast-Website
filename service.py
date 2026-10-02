import threading
from datetime import datetime, timezone
from config import MODE, FORECAST_ID, OBSERVATION_ID, WARNING_ID, CACHE_TTL, FORECAST_NOTE
import database as db
from fetch_weather import fetch_dataset
from parse_weather import parse_forecast, parse_observations, parse_warnings

_locks={name:threading.Lock() for name in ('forecast','observations','warnings')}
_attempts={}
_errors={}

def load(kind, force=False):
    handlers = {
        'forecast': (db.get_forecast, db.save_forecast, parse_forecast, FORECAST_ID),
        'observations': (db.get_stations, db.save_stations, parse_observations, OBSERVATION_ID),
        'warnings': (db.get_warnings, db.save_warnings, parse_warnings, WARNING_ID),
    }
    if kind not in handlers:
        raise ValueError(f'Unknown weather data kind: {kind}')
    read, save, parser, dataset = handlers[kind]
    with _locks[kind]:
        rows,meta=read(),db.get_meta(kind)
        now=datetime.now(timezone.utc)
        try:
            age=(now-datetime.fromisoformat(meta['fetched_at'])).total_seconds()
        except (ValueError,KeyError,TypeError):
            age=float('inf')
        should_fetch=force or (not rows and not meta.get('fetched_at')) or age>=CACHE_TTL
        # Avoid storms, including repeated manual refreshes after upstream failure.
        if should_fetch and (now.timestamp()-_attempts.get(kind,0))>=30:
            _attempts[kind]=now.timestamp()
            try:
                if MODE=='demo':
                    import demo_data
                    payload=getattr(demo_data, kind)()
                else:
                    payload=fetch_dataset(dataset)
                parsed=parser(payload)
                if not parsed and kind != 'warnings':
                    raise ValueError('資料格式不符或沒有有效資料；保留上次成功資料。')
                if kind=='forecast':
                    from config import REGIONS
                    if set(r['regionName'] for r in parsed) != set(REGIONS):
                        raise ValueError('預報缺少六大區域；請確認預報資料集格式。')
                meta={'dataset':dataset,'note':FORECAST_NOTE if kind=='forecast' and FORECAST_ID=='F-D0047-091' and MODE=='live' else None,'source':'DEMO' if MODE=='demo' else 'CWA','fetched_at':now.isoformat(),'status':'demo' if MODE=='demo' else 'fresh'}
                save(parsed,meta)
                rows=read(); _errors.pop(kind,None)
            except (RuntimeError,ValueError) as exc:
                _errors[kind]=str(exc)
        has_snapshot = bool(rows) or bool(meta.get('fetched_at'))
        status='demo' if MODE=='demo' and has_snapshot else ('stale' if has_snapshot and kind in _errors else 'fresh' if has_snapshot else 'unavailable')
        # Observation age is independent of download/cache age (formerly in FastAPI).
        if kind == 'observations' and rows and status == 'fresh':
            latest = max(datetime.fromisoformat(r['observed_at']) for r in rows)
            if (now-latest).total_seconds() > 7200:
                status = 'stale'
                _errors[kind] = '觀測時間已超過兩小時。'
        return {'source':meta.get('source','CWA' if MODE=='live' else 'DEMO'),'status':status,'fetched_at':meta.get('fetched_at'),'note':meta.get('note'),'dataset':meta.get('dataset'),'message':_errors.get(kind),'rows':rows}
