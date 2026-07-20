@echo off
powershell -ExecutionPolicy Bypass -Command "Get-Content 'C:\proyecto FAST API\diag_n_diffs.sql' | docker exec -i core-postgres psql -U app_user -d becbuc | Out-File 'C:\proyecto FAST API\diag_n_out.txt' -Encoding UTF8"
