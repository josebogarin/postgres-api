<#
.SYNOPSIS
  Crea un nuevo proyecto conectado a Postgres API.

.EXAMPLE
  .\nuevo-proyecto.ps1
  .\nuevo-proyecto.ps1 -Nombre "mi-app" -Titulo "Mi App" -Tipo nextjs
  .\nuevo-proyecto.ps1 -Nombre "sync-clientes" -Titulo "Sync Clientes" -Tipo python
  .\nuevo-proyecto.ps1 -Nombre "app-movil" -Titulo "App Movil" -Tipo expo
#>
param(
  [string]$Nombre = "",
  [string]$Titulo = "",
  [ValidateSet("nextjs","python","expo")]
  [string]$Tipo   = ""
)

$NODE    = "C:\Users\Jose Bogarin\AppData\Local\nvm\v24.15.0\node.exe"
$PNPM    = "C:\Users\Jose Bogarin\AppData\Local\nvm\v24.15.0\pnpm.cmd"
$PYTHON  = "C:\Users\Jose Bogarin\AppData\Local\Programs\Python\Python311\python.exe"
$ROOT    = "C:\proyecto FAST API"

$TEMPLATES = @{
  nextjs = "$ROOT\plantillas\nextjs-postgres-api"
  python = "$ROOT\plantillas\python-api-client"
  expo   = "$ROOT\plantillas\expo-react-native"
}

# ── Pedir datos si no vienen por parametro ────────────────────────────────────
if (-not $Tipo) {
  Write-Host ""
  Write-Host "Tipo de proyecto:" -ForegroundColor Cyan
  Write-Host "  [1] nextjs  - Web app Next.js + TypeScript"
  Write-Host "  [2] python  - Script Python con cliente API"
  Write-Host "  [3] expo    - App movil Expo / React Native"
  Write-Host ""
  $opcion = Read-Host "Elige tipo (1/2/3)"
  $Tipo = switch ($opcion) {
    "1" { "nextjs" }
    "2" { "python" }
    "3" { "expo"   }
    default { "nextjs" }
  }
}

if (-not $Nombre) {
  $Nombre = Read-Host "Nombre del proyecto (ej: crm-ventas, sync-clientes)"
}
$Nombre = $Nombre.Trim().ToLower() -replace '[^a-z0-9-]', '-'

if (-not $Titulo) {
  $Titulo = Read-Host "Titulo visible en la UI (ej: CRM Ventas)"
}
$Titulo = $Titulo.Trim()

# ── Rutas de destino ─────────────────────────────────────────────────────────
$TEMPLATE = $TEMPLATES[$Tipo]

# nextjs va a la raiz (como antes), python/expo van a proyectos\
if ($Tipo -eq "nextjs") {
  $Destino = Join-Path $ROOT $Nombre
} else {
  $Destino = Join-Path "$ROOT\proyectos" $Nombre
}

# ── Validaciones ──────────────────────────────────────────────────────────────
if (Test-Path $Destino) {
  Write-Host ""
  Write-Host "ERROR: Ya existe la carpeta $Destino" -ForegroundColor Red
  exit 1
}

if (-not (Test-Path $TEMPLATE)) {
  Write-Host ""
  Write-Host "ERROR: No se encontro el template en $TEMPLATE" -ForegroundColor Red
  exit 1
}

# ── Copiar template ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Creando proyecto '$Nombre' (tipo: $Tipo)..." -ForegroundColor Cyan
Copy-Item -Recurse -Path $TEMPLATE -Destination $Destino

# Limpiar artefactos del template
Remove-Item -Recurse -Force "$Destino\node_modules" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Destino\.next"         -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Destino\.venv"         -ErrorAction SilentlyContinue
Remove-Item -Force "$Destino\pnpm-lock.yaml"         -ErrorAction SilentlyContinue
Remove-Item -Force "$Destino\package-lock.json"      -ErrorAction SilentlyContinue

# ── Reemplazar TEMPLATE_NAME y TEMPLATE_TITLE ─────────────────────────────────
Write-Host "Configurando nombre y titulo..." -ForegroundColor Cyan

