@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
set OUT=fase3c_verif_out.txt
echo ==== FASE 3c: extraer ranking-export (662 lineas) del God file ==== > %OUT%
echo. >> %OUT%
echo [A] estructura Excel ANTES >> %OUT%
python verify_ranking_excel.py > rex_before_out.txt 2>&1
type rex_before_out.txt >> %OUT%
echo. >> %OUT%
echo [B] aplicar extraccion >> %OUT%
python extract_ranking_excel.py >> %OUT% 2>&1
echo   esperando reload (9s)... >> %OUT%
timeout /t 9 /nobreak >nul
echo. >> %OUT%
echo [C] estructura Excel DESPUES >> %OUT%
python verify_ranking_excel.py > rex_after_out.txt 2>&1
type rex_after_out.txt >> %OUT%
echo. >> %OUT%
echo [D] comparacion (debe ser identica) >> %OUT%
fc rex_before_out.txt rex_after_out.txt >> %OUT% 2>&1
echo. >> %OUT%
echo [E] pytest tests/golden >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [F] HTTP >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
