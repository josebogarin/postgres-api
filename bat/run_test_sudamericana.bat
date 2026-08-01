@echo off
cd /d "%~dp0.."
set PY=%~dp0..\backend\.venv\Scripts\python.exe
echo === Corrigiendo Bolivar-^>Gremio (3-2) ===
"%PY%" "%~dp0..\corregir_llave_ganador.py" 14 "Bolivar>Gremio:3-2" --apply
echo.
echo === Verificacion integral ===
"%PY%" "%~dp0..\verificar_sudamericana.py" > "%~dp0..\verificar_sudamericana_out.txt" 2>&1
type "%~dp0..\verificar_sudamericana_out.txt"
echo.
echo (resultado guardado en verificar_sudamericana_out.txt)
pause
