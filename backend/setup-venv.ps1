<#
.SYNOPSIS
  Recrea el venv y levanta el backend FastAPI.
  Ejecutar desde: C:\proyecto FAST API\backend\
#>

$PYTHON = "C:\Users\Jose Bogarin\AppData\Local\Programs\Python\Python311\python.exe"
$ROOT   = "C:\proyecto FAST API\backend"

Set-Location $ROOT

# ── 1. Verificar Python ──────────────────────────────────────────────────────
if (-not (Test-Path $PYTHON)) {
    Write-Host "ERROR: No se encontro Python en $PYTHON" -ForegroundColor Red
    exit 1
}
Write-Host "Python OK: $PYTHON" -ForegroundColor Green

# ── 2. Borrar venv viejo si existe ───────────────────────────────────────────
if (Test-Path ".venv") {
    Write-Host "Borrando venv viejo..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".venv"
}

# ── 3. Crear venv nuevo ──────────────────────────────────────────────────────
Write-Host "Creando venv nuevo..." -ForegroundColor Cyan
& $PYTHON -m venv .venv
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR creando venv" -ForegroundColor Red; exit 1 }
Write-Host "Venv creado OK" -ForegroundColor Green

# ── 4. Instalar dependencias ─────────────────────────────────────────────────
Write-Host "Instalando dependencias (puede tardar 1-2 min)..." -ForegroundColor Cyan
& "$ROOT\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$ROOT\.venv\Scripts\python.exe" -m pip install -r "$ROOT\requirements.txt"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR instalando dependencias" -ForegroundColor Red; exit 1 }
Write-Host "Dependencias instaladas OK" -ForegroundColor Green

# ── 5. Levantar servidor ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Iniciando FastAPI en http://localhost:8000" -ForegroundColor Green
Write-Host "  Docs: http://localhost:8000/api/v1/docs" -ForegroundColor Green
Write-Host "  Ctrl+C para detener" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""

& "$ROOT\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
