@echo off
cd /d "%~dp0.."
echo ============================================================
echo TEST: Item P - Bonus por equipos clasificados a R32
echo ============================================================
echo.
backend\.venv\Scripts\python test_grupos_p.py
echo.
pause
