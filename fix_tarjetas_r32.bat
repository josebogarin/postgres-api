@echo off
echo === FIX TARJETAS R32 ===
echo Recalculando amarillas/rojas desde eventos_api (excluye banco/staff)...
echo.
Get-Content "C:\proyecto FAST API\documentacion\fix_tarjetas_r32.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
echo.
echo Listo. Ahora recalcula puntajes en el portal: Herramientas > Calcular puntajes
pause
