@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === APLICAR: re-subir octavos de SANBIE y PATO a la BD ===
python resubir_octavos_sanbie_pato.py --import
echo.
pause
