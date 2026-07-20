@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=fase03_unificar_out.txt
echo ==== FASE 0.3 UNIFICAR (opcion A) ==== > %OUT%
echo. >> %OUT%

echo [1] borrar .git internos (historial ya preservado en bundles) >> %OUT%
if exist "backend\.git\" ( rmdir /s /q "backend\.git" & echo backend\.git (dir) borrado >> %OUT% ) else ( if exist "backend\.git" ( del /f /q "backend\.git" & echo backend\.git (file) borrado >> %OUT% ) )
if exist "frontend\.git\" ( rmdir /s /q "frontend\.git" & echo frontend\.git (dir) borrado >> %OUT% ) else ( if exist "frontend\.git" ( del /f /q "frontend\.git" & echo frontend\.git (file) borrado >> %OUT% ) )
echo. >> %OUT%

echo [2] git add -A >> %OUT%
git add -A >> %OUT% 2>&1
git diff --cached --name-only > staged.tmp 2>>%OUT%
for /f %%C in ('find /c /v "" ^< staged.tmp') do set STAGED=%%C
echo archivos en staging: %STAGED% >> %OUT%
echo. >> %OUT%

echo [3] chequeo anti-leak (.venv / node_modules) >> %OUT%
findstr /i /c:".venv/" /c:"node_modules/" staged.tmp >nul
if %errorlevel%==0 goto :abort
echo   sin leak de .venv/node_modules en staging. OK. >> %OUT%
echo. >> %OUT%

echo [4] commit unificado >> %OUT%
git commit -m "Fase 0.3 - unificar repos (opcion A): backend+frontend en repo raiz + fix item F/B1 (antes sin commitear en sub-repos)" >> %OUT% 2>&1
echo. >> %OUT%
echo --- log: >> %OUT%
git log --oneline -4 >> %OUT% 2>&1
echo --- .venv/node_modules trackeados? (debe ser 0): >> %OUT%
git ls-files ^| findstr /i /c:".venv/" /c:"node_modules/" ^| find /c /v "" >> %OUT% 2>&1
goto :verify

:abort
echo *** LEAK DETECTADO: .venv o node_modules en staging. NO se commitea. >> %OUT%
git reset >> %OUT% 2>&1
echo *** ABORTADO. Los .git internos ya se borraron pero NO se commiteo. Revisar antes de seguir. >> %OUT%
goto :end

:verify
echo. >> %OUT%
echo [5] verificacion pytest tests/golden (deben ser 17 passed) >> %OUT%
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
python -m pytest tests\golden -q >> %OUT% 2>&1
echo. >> %OUT%
echo [6] verificacion HTTP (uvicorn :8000) >> %OUT%
curl -s -o nul -w "  /BECBUC-portal http_code=%%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
curl -s -o nul -w "  /live         http_code=%%{http_code}\n" http://localhost:8000/live >> %OUT% 2>&1
curl -s -o nul -w "  /static/becbuc-live-playoffs.html http_code=%%{http_code}\n" "http://localhost:8000/static/becbuc-live-playoffs.html" >> %OUT% 2>&1

:end
del staged.tmp 2>nul
echo ---- FIN ---- >> %OUT%
notepad %OUT%
