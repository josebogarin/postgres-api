@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=git_fase4_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Fase 4 piloto: nucleo compartido becbuc-core.js (banderas ISO) en becbuc-live.html (-61 lineas; /live 200 + core.js 200 + golden 17/17)" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -6 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
