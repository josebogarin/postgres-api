@echo off
powershell -ExecutionPolicy Bypass -Command "Get-Content '%~dp0..\diag_n_simple.sql' | docker exec -i core-postgres psql -U app_user -d becbuc | Out-File '%~dp0..\diag_n2_out.txt' -Encoding UTF8"
