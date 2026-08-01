@echo off
echo ========================================
echo  BECBUC - Swap predicciones 5 pares
echo ========================================
echo.
echo Ejecutando fix_swap_predicciones.sql en Docker...
powershell -Command "Get-Content '%~dp0..\documentacion\fix_swap_predicciones.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo Listo. Ahora recalcula puntajes desde el portal:
echo   POST /api/v1/bets/calcular-puntajes/2?force_grupos=true
echo.
pause
