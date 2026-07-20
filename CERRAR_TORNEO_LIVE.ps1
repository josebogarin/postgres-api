# CERRAR_TORNEO_LIVE.ps1 - Cierre del torneo con avance en vivo.
# Correr en PowerShell:  powershell -ExecutionPolicy Bypass -File "C:\proyecto FAST API\CERRAR_TORNEO_LIVE.ps1"
$ErrorActionPreference = "Stop"
Set-Location "C:\proyecto FAST API"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " BECBUC - CIERRE DEL TORNEO (en vivo)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Nota: si se cuelga en el paso 4 (calcular-puntajes), probablemente hay" -ForegroundColor Yellow
Write-Host "otro proceso python.exe ocupando uvicorn. Cerra esas consolas y volve a correr." -ForegroundColor Yellow
Write-Host ""

$py = "C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
& $py -u "C:\proyecto FAST API\cerrar_live.py"

Write-Host ""
Write-Host "Presione una tecla para cerrar..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
