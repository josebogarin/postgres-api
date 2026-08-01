@echo off
cd /d "%~dp0.."
echo === APPLY: deja la BD IDENTICA al Excel (marcador+bonus+globales) ===
call backend\.venv\Scripts\python.exe verificar_apuestas_fin_torneo.py --apply
echo.
pause
