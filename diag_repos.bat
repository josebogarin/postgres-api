@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=diag_repos_out.txt
echo ==== DIAG NESTED REPOS + FOOTPRINT ==== > %OUT%
echo. >> %OUT%
echo === backend === >> %OUT%
if exist backend\.git (echo backend\.git EXISTE >> %OUT%) else (echo backend\.git NO existe >> %OUT%)
echo commits: >> %OUT%
git -C backend rev-list --all --count >> %OUT% 2>&1
echo log: >> %OUT%
git -C backend log --oneline -3 >> %OUT% 2>&1
echo remotes: >> %OUT%
git -C backend remote -v >> %OUT% 2>&1
echo cambios sin commitear (conteo): >> %OUT%
git -C backend status --porcelain | find /c /v "" >> %OUT% 2>&1
echo. >> %OUT%
echo === frontend === >> %OUT%
if exist frontend\.git (echo frontend\.git EXISTE >> %OUT%) else (echo frontend\.git NO existe >> %OUT%)
echo commits: >> %OUT%
git -C frontend rev-list --all --count >> %OUT% 2>&1
echo log: >> %OUT%
git -C frontend log --oneline -3 >> %OUT% 2>&1
echo remotes: >> %OUT%
git -C frontend remote -v >> %OUT% 2>&1
echo. >> %OUT%
echo === repo raiz (padre) === >> %OUT%
git -C "%~dp0." rev-list --all --count >> %OUT% 2>&1
echo. >> %OUT%
echo === footprint excluible === >> %OUT%
echo backend\.venv: >> %OUT%
dir /s "backend\.venv" 2>nul | find "File(s)" >> %OUT%
echo frontend\node_modules: >> %OUT%
dir /s "frontend\node_modules" 2>nul | find "File(s)" >> %OUT%
echo logs *.log (raiz): >> %OUT%
dir /s *.log 2>nul | find "File(s)" >> %OUT%
echo ---- FIN ---- >> %OUT%
notepad %OUT%
