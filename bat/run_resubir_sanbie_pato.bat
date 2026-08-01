@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === DRY RUN: re-subir octavos de SANBIE y PATO (no escribe) ===
python resubir_octavos_sanbie_pato.py
echo.
pause
