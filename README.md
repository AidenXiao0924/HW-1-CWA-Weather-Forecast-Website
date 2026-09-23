# Taiwan Weather Lab / 台灣氣象觀測所

單一天氣地圖網站，整合即時測站觀測與一週預報。

## 開啟網站

此電腦已安裝執行環境，雙擊 `start.bat`，開啟 http://127.0.0.1:8000 。啟動程式只啟動這一個網站。

新電腦首次使用請先執行 `setup.bat`（Python 3.11 以上），再執行 `start.bat`。停止服務使用 `stop.bat`；修改 `.env` 後需重新啟動。

## 功能

- 即時觀測：CWA 氣溫圓點、測站明細、搜尋、縣市與溫度篩選。
- Windy 背景：依金鑰方案切換風場與氣溫等圖層。未設定時使用 OpenStreetMap。
- 一週預報：六區選單、每日最高最低溫圖表、表格及 CSV 匯出。
- 後端每 10 分鐘更新，前端每 5 分鐘更新；失敗時保留 SQLite 快取。
- CWA 實測資料與 Windy 模型背景分開顯示。

## 設定

保留自己的 `.env`，不要將金鑰提交至版本控制。新安裝可複製 `.env.example`：

```env
DATA_MODE=live
CWA_API_KEY=你的氣象署金鑰
WINDY_API_KEY=你的WindyMapForecast金鑰
CWA_FORECAST_DATASET=F-D0047-091
CWA_OBSERVATION_DATASET=O-A0001-001
CACHE_TTL_SECONDS=600
```

CWA 金鑰僅在後端使用；Windy 是瀏覽器端金鑰。Testing 方案的可用氣象圖層有限。

設定 `DATA_MODE=demo` 可使用明確標示的固定模擬資料，使用獨立 demo.db；正式資料使用 data.db。live 失敗不會改用示範資料。

## 技術與套件

後端：Python、FastAPI、Uvicorn、Requests、python-dotenv，以及內建 sqlite3。
前端：HTML、CSS、原生 JavaScript、Leaflet、Windy Map Forecast API。
測試：pytest、HTTPX。網站不再依賴 Streamlit、Pandas、Altair 或 Folium。

## 資料處理與 API

`fetch_weather.py` 取得 JSON；`parse_weather.py` 驗證及彙整；`database.py` 保存 SQLite；`service.py` 管理快取；`backend.py` 提供 API 與 frontend/ 靜態網頁。

需要展示資料處理步驟時，可依序執行：

```powershell
.\.venv\Scripts\python.exe fetch_weather.py
.\.venv\Scripts\python.exe parse_weather.py
.\.venv\Scripts\python.exe database.py
```

- `/api/temperature/latest`：測站觀測。
- `/api/temperature/geojson`：GeoJSON。
- `/api/temperature/stations/{station_id}`：測站明細。
- `/api/forecast?region=中部地區`：SQLite 區域預報。
- `/api/health`：健康狀態。
- `/docs`：API 文件。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

僅供本機執行，預設綁定 127.0.0.1。TDD 中的歷史回放、Redis、Postgres 等未來階段尚未實作。原始作業文件保留於本機專案，不隨儲存庫發布。

## 原作業資料集差異（2026-09-23 實測）

老師圖片的 F-A0010-001 在 datastore 與 fileapi 皆回傳 HTTP 404。F-D0047-091 與 O-A0001-001 使用同一組金鑰均成功，因此不是金鑰失效。

本版採 F-D0047-091 縣市預報彙整，介面會揭露此差異。六區分組是本專案教學定義，非宣稱 CWA 官方六區統計：

| 區域 | 縣市 |
|---|---|
| 北部 | 基隆、臺北、新北、桃園、新竹市、新竹縣 |
| 中部 | 苗栗、臺中、彰化、南投、雲林 |
| 南部 | 嘉義市、嘉義縣、臺南、高雄、屏東 |
| 東北部 | 宜蘭 |
| 東部 | 花蓮 |
| 東南部 | 臺東 |

離島不納入本島六區。每區每日最低值取所屬縣市各時段最低值，最高值取最高值。以時段起始日歸類（18:00 夜間時段歸當日），不是午夜到午夜的精確日界；首個只有夜間的部分日略過，保留接下來七個有日間及夜間時段的日期。若老師要求指定舊資料集，可將 CWA_FORECAST_DATASET 改回 F-A0010-001；目前 404 仍需由老師確認正確代碼。
