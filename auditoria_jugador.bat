@echo off
REM auditoria_jugador.bat
REM Genera el Excel de auditoría de un apostador usando el venv del backend.
REM Uso:  auditoria_jugador.bat [nombre] [torneo_id] [output.xlsx]
REM
REM Ejemplos:
REM   auditoria_jugador.bat patito
REM   auditoria_jugador.bat "juan carlos" 2
REM   auditoria_jugador.bat patito 2 "C:\Users\Jose Bogarin\Desktop\patito.xlsx"

setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON=%SCRIPT_DIR%backend\.venv\Scripts\python.exe"
set "SCRIPT=%SCRIPT_DIR%auditoria_jugador.py"

if not exist "%PYTHON%" (
    echo ERROR: No se encontro el interprete Python en:
    echo   %PYTHON%
    echo Asegurate de que el venv del backend este instalado.
    pause
    exit /b 1
)

echo Ejecutando auditoria BECBUC...
echo.

"%PYTHON%" "%SCRIPT%" %* > "%SCRIPT_DIR%auditoria_log.txt" 2>&1

echo.
if %ERRORLEVEL% == 0 (
    echo Listo. Revisa el archivo auditoria_*.xlsx en la carpeta del proyecto.
) else (
    echo ERROR: el script termino con codigo %ERRORLEVEL%.
)

type "%SCRIPT_DIR%auditoria_log.txt"
pause
