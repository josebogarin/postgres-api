@echo off
set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set OUTPUTS=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\agent\local_ditto_dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\outputs
set LOG=%DIR%\check_estado_log.txt

%PYTHON% "%DIR%\check_estado.py" > "%LOG%" 2>&1
copy /Y "%LOG%" "%OUTPUTS%\check_estado_log.txt" >nul 2>&1
type "%LOG%"
pause
