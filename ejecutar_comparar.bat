@echo off
cd /d "C:\proyecto FAST API"
python comparar_puntajes.py > comparar_output.txt 2>&1
echo.
echo Output guardado en comparar_output.txt
type comparar_output.txt
pause
