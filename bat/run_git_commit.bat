@echo off
cd /d "%~dp0.."
if exist ".git\index.lock" del /f /q ".git\index.lock"
git config --global --add safe.directory "C:/proyecto FAST API" >nul 2>&1
git config user.name "Jose Bogarin"
git config user.email "jose.bogarin@gmail.com"
> git_commit_log.txt (
  echo === GIT ADD ===
  git add -A 2>&1
  echo === STAGED COUNT ===
  git diff --cached --name-only 2>&1 | find /c /v ""
  echo === COMMIT ===
  git commit -m "sesion 70: cierre definitivo del torneo (Espana campeon) + propuesta BECBUC 2.0 + scripts cierre/analisis + CLAUDE.md" 2>&1
  echo === LOG ===
  git log --oneline -5 2>&1
  echo === REMOTE ===
  git remote -v 2>&1
  echo === STATUS ===
  git status -s 2>&1 | find /c /v ""
)
echo DONE >> git_commit_log.txt
