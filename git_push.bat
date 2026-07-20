@echo off
echo Limpiando git lock...
if exist "C:\proyecto FAST API\backend\.git\index.lock" del /f "C:\proyecto FAST API\backend\.git\index.lock"

echo Haciendo git add y commit...
cd /d "C:\proyecto FAST API\backend"
git add -A
git commit -m "sesion 28+29: login movil + nombre apostador + vistas puntajes + exportar excel + pronosticos_aux"
echo.
echo Haciendo git push...
git push origin main
echo.
echo === Resultado ===
git log --oneline -3
pause
