@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=git_fase3_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 3 - extraer Excel auditoria a services/reportes/auditoria_excel.py (apostador_bets.py -608 lineas; estructura Excel identica verificada + golden 17/17)" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -6 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
