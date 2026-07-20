@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
set OUT=fase1_tests_out.txt
echo === [1] generar golden master === > %OUT%
python tests\golden\export_golden.py >> %OUT% 2>&1
echo. >> %OUT%
echo === [2] pytest tests/golden === >> %OUT%
python -m pytest --version >> %OUT% 2>&1 || python -m pip install pytest --quiet >> %OUT% 2>&1
python -m pytest tests\golden -v >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
