@echo off
echo ============================================
echo   BECBUC - Iniciando servidor + pagina live
echo ============================================
echo.

cd /d "%~dp0..\backend"

echo [1/3] Cerrando servidor anterior (si existe)...
taskkill /F /FI "WINDOWTITLE eq uvicorn-becbuc" /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Iniciando uvicorn...
start "uvicorn-becbec" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo [3/3] Esperando 8 segundos y abriendo pagina...
timeout /t 8 /nobreak >nul

REM Abre usando el protocolo http:// -- Windows usa el navegador predeterminado
REM (evita el selector de perfil de Chrome)
start "" "http://localhost:8000/static/becbuc-live.html"

echo.
echo ============================================
echo  Servidor corriendo. La pagina se abrio.
echo  Si ves error, esperá 5 segundos y F5.
echo ============================================
pause
