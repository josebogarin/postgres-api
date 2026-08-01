@echo off
cd /d "%~dp0.."
echo === DIAG tanda P101/P102 (y P103/P104): Excel de cierre vs BD (solo lectura) ===
call backend\.venv\Scripts\python.exe diag_tanda_semis.py
echo.
pause
