@echo off
cd /d "C:\proyecto FAST API"
echo Consultando equipos en BD...
backend\.venv\Scripts\python.exe ver_equipos_bd.py
echo.
echo Abriendo resultado en Notepad...
notepad equipos_bd.txt
