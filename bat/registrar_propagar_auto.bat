@echo off
chcp 65001 >nul
echo Registrando tarea BECBUC-PropagarClubes (cada 5 min)...
powershell -NoProfile -Command "$a=New-ScheduledTaskAction -Execute '%~dp0..\.venv\Scripts\python.exe' -Argument '%~dp0..\propagar_auto.py' -WorkingDirectory '%~dp0..'; $t=New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date); $s=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew; Register-ScheduledTask -TaskName 'BECBUC-PropagarClubes' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force"
pause
