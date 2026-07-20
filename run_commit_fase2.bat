@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=git_fase2_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 2 - repo pilot: ranking SQL -> repositories/ranking_repo.py (apostador_bets.py -155 lineas) + portabilidad (safe_write rutas relativas, tools/db_env.py lee creds de .env)" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -5 >> %OUT% 2>&1
echo === archivos nuevos de la capa repo/tools === >> %OUT%
git ls-files backend/app/repositories tools >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
