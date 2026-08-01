@echo off
echo ============================================
echo  RECALCULO PUNTAJES (algoritmo corregido)
echo ============================================
set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set LOG=%DIR%\fix_p030_log.txt
set OUTPUTS=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\agent\local_ditto_dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\outputs

echo.
echo [1/2] Recalculando puntajes con algoritmo corregido...
echo (requiere uvicorn corriendo en puerto 8000)
%PYTHON% "%DIR%\recalcular_puntajes.py" > "%LOG%" 2>&1

echo.
echo [2/2] Copiando log a outputs...
copy /Y "%LOG%" "%OUTPUTS%\fix_p030_log.txt" >nul 2>&1

echo.
echo ============================================
type "%LOG%"
echo.
pause
