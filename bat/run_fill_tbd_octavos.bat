@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\fill_tbd_octavos.py" %*
echo.
pause
