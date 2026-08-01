@echo off
chcp 65001 >nul
echo ============================================================
echo  FIX VAR P27 (Canada vs Qatar) y P39 (Belgium vs Iran)
echo  + Recalculo de puntajes
echo ============================================================
echo.
cd /D "%~dp0.."
backend\.venv\Scripts\python.exe fix_var_p27_p39.py
pause
