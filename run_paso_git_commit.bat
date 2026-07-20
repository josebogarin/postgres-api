@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=git_commit_out.txt
echo === Repo y commits previos === > %OUT%
git rev-parse --is-inside-work-tree >> %OUT% 2>&1
echo commits actuales: >> %OUT%
git rev-list --all --count >> %OUT% 2>&1
echo. >> %OUT%
echo === Config identidad (local al repo) === >> %OUT%
git config user.name "Jose Bogarin"
git config user.email "jose.bogarin@becbuc.local"
echo. >> %OUT%
echo === git add -A === >> %OUT%
git add -A >> %OUT% 2>&1
echo === archivos staged (conteo) === >> %OUT%
git diff --cached --numstat | find /c /v "" >> %OUT% 2>&1
echo. >> %OUT%
echo === git commit === >> %OUT%
git commit -m "Snapshot pre-reorganizacion: torneo 2026 cerrado, fix item F (etapa Paraguay) + globales recalculados" >> %OUT% 2>&1
echo. >> %OUT%
echo === git log (ultimos) === >> %OUT%
git log --oneline -3 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
