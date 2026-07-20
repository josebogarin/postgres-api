@echo off
echo ============================================
echo  BACKUP + GIT COMMIT  (sesion 60)
echo ============================================
echo.

REM 1. Backup
echo [1/3] Ejecutando backup...
cd /d "C:\proyecto FAST API"
powershell -ExecutionPolicy Bypass -File "backup_becbuc.ps1"
echo.

REM 2. Limpiar lock de git si existe
if exist "backend\.git\index.lock" (
    echo Limpiando index.lock...
    del /f "backend\.git\index.lock"
)

REM 3. Git commit
echo [2/3] Git add + commit...
cd /d "C:\proyecto FAST API\backend"
git add -A
git status --short
echo.
git commit -m "sesion 60: org rules applied, tercer_puesto O fix, equipo iso+ranking poblado, comparar_tbl_check.py"
echo.

echo [3/3] Git push...
git push
echo.
echo ============================================
echo Listo.
pause
