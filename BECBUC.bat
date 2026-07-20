@echo off
setlocal
cls
color 0A

set RAIZ=C:\proyecto FAST API
set BACKEND=%RAIZ%\backend
set NGROK=%RAIZ%\ngrok.exe
set PORT=8000

echo.
echo  ============================================================
echo         B E C B U C  2026  -  Iniciando sistema...
echo  ============================================================
echo.

REM ── 1. Docker / PostgreSQL ───────────────────────────────────────
echo  [1/4] Verificando base de datos...
docker start core-postgres >nul 2>&1
if errorlevel 1 (
    echo  [!] Docker no responde. Iniciando Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo      Esperando 20 segundos para que Docker arranque...
    timeout /t 20 /nobreak >nul
    docker start core-postgres >nul 2>&1
)
echo       OK - PostgreSQL listo.
echo.

REM ── 2. Backend FastAPI (uvicorn) ─────────────────────────────────
echo  [2/4] Iniciando backend FastAPI en puerto %PORT%...
start "BECBUC - Backend" cmd /k "cd /d "%BACKEND%" && .venv\Scripts\activate && uvicorn app.main:app --reload --port %PORT%"
echo       Esperando que el servidor responda...
timeout /t 5 /nobreak >nul

:wait_server
curl -s -o nul http://localhost:%PORT%/ 2>nul
if errorlevel 1 (
    echo       Todavia cargando...
    timeout /t 3 /nobreak >nul
    goto wait_server
)
echo       OK - Servidor listo en http://localhost:%PORT%
echo.

REM ── 3. Ngrok ─────────────────────────────────────────────────────
echo  [3/4] Iniciando ngrok (acceso externo)...
start "BECBUC - Ngrok" cmd /k "cd /d "%RAIZ%" && ngrok.exe http %PORT%"
timeout /t 4 /nobreak >nul
echo       OK - Monitor ngrok: http://127.0.0.1:4040
echo.

REM ── 4. Abrir portal ──────────────────────────────────────────────
echo  [4/4] Abriendo BECBUC en el navegador...
start http://localhost:%PORT%/static/login.html
timeout /t 1 /nobreak >nul

echo.
echo  ============================================================
echo         BECBUC LISTO
echo  ============================================================
echo.
echo   Portal local:   http://localhost:%PORT%/static/login.html
echo   En vivo local:  http://localhost:%PORT%/static/becbuc-live.html
echo   Ngrok monitor:  http://127.0.0.1:4040
echo   API docs:       http://localhost:%PORT%/docs
echo.
echo   Usuario admin:  jose / catalina
echo   Apostadores:    (usuario) / becbuc2026
echo.
echo   Las ventanas del backend y ngrok deben quedar abiertas.
echo   Para detener: cerrar las ventanas "BECBUC - Backend" y "BECBUC - Ngrok"
echo.
pause
