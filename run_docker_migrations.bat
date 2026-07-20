@echo off
echo === Inicio migraciones Docker === > "C:\proyecto FAST API\migration_log.txt"
echo %DATE% %TIME% >> "C:\proyecto FAST API\migration_log.txt"

echo === migracion_monitor.sql === >> "C:\proyecto FAST API\migration_log.txt"
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\migracion_monitor.sql' | docker exec -i core-postgres psql -U app_user -d becbuc" >> "C:\proyecto FAST API\migration_log.txt" 2>&1
echo Exit code monitor: %ERRORLEVEL% >> "C:\proyecto FAST API\migration_log.txt"

echo === fix_partido_id_apuestas_v2.sql === >> "C:\proyecto FAST API\migration_log.txt"
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\fix_partido_id_apuestas_v2.sql' | docker exec -i core-postgres psql -U app_user -d becbuc" >> "C:\proyecto FAST API\migration_log.txt" 2>&1
echo Exit code fix: %ERRORLEVEL% >> "C:\proyecto FAST API\migration_log.txt"

echo === FIN === >> "C:\proyecto FAST API\migration_log.txt"
