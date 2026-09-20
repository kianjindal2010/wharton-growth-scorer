@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\wharton.exe" (
  echo The model is not installed yet. Run install_windows.bat first.
  exit /b 1
)

.venv\Scripts\wharton.exe predict
endlocal

