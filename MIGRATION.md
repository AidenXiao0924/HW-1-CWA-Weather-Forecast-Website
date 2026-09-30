# Migration Summary — 2026-09-30

## 分析依據

讀取本機 source/HW10_Weather 與發布工作副本的 Python、frontend、requirements、啟動腳本、README 與部署文件。source 不是 Git repository，發布工作副本 main 沒有任何 commit 或 remote；兩者不是 GitHub 最新 checkout。工作副本 config/backend 發現上次部署加入的重複 import 與 Vercel 分支，正式 config 已清理，backend 原文封存。未把過去聊天當作目前程式碼版本。

本次修改位於 Documents/Codex/2026-09-23/new-chat/work/git-release/HW10_Weather。source/HW10_Weather 不在本次可寫入範圍，未覆寫；原稿另存忽略的 work/before-streamlit。

## 檔案與功能對照

| 類型 | 檔案／變化 |
|---|---|
| 新增 | streamlit_app.py、dashboard.py、test_dashboard.py、MIGRATION.md、legacy/README.md |
| 修改 | config.py、service.py、launcher.py、setup.bat、requirements*.txt、.env.example、.gitignore、README.md、VALIDATION.md、test_weather.py |
| 原樣保留 | fetch_weather.py、parse_weather.py、database.py、demo_data.py、start.bat、stop.bat |
| 移至 legacy | backend.py、index.py、frontend/、VERCEL.md |
| 刪除功能 | 正式 FastAPI endpoint 與 endpoint tests；舊程式不永久刪除 |

FastAPI routing / REST HTTP 改由 Streamlit 直接呼叫 service.load。
JavaScript 搜尋／篩選／明細改為 Streamlit widgets 與 Pandas；Blob CSV 改 st.download_button。
手寫 Leaflet 改 Folium 分色 CircleMarker、popup 與 streamlit-folium；Leaflet 仍為 Folium 的底層實作，並非自製 JavaScript。
SVG 折線圖改 Altair：雙線、圖例、Tooltip、日期／°C 座標與自適應寬度。
舊 parser、校驗、SQL constraints、資料表、Requests error sanitization、固定 fixtures、快取及節流保留。
觀測時間超過兩小時的 stale 判定從 backend 移到 service，確保不依賴 FastAPI。

## 互動與快取調整

只保留一套正式 Streamlit UI。兩 tabs 均會執行資料讀取，service TTL 可避免重複上游呼叫。fragment 每五分鐘在活躍 session 檢查，沒有常駐 refresh loop。
地圖 popup 與原生測站明細選單獨立；returned_objects=[] 避免拖圖觸發資料層重跑。重設地圖可重新整理頁面。
SQLite 是持久快照（視主機磁碟保障）；service 管理 TTL／Lock／last-known-good／30秒節流；不用 st.cache_data 遮蔽 service 狀態。跨程序不共享 Lock。
Windy 正式功能退出，沒有 key 仍能用 OSM 測站地圖；歷史模型 UI 只在 legacy。

## 最終架構與技術

CWA → Requests → JSON → Python parsing/validation → service ↔ SQLite → Pandas → Streamlit → Folium / Altair / DataFrame / CSV。
Python、Requests、python-dotenv、SQLite、Pandas、Streamlit、Folium、streamlit-folium、Altair；pytest + Streamlit AppTest。
Pandas 在查詢與顯示之間，不為了示意圖順序重寫既有 parser 或 schema。

## 驗證／啟動／部署

pytest 最終 22 passed；詳見 VALIDATION.md。Streamlit 實際啟動於 127.0.0.1:8502 並確認 OSM 地圖與測站、預報畫面。
安裝 requirements.txt 後執行 `python -m streamlit run streamlit_app.py`；Windows setup/start/stop 腳本已銜接。
部署使用 Streamlit Community Cloud 或持續執行的主機；指定 streamlit_app.py 與 secrets，不沿用 Vercel FastAPI Functions。新版尚未部署。
Live 有金鑰，但 CWA 網路連線失敗，未驗證真實取得成功。以 mock 測試 Live error/cache 分支並非真實 API 成功。

## Git 交付狀態

目前 branch：main。此工作副本沒有既有 commit（unborn main），remote 為空。
未猜測 remote 或身分、未建立新 GitHub repository。所有修改保留本機。
預定 commit message：refactor: migrate weather dashboard from FastAPI to Streamlit。
實際 commit / push 結果另見 VALIDATION.md 最後紀錄。

需要使用者提供有既有歷史／remote 的正確本機 clone（並設好 Git name/email），再將此次檔案同步進該 clone，檢查 diff、測試、commit 並推送既有 branch。不要把本工作副本當作既有 GitHub 歷史強制推送。
