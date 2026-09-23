import csv
import json
import sqlite3
from contextlib import contextmanager
from config import DB_PATH, ROOT

@contextmanager
def connection(path=None):
    db=sqlite3.connect(path or DB_PATH,timeout=15)
    db.row_factory=sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def initialize(path=None):
    with connection(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
          id INTEGER PRIMARY KEY, regionName TEXT NOT NULL, dataDate TEXT NOT NULL,
          mint REAL NOT NULL, maxt REAL NOT NULL, UNIQUE(regionName,dataDate), CHECK(mint<=maxt));
        CREATE TABLE IF NOT EXISTS Metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS Stations (station_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')

def save_forecast(rows,meta,path=None):
    if not rows:
        raise ValueError('拒絕以空資料覆寫預報')
    initialize(path)
    with connection(path) as db:
        db.execute('DELETE FROM TemperatureForecasts')
        db.executemany('INSERT INTO TemperatureForecasts(regionName,dataDate,mint,maxt) VALUES(:regionName,:dataDate,:mint,:maxt)',rows)
        db.execute('INSERT OR REPLACE INTO Metadata VALUES (?,?)',('forecast',json.dumps(meta)))

def get_forecast(region=None,path=None):
    initialize(path)
    with connection(path) as db:
        sql='SELECT regionName,dataDate,mint,maxt FROM TemperatureForecasts'
        args=()
        if region:
            sql+=' WHERE regionName = ?'; args=(region,)
        return [dict(r) for r in db.execute(sql+' ORDER BY dataDate,regionName',args)]

def get_regions(path=None):
    initialize(path)
    with connection(path) as db:
        return [r[0] for r in db.execute('SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName')]

def get_meta(key,path=None):
    initialize(path)
    with connection(path) as db:
        row=db.execute('SELECT value FROM Metadata WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else {}

def save_stations(rows,meta,path=None):
    if not rows:
        raise ValueError('拒絕以空資料覆寫測站')
    initialize(path)
    with connection(path) as db:
        db.execute('DELETE FROM Stations')
        db.executemany('INSERT INTO Stations VALUES (?,?)',[(r['station_id'],json.dumps(r,ensure_ascii=False)) for r in rows])
        db.execute('INSERT OR REPLACE INTO Metadata VALUES (?,?)',('observations',json.dumps(meta)))

def get_stations(path=None):
    initialize(path)
    with connection(path) as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM Stations')]

if __name__ == '__main__':
    from datetime import datetime, timezone
    from config import MODE, FORECAST_ID, FORECAST_NOTE
    with (ROOT/'weather_data.csv').open(encoding='utf-8-sig') as f:
        rows=[dict(r,mint=float(r['mint']),maxt=float(r['maxt'])) for r in csv.DictReader(f)]
    raw=json.loads((ROOT/'weather_data.json').read_text(encoding='utf-8'))
    if bool(raw.get('_demo')) != (MODE == 'demo'):
        raise SystemExit('Raw data mode differs from .env. Run fetch and parse again.')
    save_forecast(rows,{'dataset':FORECAST_ID,'note':FORECAST_NOTE if MODE=='live' and FORECAST_ID=='F-D0047-091' else None,'source':'DEMO' if MODE=='demo' else 'CWA','fetched_at':datetime.now(timezone.utc).isoformat(),'status':'demo' if MODE=='demo' else 'fresh'})
    print(f'Saved {len(rows)} rows into {DB_PATH.name}; regions: {get_regions()}')
