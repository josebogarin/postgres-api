@echo off
title BECBUC - Ejecutar Todo
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
python ejecutar_todo.py
