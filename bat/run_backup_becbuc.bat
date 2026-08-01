@echo off
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "%~dp0..\backup_becbuc.ps1" > backup_becbuc_log.txt 2>&1
echo DONE >> backup_becbuc_log.txt
