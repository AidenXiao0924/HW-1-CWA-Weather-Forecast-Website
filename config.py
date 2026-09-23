import os
import tempfile
import tempfile
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
MODE = os.getenv('DATA_MODE', 'demo').lower()
if MODE not in {'demo', 'live'}:
    raise ValueError('DATA_MODE must be demo or live')
CWA_KEY = os.getenv('CWA_API_KEY', '')
WINDY_KEY = os.getenv('WINDY_API_KEY', '')
FORECAST_ID = os.getenv('CWA_FORECAST_DATASET', 'F-D0047-091')
OBSERVATION_ID = os.getenv('CWA_OBSERVATION_DATASET', 'O-A0001-001')
CACHE_TTL = max(60, int(os.getenv('CACHE_TTL_SECONDS', '600')))
IS_VERCEL = os.getenv('VERCEL') == '1'
# Serverless instances have a read-only application directory and temporary cache.
CACHE_DIR = Path(tempfile.gettempdir()) / 'taiwan-weather' if IS_VERCEL else ROOT
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / ('demo.db' if MODE == 'demo' else 'data.db')
REGIONS = ['北部地區', '中部地區', '南部地區', '東北部地區', '東部地區', '東南部地區']
REGION_COORDS = [(25.03,121.51),(24.14,120.68),(22.99,120.21),(24.75,121.75),(23.98,121.60),(22.76,121.14)]

REGION_COUNTIES = {
    '北部地區': ['基隆市','臺北市','新北市','桃園市','新竹市','新竹縣'],
    '中部地區': ['苗栗縣','臺中市','彰化縣','南投縣','雲林縣'],
    '南部地區': ['嘉義市','嘉義縣','臺南市','高雄市','屏東縣'],
    '東北部地區': ['宜蘭縣'], '東部地區': ['花蓮縣'], '東南部地區': ['臺東縣']
}
FORECAST_NOTE = 'CWA F-D0047-091 縣市預報彙整：區域最低取所屬縣市最低值、最高取最高值；不是氣象署直接發布的六區預報。以時段起始日歸類，首個不完整日略過。'
