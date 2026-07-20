@echo off
echo Aplicando fix: pts_equipo=0 para partidos de grupo (elimina doble conteo item P)...
Get-Content "C:\proyecto FAST API\documentacion\fix_pts_equipo_grupos.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
echo.
echo Listo. Ahora recalcular puntajes desde el portal (Herramientas > Calcular puntajes)
echo o ejecutar: POST /api/v1/bets/calcular-puntajes/2
pause
