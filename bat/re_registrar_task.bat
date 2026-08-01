@echo off
REM Auto-elevate a Administrador
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Solicitando permisos de Administrador...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo === Re-registrando BECBUC-SyncAPI (Task Scheduler) ===
echo.

REM Eliminar tarea anterior si existe
schtasks /delete /tn "BECBUC-SyncAPI" /f 2>nul
echo Tarea anterior eliminada (si existia).
echo.

REM Registrar nueva tarea usando el bat wrapper (que hace cd al directorio correcto)
schtasks /create /tn "BECBUC-SyncAPI" ^
  /tr "\"%~dp0..\run_sync_auto.bat\"" ^
  /sc MINUTE /mo 1 ^
  /rl HIGHEST ^
  /ru SYSTEM ^
  /f

echo.
if %ERRORLEVEL% EQU 0 (
    echo EXITO: Tarea BECBUC-SyncAPI registrada.
    echo - Corre cada 1 minuto como SYSTEM
    echo - No necesita usuario logueado
    echo - Log: %~dp0..\sync_auto.log
    echo.
    schtasks /query /tn "BECBUC-SyncAPI" /fo LIST
    echo.
    echo Iniciando primera ejecucion de prueba...
    schtasks /run /tn "BECBUC-SyncAPI"
    timeout /t 5 /nobreak >nul
    echo.
    echo Ultimas lineas del log:
    powershell -Command "Get-Content '%~dp0..\sync_auto.log' -Tail 5"
) else (
    echo ERROR al registrar la tarea.
)

echo.
pause
