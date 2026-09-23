import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import MODE, WINDY_KEY, CACHE_TTL, IS_VERCEL, IS_VERCEL
from service import load

async def refresh_loop():
    while True:
        await asyncio.gather(asyncio.to_thread(load,'forecast'),asyncio.to_thread(load,'observations'))
        await asyncio.sleep(CACHE_TTL)

@asynccontextmanager
async def lifespan(app):
    if IS_VERCEL:
        # Requests refresh the temporary cache through service.load().
        yield
        return
    if IS_VERCEL:
        # Each request refreshes expired cache through service.load().
        yield
        return
    task=asyncio.create_task(refresh_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app=FastAPI(title='Taiwan Weather Lab',lifespan=lifespan)
STATIC=Path(__file__).parent/'frontend'

@app.get('/api/config')
def config():
    return {'mode':MODE,'windy_key':WINDY_KEY,'refresh_seconds':300}

@app.get('/api/temperature/latest')
def latest(refresh:bool=False):
    data=load('observations',refresh)
    stations=data.pop('rows')
    observed=max((s['observed_at'] for s in stations),default=None)
    # Observation age differs from cache age: a successful download can still be old.
    if observed and data['status']=='fresh' and (datetime.now(timezone.utc)-datetime.fromisoformat(observed)).total_seconds()>7200:
        data['status']='stale'; data['message']='觀測時間已超過兩小時。'
    return dict(data,updated_at=observed,count=len(stations),stations=stations)

@app.get('/api/temperature/geojson')
def geojson():
    data=latest()
    return {'type':'FeatureCollection','source':data['source'],'status':data['status'],'features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[s['lon'],s['lat']]},'properties':s} for s in data['stations']]}

@app.get('/api/temperature/stations/{station_id}')
def station(station_id:str):
    data=latest()
    item=next((s for s in data['stations'] if s['station_id']==station_id),None)
    if not item:
        raise HTTPException(404,'找不到測站')
    return dict(item,source=data['source'],status=data['status'])

@app.get('/api/forecast')
def forecast(region:str|None=None,refresh:bool=False):
    import database
    data=load('forecast',refresh)
    data.pop('rows')
    # Filter the cached forecast with a parameterized SQL query.
    return dict(data,rows=database.get_forecast(region))

@app.get('/api/health')
def health():
    data=latest()
    return {'status':'ok' if data['count'] else 'degraded','cwa_cache_status':data['status'],'latest_cwa_time':data['updated_at'],'mode':MODE}

@app.get('/')
def index():
    return FileResponse(STATIC/'index.html')

app.mount('/assets',StaticFiles(directory=STATIC),name='assets')
