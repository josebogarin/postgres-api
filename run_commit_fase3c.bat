@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=git_fase3c_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 3c - extraer ranking-export a services/reportes/ranking_excel.py (apostador_bets.py -658 lineas; estructura Excel identica verificada; +fix import StreamingResponse; golden 17/17)" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -8 >> %OUT% 2>&1
echo === tamano actual God file === >> %OUT%
python -c "print('apostador_bets.py:', sum(1 for _ in open(r'backend/app/api/v1/endpoints/apostador_bets.py', encoding='utf-8')), 'lineas')" >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
