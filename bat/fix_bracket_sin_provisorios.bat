@echo off
echo === Aplicando bracket sin terceros provisorios ===
cd /d "%~dp0.."
python fix_bracket_sin_provisorios.py
pause
