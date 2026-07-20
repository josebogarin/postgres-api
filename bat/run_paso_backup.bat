@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
echo Iniciando backup_becbuc.ps1 ... (dumps BD + zip + OneDrive) > backup_out.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\proyecto FAST API\backup_becbuc.ps1" >> backup_out.txt 2>&1
echo ---- FIN ---- >> backup_out.txt
notepad backup_out.txt
