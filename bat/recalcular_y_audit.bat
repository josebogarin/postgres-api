@echo off
echo ========================================
echo  RECALCULAR PUNTAJES + AUDITORIA PATITO
echo ========================================

set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set LOG=%DIR%\recalcular_audit_log.txt
set OUTPUTS=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\agent\local_ditto_dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\outputs

echo [1/2] Recalculando puntajes...
%PYTHON% "%DIR%\recalcular_puntajes.py" > "%LOG%" 2>&1

echo [2/2] Regenerando auditoria Patito...
%PYTHON% "%DIR%\auditoria_jugador.py" patito 2 >> "%LOG%" 2>&1

echo [3/3] Copiando a outputs...
copy /Y "%DIR%\auditoria_patito.xlsx" "%OUTPUTS%\auditoria_patito.xlsx" >> "%LOG%" 2>&1

echo.
type "%LOG%"
echo.
pause
