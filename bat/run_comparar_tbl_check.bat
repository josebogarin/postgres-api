@echo off
echo ============================================
echo  COMPARACION TBL CHECK vs BD  (sesion 59+)
echo ============================================
echo.

cd /d "%~dp0.."

REM Buscar el Excel subido en AppData\uploads
set UPLOADS=%APPDATA%\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\local_d09d3b3b-3380-4f77-80fa-069772ec423b\uploads

set EXCEL_DST=20260702- TBL CHECK PARA JOSE.xlsx

if exist "%UPLOADS%\%EXCEL_DST%" (
    echo Copiando Excel desde uploads...
    copy "%UPLOADS%\%EXCEL_DST%" "%EXCEL_DST%"
)

if not exist "%EXCEL_DST%" (
    echo ERROR: No se encontro el Excel TBL CHECK.
    echo Copiarlo manualmente a: %~dp0..\
    pause
    exit /b 1
)

echo Corriendo comparacion...
echo.

backend\.venv\Scripts\python.exe comparar_tbl_check.py "%EXCEL_DST%"

echo.
echo Ver archivo becbuc_comparacion_tbl_*.xlsx en %~dp0..\
pause
