@echo off
chcp 65001 >nul
echo Registrando tarea BECBUC-PropagarClubes (cada 5 min)...
powershell -NoProfile -Command "$a=New-ScheduledTaskAction -Execute 'C:\proyecto FAST API\.venv\Scripts\python.exe' -Argument 'C:\proyecto FAST API\propagar_auto.py' -WorkingDirectory 'C:\proyecto FAST API'; $t=New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date); $s=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew; Register-ScheduledTask -TaskName 'BECBUC-PropagarClubes' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force"
pause
