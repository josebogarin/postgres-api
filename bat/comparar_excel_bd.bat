@echo off
echo ============================================
echo  COMPARACION EXCEL vs BD - TODOS APOSTADORES
echo ============================================

set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set OUTPUTS=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\agent\local_ditto_dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\outputs

echo Ejecutando comparacion...
%PYTHON% "%DIR%\comparar_excel_bd.py"

if exist "%DIR%\comparar_bd_excel.xlsx" (
    echo.
    echo Copiando resultado a outputs...
    copy /Y "%DIR%\comparar_bd_excel.xlsx" "%OUTPUTS%\comparar_bd_excel.xlsx"
    echo Listo!
) else (
    echo ERROR: no se genero el archivo
)

echo.
pause
