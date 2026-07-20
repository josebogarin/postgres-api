@echo off
cd /d "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe test_propagacion_bracket.py > test_bracket_output.txt 2>&1
echo.>> test_bracket_output.txt
echo === FIN DEL TEST === >> test_bracket_output.txt
