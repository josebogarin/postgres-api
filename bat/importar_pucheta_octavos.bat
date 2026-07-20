@echo off
echo ============================================
echo  Importar apuestas PUCHETA - Octavos R16
echo ============================================
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat
python importar_pucheta_octavos.py
echo.
pause
