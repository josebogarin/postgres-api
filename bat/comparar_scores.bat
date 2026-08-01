@echo off
chcp 65001 >nul
cd /D "%~dp0.."
echo Comparando BD vs Excel...
backend\.venv\Scripts\python.exe -u comparar_scores.py > comparar_scores_log.txt 2>&1
type comparar_scores_log.txt
