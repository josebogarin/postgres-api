@echo off
REM Auditoria de puntajes BECBUC 2026
REM Ejecuta comparar_puntajes_control.py con el venv del backend

cd /d "C:\proyecto FAST API"

echo.
echo ====================================================
echo  AUDITORIA DE PUNTAJES BECBUC 2026
echo ====================================================
echo.

REM Si se paso el Excel como argumento, usarlo
IF NOT "%~1"=="" (
    echo Usando Excel: %~1
    backend\.venv\Scripts\python.exe comparar_puntajes_control.py "%~1"
) ELSE (
    echo Buscando Excel de control automaticamente...
    backend\.venv\Scripts\python.exe comparar_puntajes_control.py
)

echo.
IF EXIST "reporte_diferencias_puntajes.xlsx" (
    echo Reporte generado: reporte_diferencias_puntajes.xlsx
    start "" "reporte_diferencias_puntajes.xlsx"
) ELSE (
    echo ERROR: No se genero el reporte. Ver mensajes arriba.
)

pause
