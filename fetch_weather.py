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
    except requests.ConnectionError as exc:
        # Requests includes the credential in exception URLs. Never show it.
        if 'WinError 10013' in str(exc):
            raise RuntimeError('目前執行環境阻擋連線至氣象署（Windows 錯誤 10013）；尚無法驗證金鑰。') from None
        raise RuntimeError('無法連線至氣象署；請檢查網路連線。') from None
    except requests.Timeout:
        raise RuntimeError('連線至氣象署逾時；請稍後再試。') from None
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 403):
            raise RuntimeError('氣象署拒絕授權；請檢查金鑰及資料集權限。') from None
        raise RuntimeError(f'氣象署回應 HTTP {status or "錯誤"}；請檢查資料集或稍後再試。') from None
    except (requests.RequestException, ValueError):
        raise RuntimeError('氣象署回應無法解析；請稍後再試。') from None
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
