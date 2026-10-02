import csv
import json
import sqlite3
from contextlib import contextmanager
from config import DB_PATH, ROOT

FORECAST_OPTIONAL = [
    'temperature_c', 'humidity_percent', 'min_apparent_c', 'max_apparent_c',
    'precipitation_probability', 'uv_index', 'weather', 'weather_code',
    'wind_speed_mps', 'wind_direction', 'comfort', 'description'
]

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
          mint REAL NOT NULL, maxt REAL NOT NULL,
          temperature_c REAL, humidity_percent REAL, min_apparent_c REAL, max_apparent_c REAL,
          precipitation_probability REAL, uv_index REAL, weather TEXT, weather_code TEXT,
          wind_speed_mps REAL, wind_direction TEXT, comfort TEXT, description TEXT,
          UNIQUE(regionName,dataDate), CHECK(mint<=maxt));
        CREATE TABLE IF NOT EXISTS Metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS Stations (station_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS Warnings (warning_key TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')
        existing = {row[1] for row in db.execute('PRAGMA table_info(TemperatureForecasts)')}
        for column in FORECAST_OPTIONAL:
            if column not in existing:
                kind = 'REAL' if column in {'temperature_c','humidity_percent','min_apparent_c','max_apparent_c','precipitation_probability','uv_index','wind_speed_mps'} else 'TEXT'
                db.execute(f'ALTER TABLE TemperatureForecasts ADD COLUMN {column} {kind}')

def save_forecast(rows,meta,path=None):
    if not rows:
        raise ValueError('拒絕以空資料覆寫預報')
    initialize(path)
    normalized = [{key: row.get(key) for key in ['regionName','dataDate','mint','maxt'] + FORECAST_OPTIONAL} for row in rows]
    with connection(path) as db:
        db.execute('DELETE FROM TemperatureForecasts')
        columns = ['regionName','dataDate','mint','maxt'] + FORECAST_OPTIONAL
        db.executemany(f"INSERT INTO TemperatureForecasts({','.join(columns)}) VALUES({','.join(':'+c for c in columns)})", normalized)
        db.execute('INSERT OR REPLACE INTO Metadata VALUES (?,?)',('forecast',json.dumps(meta)))

def get_forecast(region=None,path=None):
    initialize(path)
    with connection(path) as db:
        sql='SELECT regionName,dataDate,mint,maxt,'+','.join(FORECAST_OPTIONAL)+' FROM TemperatureForecasts'
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

def save_warnings(rows,meta,path=None):
    initialize(path)
    with connection(path) as db:
        db.execute('DELETE FROM Warnings')
        db.executemany('INSERT INTO Warnings VALUES (?,?)', [
            ('|'.join(str(r.get(key, '')) for key in ('county','phenomenon','start_time','end_time')), json.dumps(r,ensure_ascii=False))
            for r in rows
        ])
        db.execute('INSERT OR REPLACE INTO Metadata VALUES (?,?)',('warnings',json.dumps(meta)))

def get_warnings(path=None):
    initialize(path)
    with connection(path) as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM Warnings ORDER BY warning_key')]

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
