@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installing dependencies...
py -3 -m pip install -r requirements.txt -q
echo Building PIRAT.exe...
py -3 -m PyInstaller --noconfirm PIRAT.spec
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Done: dist\PIRAT.exe
explorer dist
pause
