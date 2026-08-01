@echo off
REM Registra el barrido de resultados CADA 15 MIN (reemplaza el sync de cada minuto).
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Solicitando permisos de Administrador...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo === Reemplazando tarea de sync ===
REM Sacamos la tarea vieja de cada minuto si existe
schtasks /delete /tn "BECBUC-SyncAPI" /f 2>nul
REM (re)creamos la nueva cada 15 minutos
schtasks /delete /tn "BECBUC-SyncPendientes" /f 2>nul

schtasks /create /tn "BECBUC-SyncPendientes" ^
  /tr "\"%~dp0..\run_sync_pendientes.bat\"" ^
  /sc MINUTE /mo 15 ^
  /rl HIGHEST ^
  /ru SYSTEM ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo EXITO: BECBUC-SyncPendientes registrada - corre cada 15 min como SYSTEM.
    echo Log: %~dp0..\sync_auto.log
    schtasks /run /tn "BECBUC-SyncPendientes"
    timeout /t 5 /nobreak >nul
    powershell -Command "Get-Content '%~dp0..\sync_auto.log' -Tail 8"
) else (
    echo ERROR al registrar la tarea.
)
echo.
pause
