@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0.."
call backend\.venv\Scripts\activate
python -u fix_etapa_paraguay.py > fix_etapa_paraguay_out.txt 2>&1
echo ---- FIN ---- >> fix_etapa_paraguay_out.txt
notepad fix_etapa_paraguay_out.txt
