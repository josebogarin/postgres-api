@echo off
REM Script para iniciar Backend + Frontend
REM Haz doble click o ejecuta: iniciar-todo.bat

cls
color 0A
echo.
echo ================================================================================
echo                  INICIANDO PLATAFORMA FASTAPI + FLASK
echo ================================================================================
echo.

REM Definir rutas
set BACKEND_PATH=%~dp0..\backend
set WEB_PATH=%~dp0..\web
set BACKEND_PORT=8000
set WEB_PORT=5000

echo [1/2] Iniciando Backend en puerto %BACKEND_PORT%...
start "Backend FastAPI" cmd /k "cd /d "%BACKEND_PATH%" && .venv\Scripts\uvicorn.exe app.main:app --reload --port %BACKEND_PORT%"

timeout /t 3 /nobreak

echo [2/2] Iniciando Frontend en puerto %WEB_PORT%...
start "Frontend Flask" cmd /k "cd /d "%WEB_PATH%" && python app.py"

timeout /t 2 /nobreak

echo.
echo ================================================================================
echo                        ✅ PLATAFORMA INICIADA
echo ================================================================================
echo.
echo  Frontend Web:    http://localhost:%WEB_PORT%
echo  API Swagger:     http://localhost:%BACKEND_PORT%/docs
echo.
echo  User: admin@example.com
echo  Pass: changeme123
echo.
echo Abriendo navegadores...
echo.

REM Abrir navegadores
start http://localhost:%WEB_PORT%
timeout /t 1 /nobreak
start http://localhost:%BACKEND_PORT%/docs

echo Presiona cualquier tecla para cerrar esta ventana (las aplicaciones seguiran corriendo)
pause
