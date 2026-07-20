# Script para iniciar Backend + Frontend con un solo comando
# Uso: .\iniciar-todo.ps1

Write-Host "=" * 70
Write-Host "INICIANDO PLATAFORMA FASTAPI + FLASK" -ForegroundColor Green
Write-Host "=" * 70

# Variables
$BackendPath = "C:\proyecto FAST API\backend"
$WebPath = "C:\proyecto FAST API\web"
$BackendPort = 8000
$WebPort = 5000

# Función para verificar si un puerto está en uso
function Test-Port($Port) {
    $Connection = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
    return $Connection.TcpTestSucceeded
}

# Limpiar puertos si es necesario
Write-Host "`n[1/4] Verificando puertos..." -ForegroundColor Yellow

if (Test-Port $BackendPort) {
    Write-Host "⚠️  Puerto $BackendPort está en uso. Intenta cerrar procesos existentes." -ForegroundColor Red
    Write-Host "Ejecuta en PowerShell: Get-NetTCPConnection -LocalPort $BackendPort | Stop-Process -Force" -ForegroundColor Gray
}

if (Test-Port $WebPort) {
    Write-Host "⚠️  Puerto $WebPort está en uso." -ForegroundColor Red
}

# Arrancar Backend
Write-Host "`n[2/4] Iniciando Backend FastAPI en puerto $BackendPort..." -ForegroundColor Cyan
Write-Host "      Ubicación: $BackendPath" -ForegroundColor Gray

$BackendProcess = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit -Command `"cd '$BackendPath'; & '.\.venv\Scripts\uvicorn.exe' app.main:app --reload --port $BackendPort`"" `
    -WindowStyle Normal `
    -PassThru

Write-Host "      PID: $($BackendProcess.Id)" -ForegroundColor Gray
Start-Sleep -Seconds 2

# Arrancar Frontend Web
Write-Host "`n[3/4] Iniciando Frontend Flask en puerto $WebPort..." -ForegroundColor Cyan
Write-Host "      Ubicación: $WebPath" -ForegroundColor Gray

$WebProcess = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit -Command `"cd '$WebPath'; python app.py`"" `
    -WindowStyle Normal `
    -PassThru

Write-Host "      PID: $($WebProcess.Id)" -ForegroundColor Gray
Start-Sleep -Seconds 3

# Abrir navegadores
Write-Host "`n[4/4] Abriendo navegadores..." -ForegroundColor Cyan

Write-Host "      ✓ Frontend Web: http://localhost:$WebPort" -ForegroundColor Green
Start-Process "http://localhost:$WebPort"

Write-Sleep -Seconds 2

Write-Host "      ✓ API Swagger: http://localhost:$BackendPort/docs" -ForegroundColor Green
Start-Process "http://localhost:$BackendPort/docs"

# Resumen
Write-Host "`n" + "=" * 70
Write-Host "✅ PLATAFORMA INICIADA CORRECTAMENTE" -ForegroundColor Green
Write-Host "=" * 70

Write-Host @"

📍 ACCESOS DISPONIBLES:
   • Frontend Web:    http://localhost:$WebPort
   • API Swagger:     http://localhost:$BackendPort/docs
   • API ReDoc:       http://localhost:$BackendPort/redoc
   • API Base:        http://localhost:$BackendPort/api/v1

👤 CREDENCIALES:
   • Email:    admin@example.com
   • Password: changeme123

📊 PROCESOS EN EJECUCIÓN:
   • Backend (PID $($BackendProcess.Id))
   • Frontend (PID $($WebProcess.Id))

⏹️  PARA DETENER TODO:
   1. Cierra ambas ventanas de PowerShell, o
   2. Ejecuta en una nueva PowerShell:
      Stop-Process -Id $($BackendProcess.Id) -Force
      Stop-Process -Id $($WebProcess.Id) -Force

💡 NOTAS:
   • Backend: http://localhost:$BackendPort
   • Frontend: http://localhost:$WebPort
   • Los navegadores se abrirán automáticamente
   • Las terminal se mantendrán abiertas para ver logs

" -ForegroundColor White

Write-Host "=" * 70
Write-Host "Script completado. Presiona Ctrl+C para detener." -ForegroundColor Yellow
Write-Host "=" * 70

# Mantener el script abierto
Read-Host "Presiona Enter para cerrar este script (NO cierra las aplicaciones)"
