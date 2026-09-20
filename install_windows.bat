@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or 3.12 from python.org.
  exit /b 1
)

py -3.12 -m venv .venv 2>nul
if errorlevel 1 py -3.11 -m venv .venv
if errorlevel 1 (
  echo Could not create the Python environment.
  exit /b 1
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 exit /b 1

echo.
echo Installation complete.
echo Run run_wharton.bat or .venv\Scripts\wharton.exe predict
endlocal

