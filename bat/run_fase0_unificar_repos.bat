@echo off
setlocal enabledelayedexpansion
cd /d "C:\proyecto FAST API"

echo ============================================================
echo  FASE 0 - Unificar repos anidados + commit de TODO (BECBUC)
echo ============================================================
echo.
echo Este script hace, en orden:
echo   1) Respalda backend\.git, frontend\.git y frontend-becbuc\.git en un ZIP
echo   2) Exporta el git log de cada repo anidado a documentacion\git_history\
echo   3) Quita los gitlinks del indice raiz (git rm --cached)
echo   4) BORRA los .git anidados (ya respaldados en el ZIP)
echo   5) git add -A  +  commit de todo desde la raiz (respeta .gitignore)
echo   6) Corre backup_becbuc.ps1
echo.
echo   NO hace push (no hay remoto configurado). El commit es LOCAL.
echo   Revisa el git status antes de confirmar el commit (2do prompt).
echo.
set /p OK="Escribi SI y Enter para continuar (cualquier otra cosa cancela): "
if /I not "%OK%"=="SI" goto :cancel

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i

echo.
echo [0/6] Verificando repo raiz...
git rev-parse --is-inside-work-tree >nul 2>&1 || (echo ERROR: no hay repo git en la raiz. & goto :end)

echo.
echo [1/6] Respaldando .git anidados en _backups\git_anidados_%TS%.zip ...
if not exist "_backups" mkdir "_backups"
powershell -NoProfile -Command "$i=@(); foreach($d in 'backend\.git','frontend\.git','frontend-becbuc\.git'){ if(Test-Path $d){ $i+=$d } }; if($i.Count){ Compress-Archive -Path $i -DestinationPath '_backups\git_anidados_%TS%.zip' -Force; Write-Host ('  ZIP creado con: ' + ($i -join ', ')) } else { Write-Host '  No hay .git anidados que respaldar' }"

echo.
echo [2/6] Exportando historial de repos anidados a documentacion\git_history\ ...
if not exist "documentacion\git_history" mkdir "documentacion\git_history"
if exist "backend\.git"          git -C backend          log --stat > "documentacion\git_history\backend_log_%TS%.txt" 2>nul
if exist "frontend\.git"         git -C frontend         log --stat > "documentacion\git_history\frontend_log_%TS%.txt" 2>nul
if exist "frontend-becbuc\.git"  git -C frontend-becbuc  log --stat > "documentacion\git_history\frontend-becbuc_log_%TS%.txt" 2>nul

echo.
echo [3/6] Quitando gitlinks del indice raiz (si existen)...
git rm -r --cached backend         >nul 2>&1
git rm -r --cached frontend        >nul 2>&1
git rm -r --cached frontend-becbuc >nul 2>&1

echo.
echo [4/6] Borrando .git anidados (ya respaldados)...
if exist "backend\.git"          rmdir /s /q "backend\.git"
if exist "frontend\.git"         rmdir /s /q "frontend\.git"
if exist "frontend-becbuc\.git"  rmdir /s /q "frontend-becbuc\.git"

echo.
echo [5/6] git add -A (respetando .gitignore)...
git add -A
echo.
echo ---- Resumen (conteo de archivos staged) ----
git diff --cached --name-only | find /c /v ""
echo ---- git status (resumen) ----
git status --short
echo.
set /p OK2="Escribi COMMIT y Enter para confirmar el commit (otra cosa cancela): "
if /I not "%OK2%"=="COMMIT" goto :cancel

git commit -m "chore(fase0): unificar repos anidados + snapshot completo (backend refactor + Live nuevo + buscador de copas + reglas multi-torneo)"
echo.
echo Commit realizado. Ultimo commit:
git log --oneline -1

echo.
echo [6/6] Backup del proyecto (backup_becbuc.ps1)...
if exist "backup_becbuc.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "backup_becbuc.ps1"
) else (
  echo   backup_becbuc.ps1 no encontrado en la raiz, salteando.
)

echo.
echo ============================================================
echo  LISTO. Repo unificado + commit + backup.
echo  Historiales anidados: documentacion\git_history\ y _backups\git_anidados_%TS%.zip
echo  Para publicar: configurar remoto y 'git push' manualmente.
echo ============================================================
goto :end

:cancel
echo.
echo CANCELADO por el usuario.
echo Si ya se paso el paso [4], los .git anidados estan en el ZIP de _backups.
echo Para revertir el staging: git reset

:end
echo.
pause
