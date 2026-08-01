@echo off
chcp 65001 >nul
cd /d "%~dp0."
set OUT=git_dbcleanup_out.txt
echo === git add -A === > %OUT%
git add -A >> %OUT% 2>&1
echo === commit === >> %OUT%
git commit -m "Limpieza BD becbuc: DROP 11 tablas + 12 vistas del prototipo viejo (0 filas / no referenciadas). becbuc 32->21 tablas, 14->2 vistas. Backup pre-drop + golden 17/17 + Excel OK. app_db intacta. Scripts: assess/drop." >> %OUT% 2>&1
echo === log === >> %OUT%
git log --oneline -4 >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
