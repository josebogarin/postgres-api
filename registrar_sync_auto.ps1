# registrar_sync_auto.ps1 - Ejecutar como Administrador

$pythonExe  = 'C:\proyecto FAST API\backend\.venv\Scripts\python.exe'
$scriptPath = 'C:\proyecto FAST API\sync_auto.py'
$workDir    = 'C:\proyecto FAST API'
$taskName   = 'BECBUC-SyncAPI'
$logFile    = 'C:\proyecto FAST API\sync_auto.log'

Write-Host "=== Probando sync_auto.py ===" -ForegroundColor Cyan
& $pythonExe $scriptPath

if (Test-Path $logFile) {
    Write-Host "Log creado OK:" -ForegroundColor Green
    Get-Content $logFile | Select-Object -Last 5
} else {
    Write-Host "AVISO: No se creo sync_auto.log" -ForegroundColor Yellow
}

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Eliminando tarea anterior..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Write-Host "=== Registrando Task Scheduler ===" -ForegroundColor Cyan
$action   = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptPath -WorkingDirectory $workDir
$trigger  = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 1) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest

Write-Host "=== Estado ===" -ForegroundColor Cyan
Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo | Select-Object LastRunTime, NextRunTime, LastTaskResult

Write-Host "Listo! Tarea registrada. Log en: $logFile" -ForegroundColor Green
