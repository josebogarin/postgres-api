@echo off
cd /d "%~dp0.."
echo === DIAG VAR real por partido: Excel RESULTADOS OFICIALES vs BD (solo lectura) ===
call backend\.venv\Scripts\python.exe diag_var_real.py
echo.
pause
