@echo off
powershell -ExecutionPolicy Bypass -Command "Get-Content 'C:\proyecto FAST API\check_minuto99.sql' | docker exec -i core-postgres psql -U app_user -d becbuc | Out-File 'C:\proyecto FAST API\check99_out.txt' -Encoding UTF8"
