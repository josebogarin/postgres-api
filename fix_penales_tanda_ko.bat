@echo off
echo === Corregir penales_partido en partidos KO con tanda ===
echo.
echo Resetea penales_partido a 0 y datos_confirmados a FALSE
echo para todos los partidos con tanda donde el valor parece de la tanda.
echo Luego Sync desde API-Football recalculara correctamente.
echo.
docker exec core-postgres psql -U app_user -d becbuc -c ^
"SELECT numero_fifa, penales_local, penales_visitante, penales_partido FROM partido WHERE penales_local IS NOT NULL ORDER BY numero_fifa;"
echo.
echo Aplicando fix (reset penales_partido donde penales_partido = penales_local + penales_visitante)...
docker exec core-postgres psql -U app_user -d becbuc -c ^
"UPDATE partido SET penales_partido = 0, datos_confirmados = FALSE WHERE penales_local IS NOT NULL AND penales_partido = (COALESCE(penales_local,0) + COALESCE(penales_visitante,0)); SELECT 'Filas actualizadas: ' || COUNT(*) FROM partido WHERE penales_local IS NOT NULL AND penales_partido = 0;"
echo.
echo Ahora ir a Herramientas y hacer Sync desde API-Football para recalcular.
pause
