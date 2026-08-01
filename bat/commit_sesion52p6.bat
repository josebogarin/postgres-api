@echo off
cd /d "%~dp0..\backend"
del ".git\index.lock" 2>nul
git add "static/becbuc-live-playoffs.html" "..\CLAUDE.md"
git commit -m "sesion 52 parte 6: login real + timezone fix + live items panel + tab apuestas privacidad"
git push
echo.
echo Commit completado. Presiona cualquier tecla para cerrar.
pause
