@echo off
title BECBUC - Ejecutar Todo
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python ejecutar_todo.py
