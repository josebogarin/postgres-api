@echo off
cd /d "%~dp0.."
echo === DIAGNOSTICO ITEM L (VAR): Excel vs BD, con causa por fila (solo lectura) ===
call backend\.venv\Scripts\python.exe diag_var_L.py
echo.
pause
