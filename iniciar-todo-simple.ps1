# Version simplificada: Solo arrancar todo, sin tanto ruido
# Uso: .\iniciar-todo-simple.ps1

Clear-Host
Write-Host "Iniciando plataforma..." -ForegroundColor Green

# Rutas
$Backend = "C:\proyecto FAST API\backend"
$Web = "C:\proyecto FAST API\web"

# Arrancar Backend en nueva ventana
Write-Host "Lanzando Backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Backend'; & '.\.venv\Scripts\uvicorn.exe' app.main:app --reload --port 8000"

# Pequeño delay para que el backend se inicie
Start-Sleep -Seconds 3

# Arrancar Frontend en nueva ventana
Write-Host "Lanzando Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Web'; python app.py"

# Pequeño delay
Start-Sleep -Seconds 2

# Abrir navegadores
Write-Host "Abriendo navegadores..."
Start-Process "http://localhost:5000"
Start-Process "http://localhost:8000/docs"

Write-Host @"

✅ ¡Todo iniciado!

Frontend:  http://localhost:5000
API:       http://localhost:8000/docs

User: admin@example.com
Pass: changeme123

"@ -ForegroundColor Green
