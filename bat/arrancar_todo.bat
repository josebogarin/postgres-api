@echo off
REM ============================================================================
REM  arrancar_todo.bat - Arranque completo BECBUC
REM   0) (opcional) compila el frontend nuevo y lo copia a backend\static\v2
REM   1) arranca uvicorn (:8000) en su ventana
REM   2) arranca ngrok (http 8000) en su ventana
REM   3) abre el Live nuevo y el inspector de ngrok
REM  Correr desde la PC (Windows).
REM  NOTA: con el Live servido en /static/v2, "npm run dev" (:3000) ya no hace
REM        falta. npm aca se usa SOLO para compilar.
REM ============================================================================
title BECBUC - Arranque completo
setlocal EnableExtensions
pushd "%~dp0.."
set "ROOT=%CD%"

echo.
choice /C SN /T 8 /D S /M "Compilar el frontend (Live nuevo) antes de arrancar"
if errorlevel 2 goto :skipbuild

echo.
echo === Paso 0: compilar frontend-becbuc (build:export) ===
cd /d "%ROOT%\frontend-becbuc"
call npm run build:export
if errorlevel 1 (
  echo.
  echo *** ERROR en el build. Se aborta el arranque. ***
  popd
  pause
  exit /b 1
)
if not exist "%ROOT%\frontend-becbuc\out\index.html" (
  echo *** ERROR: no se genero out\index.html. Se aborta. ***
  popd
  pause
  exit /b 1
)
echo === Copiando out -^> backend\static\v2 ===
robocopy "%ROOT%\frontend-becbuc\out" "%ROOT%\backend\static\v2" /MIR /NFL /NDL /NJH /NJS /NC /NS >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo *** ERROR copiando a static\v2 - robocopy code %RC% ***
  popd
  pause
  exit /b 1
)
echo Frontend compilado y desplegado en backend\static\v2
:skipbuild

echo.
echo === Deteniendo instancias previas (uvicorn / ngrok) ===
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /IM ngrok.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo === Paso 1: arrancando uvicorn en :8000 ===
cd /d "%ROOT%\backend"
start "BECBUC-Uvicorn" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Esperando a que uvicorn levante ...
timeout /t 6 /nobreak >nul

echo.
echo === Paso 2: arrancando ngrok (http 8000) ===
cd /d "%ROOT%"
start "BECBUC-Ngrok" cmd /k "ngrok.exe http 8000"
timeout /t 3 /nobreak >nul

echo.
echo === Abriendo Live nuevo + inspector de ngrok ===
start "" "http://localhost:8000/static/v2/"
start "" "http://127.0.0.1:4040"

echo.
echo ============================================================================
echo  LISTO.
echo   Live nuevo local:   http://localhost:8000/static/v2/
echo   Portal viejo:       http://localhost:8000/BECBUC-portal
echo   URL publica ngrok:  ver en http://127.0.0.1:4040 (pestana Status)
echo  Cerra las ventanas "BECBUC-Uvicorn" y "BECBUC-Ngrok" para apagar todo.
echo ============================================================================
popd
endlocal
