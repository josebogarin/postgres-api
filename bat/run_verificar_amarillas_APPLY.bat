@echo off
title BECBUC - Verificar Amarillas Playoffs (APLICAR CAMBIOS)
echo ================================================
echo  VERIFICAR Y ACTUALIZAR AMARILLAS EN BD
echo ================================================
echo.
echo ATENCION: Este script MODIFICA la BD con los valores de API-Football.
echo Despues de aplicar, recalcular puntajes desde el Portal.
echo.
set /p confirm="Confirmar actualizacion? (s/n): "
if /i "%confirm%" neq "s" (
    echo Cancelado.
    pause
    exit /b
)
echo.
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul || (
    echo Instalando dependencias...
    pip install psycopg2-binary requests -q
)
python verificar_amarillas_playoffs.py --apply
echo.
pause
