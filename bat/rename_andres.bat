@echo off
echo === Renombrando usuario andres (id=9) a andresboga ===
docker exec core-postgres psql -U app_user -d app_db -c "UPDATE users SET username='andresboga' WHERE id=9 AND username='andres';" > "%~dp0..\rename_result.txt" 2>&1
echo.
echo === Verificacion ===
docker exec core-postgres psql -U app_user -d app_db -c "SELECT id, username, nombre FROM users WHERE id=9;" >> "%~dp0..\rename_result.txt" 2>&1
type "%~dp0..\rename_result.txt"
pause
