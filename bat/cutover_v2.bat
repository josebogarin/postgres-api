@echo off
REM ============================================================================
REM  cutover_v2.bat - Lleva el frontend-becbuc (Live nuevo) a /static/v2 del 8000
REM  Pasos: 0) backup version antigua  1) build:export  2) copiar out -> static/v2
REM  Correr desde la PC (Windows), NO desde el sandbox.
REM ============================================================================
setlocal EnableExtensions

REM Raiz del proyecto (este .bat vive en bat\, subimos un nivel y normalizamos)
pushd "%~dp0.."
set "ROOT=%CD%"

REM Timestamp robusto via PowerShell (independiente del locale)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set "TS=%%i"

echo.
echo === Paso 0: backup de la version antigua ===
set "BK=%ROOT%\_backups\static_pre_v2_%TS%"
if not exist "%BK%" mkdir "%BK%"
copy /Y "%ROOT%\backend\static\becbuc-live*.html"   "%BK%\" >nul 2>&1
copy /Y "%ROOT%\backend\static\BECBUC-portal.html"  "%BK%\" >nul 2>&1
copy /Y "%ROOT%\backend\static\BECBUC-movil.html"   "%BK%\" >nul 2>&1
REM backup del main.py por las dudas (por el cambio html=True)
copy /Y "%ROOT%\backend\app\main.py"                "%BK%\main.py.bak" >nul 2>&1
echo Backup guardado en: %BK%

echo.
echo === Paso 1: build:export (npm) ===
cd /d "%ROOT%\frontend-becbuc"
call npm run build:export
if errorlevel 1 (
  echo.
  echo *** ERROR en el build. Se aborta el cutover. La version vieja NO se toco. ***
  popd 2>nul
  exit /b 1
)
if not exist "%ROOT%\frontend-becbuc\out\index.html" (
  echo.
  echo *** ERROR: no se genero out\index.html. Se aborta. ***
  exit /b 1
)

echo.
echo === Paso 2: copiar out -^> backend\static\v2 ===
robocopy "%ROOT%\frontend-becbuc\out" "%ROOT%\backend\static\v2" /MIR /NFL /NDL /NJH /NJS /NC /NS >nul
REM robocopy: exit codes 0-7 son exito; 8+ es error
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 goto :copyerr

echo.
echo ============================================================================
echo  LISTO. Reinicia uvicorn y prueba en:  http://localhost:8000/static/v2/
echo  Version antigua respaldada en: %BK%
echo  Nota: la version vieja sigue intacta en backend\static\, esto es aditivo.
echo ============================================================================
popd
endlocal
exit /b 0

:copyerr
echo *** ERROR al copiar out hacia static\v2 - robocopy code %RC% ***
popd
endlocal
exit /b 1
