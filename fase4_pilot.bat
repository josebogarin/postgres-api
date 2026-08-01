@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0backend"
call .venv\Scripts\activate
cd /d "%~dp0."
set OUT=fase4_pilot_out.txt
echo ==== FASE 4 piloto: nucleo compartido (banderas) en becbuc-live.html ==== > %OUT%
echo. >> %OUT%
echo [A] aplicar extraccion del nucleo >> %OUT%
python patch_frontend_core.py >> %OUT% 2>&1
echo. >> %OUT%
echo [B] HTTP: /live y el nuevo core.js (deben ser 200) >> %OUT%
curl -s -o nul -w "  /live = %%{http_code}\n" http://localhost:8000/live >> %OUT% 2>&1
curl -s -o nul -w "  /static/js/becbuc-core.js = %%{http_code}\n" http://localhost:8000/static/js/becbuc-core.js >> %OUT% 2>&1
echo. >> %OUT%
echo [C] pytest tests/golden (sanity backend) >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
start "" "http://localhost:8000/live"
notepad %OUT%
