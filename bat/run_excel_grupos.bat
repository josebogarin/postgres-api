@echo off
echo Generando Excel de puntaje por item - Fase de Grupos...
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python excel_grupos_por_item.py
pause
