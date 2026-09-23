@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv .venv
  goto install
)
where python >nul 2>nul
if not errorlevel 1 (
  python -m venv .venv
  goto install
)
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
  "%BUNDLED%" -m venv .venv
  goto install
)
echo Please install Python 3.11 or newer from python.org.
pause
exit /b 1
:install
if not exist ".venv\Scripts\python.exe" exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo Installation failed. Check network and try again.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
echo Setup complete. Double click start.bat.
pause
