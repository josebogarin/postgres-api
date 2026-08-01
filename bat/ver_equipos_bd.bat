@echo off
cd /d "%~dp0.."
echo Consultando equipos en BD...
backend\.venv\Scripts\python.exe ver_equipos_bd.py
echo.
echo Abriendo resultado en Notepad...
notepad equipos_bd.txt
