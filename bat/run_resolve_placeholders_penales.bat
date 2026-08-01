@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\resolve_placeholders_penales.py" %*
echo.
pause
