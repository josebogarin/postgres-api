@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Iniciando backup_becbuc.ps1 ... (dumps BD + zip + OneDrive) > backup_out.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\backup_becbuc.ps1" >> backup_out.txt 2>&1
echo ---- FIN ---- >> backup_out.txt
notepad backup_out.txt
