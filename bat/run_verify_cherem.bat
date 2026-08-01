@echo off
echo Ejecutando verificacion completa cherem...
Get-Content "%~dp0..\verify_cherem.sql" | docker exec -i core-postgres psql -U app_user -d becbuc > "%~dp0..\verify_cherem_out.txt" 2>&1
type "%~dp0..\verify_cherem_out.txt"
pause
