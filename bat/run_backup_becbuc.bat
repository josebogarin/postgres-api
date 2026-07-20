@echo off
cd /d "C:\proyecto FAST API"
powershell -ExecutionPolicy Bypass -File "C:\proyecto FAST API\backup_becbuc.ps1" > backup_becbuc_log.txt 2>&1
echo DONE >> backup_becbuc_log.txt
