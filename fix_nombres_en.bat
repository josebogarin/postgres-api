@echo off
chcp 65001 >nul
echo ====================================================
echo  Fix Nombres Equipos (Espanol -> Ingles)
echo ====================================================
echo.
type "C:\proyecto FAST API\documentacion\fix_nombres_equipos_en.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
echo.
echo ====================================================
echo  Listo. Podes cerrar esta ventana.
echo ====================================================
pause
