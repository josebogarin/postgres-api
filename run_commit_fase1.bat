@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=git_fase1_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 1 - red de seguridad: golden master torneo2 + tests no-regresion (17 passed)" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -4 >> %OUT% 2>&1
echo === contenido tests/golden === >> %OUT%
dir /b tests\golden >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
