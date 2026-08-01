@echo off
echo ============================================================
echo RESET KO - Elimina resultados simulados de fases KO
echo Conserva: equipos R32, apuestas de apostadores, puntajes grupos
echo ============================================================
echo.
echo ATENCION: Esto borra todos los resultados de partidos KO.
echo Presiona Ctrl+C para cancelar o cualquier tecla para continuar...
pause > nul

powershell -Command "Get-Content '%~dp0..\documentacion\reset_ko_resultados.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"

echo.
echo Listo. Correr calcular-puntajes desde el portal para verificar.
pause
