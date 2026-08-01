@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\restaurar_octavos_sudamericana.py" %*
echo.
pause
