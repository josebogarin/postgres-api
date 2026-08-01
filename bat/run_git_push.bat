@echo off
cd /d "%~dp0.."
set GIT_TERMINAL_PROMPT=0
> git_push_log.txt (
  echo === REMOTE SET ===
  git remote remove origin 2>&1
  git remote add origin https://github.com/josebogarin/postgres-api.git 2>&1
  git remote -v 2>&1
  echo === BRANCH ===
  git branch -M main 2>&1
  echo === PUSH ===
  git push -u origin main 2>&1
  echo === EXITCODE %ERRORLEVEL% ===
)
echo DONE >> git_push_log.txt
