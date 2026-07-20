@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
set OUT=reorg_fase_b1_out.txt
set STAT=backend\static
set DST=backend\static\_backup_html
echo ==== FASE B1 (mover backups HTML) ==== > %OUT%

echo [0] checkpoint commit pre-B1 >> %OUT%
git add -A >> %OUT% 2>&1
git commit -m "Checkpoint pre-B1: scripts verificacion item F" >> %OUT% 2>&1

if not exist "%DST%" mkdir "%DST%"
echo. >> %OUT%
echo [1] moviendo backups a _backup_html\ >> %OUT%
move "%STAT%\*.bak" "%DST%\" >> %OUT% 2>&1
move "%STAT%\*backup*.html" "%DST%\" >> %OUT% 2>&1
echo. >> %OUT%
echo --- contenido de _backup_html\: >> %OUT%
dir /b "%DST%" >> %OUT% 2>&1
echo. >> %OUT%
echo --- HTML activos que QUEDAN en static\ (raiz): >> %OUT%
dir /b "%STAT%\*.html" >> %OUT% 2>&1

echo. >> %OUT%
echo [2] commit Reorg fase B1 >> %OUT%
git add -A >> %OUT% 2>&1
git commit -m "Reorg fase B1 - backups HTML a backend/static/_backup_html/" >> %OUT% 2>&1
git log --oneline -4 >> %OUT% 2>&1

echo. >> %OUT%
echo [3] verificacion HTTP (200 esperado, activos NO tocados): >> %OUT%
echo /BECBUC-portal: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" http://localhost:8000/BECBUC-portal >> %OUT% 2>&1
echo /live: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" http://localhost:8000/live >> %OUT% 2>&1
echo /login: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" http://localhost:8000/login >> %OUT% 2>&1
echo /static/becbuc-live-playoffs.html: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" "http://localhost:8000/static/becbuc-live-playoffs.html" >> %OUT% 2>&1
echo /static/BECBUC-movil.html: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" "http://localhost:8000/static/BECBUC-movil.html" >> %OUT% 2>&1
echo /static/BECBUC-portal.html: >> %OUT%
curl -s -o nul -w "  http_code=%%{http_code}\n" "http://localhost:8000/static/BECBUC-portal.html" >> %OUT% 2>&1
echo ---- FIN ---- >> %OUT%
notepad %OUT%
