@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
set OUT=fase3c_reverif_out.txt
echo ==== FASE 3c RE-VERIF (tras fix StreamingResponse) ==== > %OUT%
echo   esperando reload (8s)... >> %OUT%
timeout /t 8 /nobreak >nul
echo [C2] estructura Excel DESPUES (fix) >> %OUT%
python verify_ranking_excel.py > rex_after2_out.txt 2>&1
type rex_after2_out.txt >> %OUT%
echo. >> %OUT%
echo [D2] comparacion ANTES vs DESPUES-fix (debe ser identica) >> %OUT%
fc rex_before_out.txt rex_after2_out.txt >> %OUT% 2>&1
echo. >> %OUT%
echo [E] pytest tests/golden >> %OUT%
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [F] HTTP >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
curl -s -o nul -w "  /api/v1/bets/ranking-export/2 = %%{http_code}\n" "http://localhost:8000/api/v1/bets/ranking-export/2" >> %OUT% 2>&1
del rex_before_out.txt rex_after_out.txt rex_after2_out.txt 2>nul
echo ---- FIN ---- >> %OUT%
notepad %OUT%
