@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=git_fase3b_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 3b - extraer exportar_puntajes a services/reportes/puntajes_excel.py (apostador_bets.py -85 lineas). BONUS: arregla bug latente (endpoint daba 500 por _dt no importado; ahora 200). golden 17/17" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -7 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
