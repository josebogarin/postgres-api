@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0backend"
call .venv\Scripts\activate
cd /d "%~dp0."
set OUT=fase3_verif_out.txt
echo ==== FASE 3: extraer Excel de auditoria del God file ==== > %OUT%
echo. >> %OUT%
echo [A] estructura Excel ANTES >> %OUT%
python verify_audit_excel.py > audit_before_out.txt 2>&1
type audit_before_out.txt >> %OUT%
echo. >> %OUT%
echo [B] aplicar extraccion (funcion -> services/reportes/auditoria_excel.py) >> %OUT%
python extract_auditoria_excel.py >> %OUT% 2>&1
echo   esperando reload de uvicorn (9s)... >> %OUT%
timeout /t 9 /nobreak >nul
echo. >> %OUT%
echo [C] estructura Excel DESPUES >> %OUT%
python verify_audit_excel.py > audit_after_out.txt 2>&1
type audit_after_out.txt >> %OUT%
echo. >> %OUT%
echo [D] comparacion estructura ANTES vs DESPUES (debe ser identica) >> %OUT%
fc audit_before_out.txt audit_after_out.txt >> %OUT% 2>&1
echo. >> %OUT%
echo [E] pytest tests/golden (deben ser 17 passed) >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [F] HTTP >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
curl -s -o nul -w "  /api/v1/bets/ranking/2 = %%{http_code}\n" "http://localhost:8000/api/v1/bets/ranking/2" >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
