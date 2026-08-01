@echo off
echo ========================================
echo  Arrancando BECBUC Despacho Remoto
echo ========================================

echo [1/2] Arrancando uvicorn...
start "BECBUC - uvicorn" cmd /k "cd /d "%~dp0..\backend" && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

echo Esperando 5 segundos para que levante el servidor...
timeout /t 5 /nobreak >nul

echo [2/2] Arrancando ngrok...
start "BECBUC - ngrok" cmd /k "cd /d "%~dp0.." && ngrok.exe http 8000"

echo.
echo ✅ Listo. Revisa la ventana de ngrok para obtener la URL publica.
echo    Monitor ngrok: http://127.0.0.1:4040
echo.
pause
