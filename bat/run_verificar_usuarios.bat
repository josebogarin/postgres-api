@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Verificar usuarios Sandra / Hugo Biedermann (Pato) ===
python verificar_usuario_sandra.py
echo.
pause
