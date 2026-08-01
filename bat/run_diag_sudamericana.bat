@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\diag_sudamericana.py" > "%~dp0..\diag_sudamericana_out.txt" 2>&1
echo Diagnostico guardado en diag_sudamericana_out.txt
type "%~dp0..\diag_sudamericana_out.txt" | more
