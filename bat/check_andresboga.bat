@echo off
echo === Apuestas de andresboga (id=9) en becbuc ===
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) FROM apuesta WHERE apostador_id=9;" > "%~dp0..\andresboga_check.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) FROM puntaje_detalle WHERE apostador_id=9;" >> "%~dp0..\andresboga_check.txt" 2>&1

echo. >> "%~dp0..\andresboga_check.txt"
echo === ANDRES en pronosticos_aux (que NO sea CHEREM) === >> "%~dp0..\andresboga_check.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT DISTINCT nombre, alias FROM pronosticos_aux WHERE UPPER(nombre) LIKE '%%ANDRES%%' OR UPPER(alias) LIKE '%%ANDRES%%' ORDER BY nombre;" >> "%~dp0..\andresboga_check.txt" 2>&1

type "%~dp0..\andresboga_check.txt"
pause
