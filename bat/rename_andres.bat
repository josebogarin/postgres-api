@echo off
echo === Renombrando usuario andres (id=9) a andresboga ===
docker exec core-postgres psql -U app_user -d app_db -c "UPDATE users SET username='andresboga' WHERE id=9 AND username='andres';" > "C:\proyecto FAST API\rename_result.txt" 2>&1
echo.
echo === Verificacion ===
docker exec core-postgres psql -U app_user -d app_db -c "SELECT id, username, nombre FROM users WHERE id=9;" >> "C:\proyecto FAST API\rename_result.txt" 2>&1
type "C:\proyecto FAST API\rename_result.txt"
pause
