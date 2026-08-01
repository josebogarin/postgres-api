@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set OUT=git_reorg_a_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Reorg fase A: mover 261 .bat a bat/, reorganizar documentacion/ en migraciones|fixes_oneoff|manuales_pdf|md" >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -3 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
