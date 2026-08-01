@echo off
chcp 65001 >nul
echo ====================================================
echo  Fix Standings Grupo G + Recalculo Puntajes
echo ====================================================
echo.
echo s | "%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\fix_standings_grupo_g.py"
echo.
echo ====================================================
echo  Listo. Podes cerrar esta ventana.
echo ====================================================
pause
