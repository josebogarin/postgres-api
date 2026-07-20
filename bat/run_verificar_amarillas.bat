@echo off
title BECBUC - Verificar Amarillas Playoffs (Dry-Run)
echo ================================================
echo  VERIFICAR AMARILLAS PLAYOFFS - SOLO REPORTE
echo ================================================
echo.
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul || (
    echo Instalando psycopg2 y requests...
    pip install psycopg2-binary requests -q
)
python verificar_amarillas_playoffs.py
echo.
pause
