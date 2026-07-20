Get-Content "C:\proyecto FAST API\documentacion\fix_tarjetas_r32.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