$extensiones = ".ts",".tsx",".json",".css",".mjs",".py",".env.example",".md"
$archivos = Get-ChildItem -Recurse -File -Path $Destino |
  Where-Object { $_.Extension -in $extensiones -or $_.Name -like "*.env*" }

foreach ($archivo in $archivos) {
  $contenido = Get-Content $archivo.FullName -Raw -Encoding UTF8
  if ($contenido -match "TEMPLATE_NAME|TEMPLATE_TITLE") {
    $contenido = $contenido -replace "TEMPLATE_NAME",  $Nombre
    $contenido = $contenido -replace "TEMPLATE_TITLE", $Titulo
    Set-Content $archivo.FullName $contenido -Encoding UTF8 -NoNewline
  }
}

# ── Copiar .env.example -> .env ───────────────────────────────────────────────
if (Test-Path "$Destino\.env.example") {
  Copy-Item "$Destino\.env.example" "$Destino\.env"
  Write-Host "Creado .env desde .env.example" -ForegroundColor DarkGray
}

# ── Setup por tipo ────────────────────────────────────────────────────────────
Set-Location $Destino

if ($Tipo -eq "nextjs") {
  Write-Host "Instalando dependencias con pnpm..." -ForegroundColor Cyan
  & $PNPM install --ignore-scripts
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Advertencia: pnpm install termino con codigo $LASTEXITCODE" -ForegroundColor Yellow
  }
}

if ($Tipo -eq "python") {
  Write-Host "Creando entorno virtual Python..." -ForegroundColor Cyan
  & $PYTHON -m venv .venv
  Write-Host "Instalando dependencias..." -ForegroundColor Cyan
  & "$Destino\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  & "$Destino\.venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Advertencia: pip install termino con codigo $LASTEXITCODE" -ForegroundColor Yellow
  }
}

if ($Tipo -eq "expo") {
  Write-Host "Instalando dependencias Expo con npm..." -ForegroundColor Cyan
  & $NODE (& where.exe npm | Select-Object -First 1) install
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Intentando con npx expo install..." -ForegroundColor Yellow
    npx expo install
  }
}

# ── Puerto sugerido (solo nextjs) ─────────────────────────────────────────────
$Puerto = 3001
if ($Tipo -eq "nextjs") {
  while ((Get-NetTCPConnection -LocalPort $Puerto -ErrorAction SilentlyContinue)) {
    $Puerto++
  }
}

# ── Resultado ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Proyecto '$Nombre' creado correctamente"         -ForegroundColor Green
Write-Host "  Tipo: $Tipo"                                     -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Carpeta : $Destino"                              -ForegroundColor Green

if ($Tipo -eq "nextjs") {
  Write-Host "  Puerto  : $Puerto (sugerido)"                  -ForegroundColor Green
}
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""

switch ($Tipo) {
  "nextjs" {
    Write-Host "Para iniciar el proyecto:" -ForegroundColor Yellow
    Write-Host "  cd `"$Destino`""         -ForegroundColor White
    Write-Host "  pnpm dev --port $Puerto" -ForegroundColor White
    Write-Host ""
    Write-Host "Abre Claude en la carpeta y ejecuta /postgres-api" -ForegroundColor Cyan
    Write-Host "para cargar el contexto completo de la API."       -ForegroundColor Cyan
  }
  "python" {
    Write-Host "Para activar el entorno y ejecutar:" -ForegroundColor Yellow
    Write-Host "  cd `"$Destino`""                   -ForegroundColor White
    Write-Host "  .\.venv\Scripts\activate"           -ForegroundColor White
    Write-Host "  python main.py"                     -ForegroundColor White
    Write-Host ""
    Write-Host "Edita el .env con la URL de la API y tus credenciales." -ForegroundColor Cyan
  }
  "expo" {
    Write-Host "Para iniciar el proyecto Expo:" -ForegroundColor Yellow
    Write-Host "  cd `"$Destino`""               -ForegroundColor White
    Write-Host "  npx expo start"                -ForegroundColor White
    Write-Host ""
    Write-Host "Edita el .env con la IP local de tu maquina." -ForegroundColor Cyan
    Write-Host "  EXPO_PUBLIC_API_URL=http://192.168.1.X:8000/api/v1" -ForegroundColor White
  }
}
Write-Host ""
