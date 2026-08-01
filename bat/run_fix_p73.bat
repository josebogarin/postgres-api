@echo off
echo ============================================================
echo FIX P73 - South Africa vs Canada: marcar como EN JUEGO
echo Corrige la hora (17:00 UTC = 11:00 CR = 1pm ET)
echo ============================================================
powershell -Command "Get-Content '%~dp0..\documentacion\fix_p73_en_juego.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo Listo. El live y bracket deberan mostrar el partido en vivo.
echo Presiona Sincronizar en el portal para actualizar goles desde API-Football.
pause
