@echo off
REM ============================================================================
REM  rebuild_reiniciar.bat - Cierra uvicorn (si esta abierto), recompila y
REM  despliega la v2 (cutover_v2), y reinicia uvicorn en :8000.
REM  Si el build falla, NO reinicia uvicorn.
REM  ngrok NO se toca: al volver uvicorn a :8000, el tunel reconecta solo.
REM ============================================================================
title BECBUC - Rebuild + Reiniciar
setlocal EnableExtensions
set "ROOT=%~dp0.."

echo === Cerrando uvicorn (si esta abierto) ===
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /FI "WINDOWTITLE eq BECBUC-Uvicorn*" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo === Recompilando y desplegando la v2 ===
call "%~dp0cutover_v2.bat"
if errorlevel 1 (
  echo.
  echo *** El build fallo. NO se reinicia uvicorn. Revisa el error de arriba. ***
  pause
  exit /b 1
)

echo.
echo === Reiniciando uvicorn en :8000 ===
cd /d "%ROOT%\backend"
start "BECBUC-Uvicorn" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo.
echo ============================================================================
echo  LISTO: v2 recompilada + uvicorn reiniciado.
echo  Probar: http://localhost:8000/static/v2/
echo  Publico: https://cupped-oink-thousand.ngrok-free.dev/becbuc-live
echo  (espera unos segundos a que uvicorn levante; hace Ctrl+F5)
echo ============================================================================
timeout /t 4 >nul
endlocal
