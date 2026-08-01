@echo off
cd /d "%~dp0.."
set GIT_TERMINAL_PROMPT=0
> git_push_branch_log.txt (
  echo === CREAR RAMA ===
  git branch becbuc-sesion70 2>&1
  echo === PUSH RAMA ===
  git push -u origin becbuc-sesion70 2>&1
  echo === EXITCODE %ERRORLEVEL% ===
  echo === RAMAS ===
  git branch 2>&1
)
echo DONE >> git_push_branch_log.txt
