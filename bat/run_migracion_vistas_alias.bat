@echo off
echo Actualizando vistas v_copamundial_puntajes y v_copamundial_puntajes_det (alias/username)...
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\migracion_vistas_alias.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo Verificando vista (primeras 5 filas):
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT apostador, username, total_puntos FROM v_copamundial_puntajes LIMIT 5;"
echo.
pause
