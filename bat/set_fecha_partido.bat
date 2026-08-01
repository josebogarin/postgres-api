@echo off
REM Uso:  set_fecha_partido.bat <partido_id> <YYYY-MM-DD> <HH:MM>   (hora Paraguay)
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python set_fecha_partido.py %1 %2 %3
echo.
pause
