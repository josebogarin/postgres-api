@echo off
REM Sync INMEDIATO (force) de todos los torneos activos (o los que pases como argumento)
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\sync_ahora.py" %*
echo.
pause
