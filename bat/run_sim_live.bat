@echo off
echo ============================================================
echo SIMULACION - Germany vs Paraguay en vivo (minuto 67)
echo ============================================================
powershell -Command "Get-Content '%~dp0..\documentacion\sim_partido_live.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo Simulacion lista. Abrir becbuc-live.html para ver el resultado.
echo Para revertir: run_sim_live_revert.bat
pause
