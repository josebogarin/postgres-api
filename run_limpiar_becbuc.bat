@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0backend"
call .venv\Scripts\activate
cd /d "%~dp0."
set OUT=limpiar_becbuc_out.txt
echo ==== LIMPIEZA BASE becbuc ==== > %OUT%
echo. >> %OUT%
echo [1] backup fresco de becbuc (dump) >> %OUT%
if not exist "C:\backup_becbuc" mkdir "C:\backup_becbuc"
docker exec core-postgres pg_dump -U app_user --no-owner --clean --if-exists becbuc > "C:\backup_becbuc\becbuc_pre_drop.sql" 2>> %OUT%
for %%Z in ("C:\backup_becbuc\becbuc_pre_drop.sql") do echo   dump becbuc_pre_drop.sql = %%~zZ bytes >> %OUT%
echo. >> %OUT%
echo [2] DROP tablas/vistas obsoletas (con verificacion + rollback) >> %OUT%
python drop_becbuc_obsoletas.py >> %OUT% 2>&1
echo. >> %OUT%
echo [3] pytest tests/golden (deben ser 17 passed) >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [4] HTTP + prueba funcional (Excel usa las vistas que se mantienen) >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
python verify_puntajes_excel.py >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
