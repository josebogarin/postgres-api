@echo off
echo ========================================
echo  Actualizar R32 desde Excel TBL CHECK
echo ========================================
cd /d "C:\proyecto FAST API"
set EXCEL=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\local_9db4502a-7e61-4142-bb4b-38eee8035736\uploads\20260702- TBL CHECK PARA JOSE.xlsx
backend\.venv\Scripts\python.exe actualizar_r32_desde_excel.py "%EXCEL%"
echo.
pause
