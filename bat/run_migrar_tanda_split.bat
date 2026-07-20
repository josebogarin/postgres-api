@echo off
echo Agregando columnas pts_penales_local_tanda / pts_penales_visitante_tanda...
docker exec core-postgres psql -U app_user -d becbuc -c "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_local_tanda INT DEFAULT 0; ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_visitante_tanda INT DEFAULT 0;"
echo Hecho.
echo Ahora ejecuta POST /calcular-puntajes/2 para repoblar las nuevas columnas.
pause
