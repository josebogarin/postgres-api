@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=estado_repos_out.txt
echo === ESTADO REPOS === > %OUT%
if exist "backend\.git" (echo backend\.git EXISTE >> %OUT%) else (echo backend\.git NO_EXISTE >> %OUT%)
if exist "frontend\.git" (echo frontend\.git EXISTE >> %OUT%) else (echo frontend\.git NO_EXISTE >> %OUT%)
echo --- git status parent (conteo de lineas): >> %OUT%
git status --porcelain > st.tmp 2>&1
for /f %%C in ('find /c /v "" ^< st.tmp') do echo   cambios=%%C >> %OUT%
echo --- estado de backend/ y frontend/ segun git (solo esas rutas): >> %OUT%
git status --porcelain -- backend frontend > st2.tmp 2>&1
for /f %%D in ('find /c /v "" ^< st2.tmp') do echo   cambios_en_backend_frontend=%%D >> %OUT%
del st2.tmp 2>nul
echo --- log parent: >> %OUT%
git log --oneline -3 >> %OUT% 2>&1
del st.tmp 2>nul
echo ---- FIN ---- >> %OUT%
notepad %OUT%
