import json
import requests
from config import CWA_KEY, FORECAST_ID, MODE, ROOT

def fetch_dataset(dataset):
    if not CWA_KEY:
        raise RuntimeError('尚未設定 CWA_API_KEY；請在 .env 填入金鑰。')
    try:
        response=requests.get(f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset}',params={'Authorization':CWA_KEY,'format':'JSON'},timeout=(10,30))
        response.raise_for_status()
        data=response.json()
    except (requests.RequestException,ValueError):
        # Do not expose response URLs, which contain credentials, in logs or browser.
        raise RuntimeError('氣象署資料取得失敗，請檢查網路、金鑰或資料集權限。') from None
    if str(data.get('success','true')).lower() != 'true':
        raise RuntimeError('氣象署回傳失敗狀態。')
    return data

if __name__ == '__main__':
    if MODE == 'demo':
        from demo_data import forecast
        data=forecast()
    else:
        data=fetch_dataset(FORECAST_ID)
    (ROOT/'weather_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Saved weather_data.json ({MODE})')
