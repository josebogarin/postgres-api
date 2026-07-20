@echo off
echo Actualizando P79 Mexico vs Ecuador: aplazado -> programado, 21:00 CR Jul 1 (03:00 UTC Jul 2)
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE partido SET estado='programado', fecha='2026-07-02 03:00:00' WHERE numero_fifa=79 RETURNING numero_fifa, estado, fecha;"
echo.
echo Verificando...
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT numero_fifa, estado, fecha FROM partido WHERE numero_fifa=79;"
pause
