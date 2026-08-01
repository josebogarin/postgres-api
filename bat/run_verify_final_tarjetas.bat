@echo off
cd /d "%~dp0.."
echo === VERIFICACION TARJETAS FINAL (P103/P104) - NO cierra el torneo ===
echo === Requiere uvicorn en :8000 ===
call backend\.venv\Scripts\python.exe verify_final_tarjetas.py > verify_final_tarjetas_log.txt 2>&1
echo DONE >> verify_final_tarjetas_log.txt
