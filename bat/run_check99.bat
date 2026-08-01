@echo off
powershell -ExecutionPolicy Bypass -Command "Get-Content '%~dp0..\check_minuto99.sql' | docker exec -i core-postgres psql -U app_user -d becbuc | Out-File '%~dp0..\check99_out.txt' -Encoding UTF8"
