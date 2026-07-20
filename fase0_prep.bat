@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=fase0_prep_out.txt
echo ==== FASE 0 PREP (no destructivo) ==== > %OUT%
echo. >> %OUT%
echo [footprint excluible, MB] >> %OUT%
powershell -NoProfile -Command "$v=(Get-ChildItem 'backend\.venv' -Recurse -File -EA SilentlyContinue|Measure-Object Length -Sum).Sum; $n=(Get-ChildItem 'frontend\node_modules' -Recurse -File -EA SilentlyContinue|Measure-Object Length -Sum).Sum; $l=(Get-ChildItem . -Recurse -Filter *.log -File -EA SilentlyContinue|Measure-Object Length -Sum).Sum; ('.venv        = {0:N1} MB' -f ($v/1MB)); ('node_modules = {0:N1} MB' -f ($n/1MB)); ('logs         = {0:N1} MB' -f ($l/1MB)); ('TOTAL excluible = {0:N1} MB' -f (($v+$n+$l)/1MB))" >> %OUT% 2>&1
echo. >> %OUT%
echo [0.1+0.2] commit gitignore + backup scope >> %OUT%
git add -A >> %OUT% 2>&1
git commit -m "Fase 0.1+0.2: gitignore afinado (generados) + backup_becbuc scope liviano" >> %OUT% 2>&1
echo. >> %OUT%
echo [parent remote] >> %OUT%
git remote -v >> %OUT% 2>&1
echo. >> %OUT%
echo [bundles de historial de sub-repos] >> %OUT%
if not exist "C:\backup_becbuc\repos_history" mkdir "C:\backup_becbuc\repos_history"
git -C backend bundle create "C:\backup_becbuc\repos_history\backend_history.bundle" --all >> %OUT% 2>&1
git -C frontend bundle create "C:\backup_becbuc\repos_history\frontend_history.bundle" --all >> %OUT% 2>&1
echo --- verificacion (dir): >> %OUT%
dir "C:\backup_becbuc\repos_history" >> %OUT% 2>&1
echo --- verify integridad backend: >> %OUT%
git bundle verify "C:\backup_becbuc\repos_history\backend_history.bundle" >> %OUT% 2>&1
echo --- verify integridad frontend: >> %OUT%
git bundle verify "C:\backup_becbuc\repos_history\frontend_history.bundle" >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
