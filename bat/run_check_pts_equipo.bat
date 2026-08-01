@echo off
SET PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
%PYTHON% "%~dp0..\check_pts_equipo.py"
pause
