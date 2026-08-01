@echo off
echo ============================================================
echo  BECBUC - Verificar resultados y fix minuto_primer_gol
echo  Fuente: 40-RESULTADOS OFICIALES del Excel de control
echo ============================================================
echo.

echo Ejecutando comparacion y actualizacion...
powershell -Command "Get-Content '%~dp0..\documentacion\verificar_y_fix_minuto_gol.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"

echo.
echo Minutos aun NULL en finalizados (deberia ser 0):
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) as pendientes FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=2 AND p.estado='finalizado' AND p.minuto_primer_gol IS NULL;"

echo.
pause
