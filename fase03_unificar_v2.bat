@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=fase03_unificar_out.txt
echo ==== FASE 0.3 UNIFICAR (opcion A) v2 ==== > %OUT%
echo. >> %OUT%

echo [1] borrar .git internos (historial en bundles) >> %OUT%
if exist "backend\.git" rmdir /s /q "backend\.git"
if exist "frontend\.git" rmdir /s /q "frontend\.git"
if exist "backend\.git" echo ERROR: backend\.git sigue existiendo >> %OUT%
if exist "backend\.git" goto :end
if exist "frontend\.git" echo ERROR: frontend\.git sigue existiendo >> %OUT%
if exist "frontend\.git" goto :end
echo   backend\.git y frontend\.git borrados. >> %OUT%
echo. >> %OUT%

echo [2] quitar gitlinks del indice + git add -A >> %OUT%
git rm -r --cached --quiet backend frontend >> %OUT% 2>&1
git add -A >> %OUT% 2>&1
git diff --cached --name-only > staged.tmp 2>>%OUT%
for /f %%C in ('find /c /v "" ^< staged.tmp') do set STAGED=%%C
echo   archivos en staging: %STAGED% >> %OUT%
echo. >> %OUT%

echo [3] chequeo anti-leak (.venv / node_modules) >> %OUT%
findstr /i /c:".venv/" /c:"node_modules/" staged.tmp >nul
if %errorlevel%==0 goto :abort
echo   sin leak. OK. >> %OUT%
echo. >> %OUT%

echo [4] commit unificado >> %OUT%
git commit -m "Fase 0.3 - unificar repos opcion A: backend+frontend en repo raiz + fix item F y reorg B1 (antes sin commitear)" >> %OUT% 2>&1
echo --- log: >> %OUT%
git log --oneline -4 >> %OUT% 2>&1
echo --- .venv/node_modules trackeados (debe ser 0): >> %OUT%
git ls-files > allfiles.tmp 2>&1
findstr /i /c:".venv/" /c:"node_modules/" allfiles.tmp | find /c /v "" >> %OUT%
del allfiles.tmp 2>nul
goto :verify

:abort
echo *** LEAK: .venv/node_modules en staging. NO se commitea. >> %OUT%
git reset >> %OUT% 2>&1
echo *** ABORTADO. Revisar antes de continuar. >> %OUT%
goto :end

:verify
echo. >> %OUT%
echo [5] pytest tests/golden (deben ser 17 passed) >> %OUT%
cd /d "%~dp0backend"
call .venv\Scripts\activate
cd /d "%~dp0."
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [6] HTTP (uvicorn :8000) >> %OUT%
curl -s -o nul -w "  /BECBUC-portal = %%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
curl -s -o nul -w "  /live = %%{http_code}\n" http://localhost:8000/live >> %OUT% 2>&1
curl -s -o nul -w "  /static/becbuc-live-playoffs.html = %%{http_code}\n" "http://localhost:8000/static/becbuc-live-playoffs.html" >> %OUT% 2>&1

:end
del staged.tmp 2>nul
echo ---- FIN ---- >> %OUT%
notepad %OUT%
