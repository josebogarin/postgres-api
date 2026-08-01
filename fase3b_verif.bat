@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0backend"
call .venv\Scripts\activate
cd /d "%~dp0."
set OUT=fase3b_verif_out.txt
echo ==== FASE 3b: extraer exportar_puntajes del God file ==== > %OUT%
echo. >> %OUT%
echo [A] estructura Excel ANTES >> %OUT%
python verify_puntajes_excel.py > pun_before_out.txt 2>&1
type pun_before_out.txt >> %OUT%
echo. >> %OUT%
echo [B] aplicar extraccion >> %OUT%
python extract_puntajes_excel.py >> %OUT% 2>&1
echo   esperando reload (9s)... >> %OUT%
timeout /t 9 /nobreak >nul
echo. >> %OUT%
echo [C] estructura Excel DESPUES >> %OUT%
python verify_puntajes_excel.py > pun_after_out.txt 2>&1
type pun_after_out.txt >> %OUT%
echo. >> %OUT%
echo [D] comparacion (debe ser identica) >> %OUT%
fc pun_before_out.txt pun_after_out.txt >> %OUT% 2>&1
echo. >> %OUT%
echo [E] pytest tests/golden >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [F] HTTP >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
