@echo off
echo Revirtiendo simulacion de partido en vivo...
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\sim_partido_live_revert.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo Revert OK.
pause
