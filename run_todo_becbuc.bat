@echo off
title BECBUC - Ejecutar todo
color 0A
echo ============================================
echo  BECBUC - Simulacion completa + Excel
echo ============================================
echo.

cd /d "C:\proyecto FAST API"

REM --- Paso 1: Verificar Docker ---
echo [1/4] Verificando Docker...
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT 1" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker / core-postgres no esta corriendo.
    echo Iniciar Docker Desktop y esperar que arranque.
    pause
    exit /b 1
)
echo       Docker OK.

REM --- Paso 2: Arrancar uvicorn en ventana separada ---
echo [2/4] Iniciando servidor uvicorn en puerto 8000...
start "BECBUC-Server" cmd /k "cd /d \"C:\proyecto FAST API\backend\" && .venv\Scripts\activate && uvicorn app.main:app --port 8000"
echo       Esperando 10 segundos para que el servidor arranque...
timeout /t 10 /nobreak >nul

REM --- Verificar que el servidor responde ---
curl -s --max-time 5 http://localhost:8000/ >nul 2>&1
if %errorlevel% neq 0 (
    echo AVISO: servidor aun no responde, esperando 10 segundos mas...
    timeout /t 10 /nobreak >nul
)

REM --- Paso 3: Simulacion ---
echo [3/4] Corriendo test_integral.py (simulacion)...
echo       Esto puede tardar 1-2 minutos...
echo.
cd /d "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe test_integral.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR en test_integral.py. Ver mensajes arriba.
    pause
    exit /b 1
)

REM --- Paso 4: Generar Excel ---
echo.
echo [4/4] Generando Excel de auditoria...
backend\.venv\Scripts\python.exe generar_excel_becbuc.py
if %errorlevel% neq 0 (
    echo ERROR en generar_excel_becbuc.py. Ver mensajes arriba.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  LISTO. Archivo generado:
echo  C:\proyecto FAST API\BECBUC_verificacion.xlsx
echo ============================================
echo.
echo Abriendo Excel...
start "" "C:\proyecto FAST API\BECBUC_verificacion.xlsx"
pause
