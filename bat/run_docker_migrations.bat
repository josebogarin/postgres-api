@echo off
echo === Inicio migraciones Docker === > "%~dp0..\migration_log.txt"
echo %DATE% %TIME% >> "%~dp0..\migration_log.txt"

echo === migracion_monitor.sql === >> "%~dp0..\migration_log.txt"
powershell -Command "Get-Content '%~dp0..\documentacion\migracion_monitor.sql' | docker exec -i core-postgres psql -U app_user -d becbuc" >> "%~dp0..\migration_log.txt" 2>&1
echo Exit code monitor: %ERRORLEVEL% >> "%~dp0..\migration_log.txt"

echo === fix_partido_id_apuestas_v2.sql === >> "%~dp0..\migration_log.txt"
powershell -Command "Get-Content '%~dp0..\documentacion\fix_partido_id_apuestas_v2.sql' | docker exec -i core-postgres psql -U app_user -d becbuc" >> "%~dp0..\migration_log.txt" 2>&1
echo Exit code fix: %ERRORLEVEL% >> "%~dp0..\migration_log.txt"

echo === FIN === >> "%~dp0..\migration_log.txt"
