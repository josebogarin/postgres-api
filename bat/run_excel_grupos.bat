@echo off
echo Generando Excel de puntaje por item - Fase de Grupos...
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
python excel_grupos_por_item.py
pause
