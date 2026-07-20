# run_populate_y_analisis.ps1
# Paso 1: login + populate, Paso 2: análisis de confiabilidad

cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\Activate.ps1
cd "C:\proyecto FAST API"

Write-Host "=== Paso 1: Login ===" -ForegroundColor Cyan
$loginBody = '{"username":"jose","password":"catalina"}'
$loginResp = irm "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
$tok = $loginResp.access_token
Write-Host "Token OK" -ForegroundColor Green

Write-Host ""
Write-Host "=== Paso 2: Populate stats fuentes ===" -ForegroundColor Cyan
$result = irm "http://localhost:8000/api/v1/bets/populate-stats-fuentes/2" -Method POST -Headers @{Authorization="Bearer $tok"}
Write-Host "Procesados: $($result.procesados)  Errores: $($result.errores)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Paso 3: Análisis de confiabilidad ===" -ForegroundColor Cyan
python analizar_fuentes.py

Read-Host "Presiona Enter para cerrar"
