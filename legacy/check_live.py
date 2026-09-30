import json
from config import FORECAST_ID, OBSERVATION_ID, ROOT
from fetch_weather import fetch_dataset
from parse_weather import parse_forecast, parse_observations
from concurrent.futures import ThreadPoolExecutor

def check(dataset, parser):
    try:
        data=fetch_dataset(dataset)
        rows=parser(data)
        print(dataset, 'success', 'records keys:',list(data.get('records',{})), 'valid rows:',len(rows))
        if rows:print('First normalized record:',json.dumps(rows[0],ensure_ascii=False))
        else:print('Schema sample:',json.dumps(data,ensure_ascii=False)[:8500])
        (ROOT/'work').mkdir(exist_ok=True)
        (ROOT/'work'/f'{dataset}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    except Exception as e: print(dataset,type(e).__name__,str(e))
with ThreadPoolExecutor() as pool:
    list(pool.map(lambda args:check(*args),[(FORECAST_ID,parse_forecast),(OBSERVATION_ID,parse_observations)]))
