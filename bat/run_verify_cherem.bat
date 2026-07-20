@echo off
echo Ejecutando verificacion completa cherem...
Get-Content "C:\proyecto FAST API\verify_cherem.sql" | docker exec -i core-postgres psql -U app_user -d becbuc > "C:\proyecto FAST API\verify_cherem_out.txt" 2>&1
type "C:\proyecto FAST API\verify_cherem_out.txt"
pause
