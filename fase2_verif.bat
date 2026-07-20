@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
set OUT=fase2_verif_out.txt
echo ==== FASE 2: repo pilot ranking + portabilidad ==== > %OUT%
echo. >> %OUT%
echo [A] smoke test portabilidad (tools/db_env.py) >> %OUT%
python tools\db_env.py >> %OUT% 2>&1
echo. >> %OUT%
echo [B] capturar ranking ANTES del patch >> %OUT%
curl -s "http://localhost:8000/api/v1/bets/ranking/2" > ranking_before.json 2>>%OUT%
for %%Z in (ranking_before.json) do echo   ranking_before.json = %%~zZ bytes >> %OUT%
echo. >> %OUT%
echo [C] aplicar patch (wire endpoint ranking -> ranking_repo) >> %OUT%
python patch_ranking.py >> %OUT% 2>&1
echo   esperando reload de uvicorn (8s)... >> %OUT%
timeout /t 8 /nobreak >nul
echo. >> %OUT%
echo [D] capturar ranking DESPUES del patch >> %OUT%
curl -s "http://localhost:8000/api/v1/bets/ranking/2" > ranking_after.json 2>>%OUT%
for %%Z in (ranking_after.json) do echo   ranking_after.json = %%~zZ bytes >> %OUT%
echo. >> %OUT%
echo [E] comparacion ANTES vs DESPUES (debe decir: no se encontraron diferencias) >> %OUT%
fc ranking_before.json ranking_after.json >> %OUT% 2>&1
echo. >> %OUT%
echo [F] pytest tests/golden (deben ser 17 passed) >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [G] HTTP portal + ranking >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
curl -s -o nul -w "  /api/v1/bets/ranking/2 = %%{http_code}\n" "http://localhost:8000/api/v1/bets/ranking/2" >> %OUT% 2>&1
del ranking_before.json ranking_after.json 2>nul
echo ---- FIN ---- >> %OUT%
notepad %OUT%
