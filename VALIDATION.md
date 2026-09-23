# 驗證紀錄（2026-09-23）

- 使用使用者提供的 CWA 金鑰：O-A0001-001 成功，846 筆有效測站觀測。
- F-D0047-091 成功：六區各七天，共 42 筆彙整預報。
- F-A0010-001 在 datastore 與 fileapi 皆 HTTP 404；已於 README 說明替代來源與彙整定義。
- fetch → parse → database 真實資料流程成功，SQLite 已寫入。
- pytest：16 passed。
- Streamlit AppTest：無例外，七天表格與北部→中部選單切換通過。
- 瀏覽器：地圖、測站搜尋、詳情、七日圖表、來源提示與 Streamlit 畫面確認。
- JavaScript 語法檢查通過。
- Windy 無金鑰，未驗證氣象背景圖層；OpenStreetMap 替代底圖確認可用。
- 此電腦已安裝 .venv，日後執行 start.bat 即可。
- 壓縮備份不含 .env、資料庫、執行環境或日誌。解壓後執行 setup.bat，預設示範模式。

## 單一網站調整

已移除作業版導覽與 Streamlit 啟動項目；保留地圖網站的即時觀測及一週預報。requirements 與鎖定檔已移除 Streamlit 專用依賴。舊 app.py 僅留在忽略的 work/retired-streamlit 作為還原備份，不列入交付。
