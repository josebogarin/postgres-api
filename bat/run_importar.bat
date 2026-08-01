@echo off
echo Ejecutando importacion de pronosticos_aux...
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\importar_pronosticos_aux.py"
