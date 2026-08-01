@echo off
cd /d "%~dp0.."
echo ============================================================
echo BECBUC 2026 - Excel Auditoria Fase de Grupos
echo ============================================================
echo.
backend\.venv\Scripts\python generar_excel_grupos_auditoria.py
echo.
pause
