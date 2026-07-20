@echo off
cd /d "C:\proyecto FAST API\backend"
if exist ".git\index.lock" del /f ".git\index.lock"
git add static/login.html
git commit -m "sesion 29: fix login.html"
git push origin main
git log --oneline -3
pause
