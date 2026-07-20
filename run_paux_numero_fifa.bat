@echo off
echo Agregando campo numero_partido_fifa a pronosticos_aux...
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\migracion_paux_numero_fifa.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
pause
