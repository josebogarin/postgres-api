# ============================================================
# backup_becbuc.ps1 - Backup completo de BECBUC
# Uso: .\backup_becbuc.ps1
# Genera un ZIP con codigo + dumps de BDs y lo copia a OneDrive
# ============================================================

$fecha      = Get-Date -Format "yyyyMMdd_HHmm"
$raiz       = "C:\proyecto FAST API"
$destino    = "C:\backup_becbuc\backup_$fecha"
$zipFinal   = "C:\backup_becbuc\BECBUC_backup_$fecha.zip"
$onedrive   = "C:\Users\Jose Bogarin\OneDrive - lambda consulting\consultorias JB\BECBUC"
$contenedor = "core-postgres"
$usuario    = "app_user"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  BECBUC - Backup $fecha" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. Crear carpeta destino
New-Item -ItemType Directory -Force -Path "$destino\db" | Out-Null
New-Item -ItemType Directory -Force -Path "$destino\codigo" | Out-Null

# 2. Verificar que Docker esta corriendo
Write-Host "[1/4] Verificando Docker..." -ForegroundColor Yellow
$dockerOk = docker ps --filter "name=$contenedor" --format "{{.Names}}" 2>$null
if ($dockerOk -ne $contenedor) {
    Write-Host "ERROR: El contenedor '$contenedor' no esta corriendo." -ForegroundColor Red
    Write-Host "       Inicialo con: docker start $contenedor" -ForegroundColor Red
    exit 1
}
Write-Host "      OK - contenedor $contenedor activo" -ForegroundColor Green

# 3. Dump base de datos becbuc
Write-Host ""
Write-Host "[2/4] Dump base de datos 'becbuc'..." -ForegroundColor Yellow
docker exec $contenedor pg_dump -U $usuario --no-owner --clean --if-exists becbuc > "$destino\db\becbuc_$fecha.sql"
if ($LASTEXITCODE -eq 0) {
    $size = (Get-Item "$destino\db\becbuc_$fecha.sql").Length / 1KB
    Write-Host ("      OK - becbuc_{0}.sql ({1:N0} KB)" -f $fecha, $size) -ForegroundColor Green
} else {
    Write-Host "      ERROR al dumpear becbuc" -ForegroundColor Red
}

# 4. Dump base de datos app_db
Write-Host ""
Write-Host "[3/4] Dump base de datos 'app_db'..." -ForegroundColor Yellow
docker exec $contenedor pg_dump -U $usuario --no-owner --clean --if-exists app_db > "$destino\db\app_db_$fecha.sql"
if ($LASTEXITCODE -eq 0) {
    $size = (Get-Item "$destino\db\app_db_$fecha.sql").Length / 1KB
    Write-Host ("      OK - app_db_{0}.sql ({1:N0} KB)" -f $fecha, $size) -ForegroundColor Green
} else {
    Write-Host "      ERROR al dumpear app_db" -ForegroundColor Red
}

# 5. Copiar guia de recuperacion
$guia = "$raiz\BECBUC_Guia_Recuperacion.docx"
if (Test-Path $guia) {
    Copy-Item $guia -Destination "$destino\BECBUC_Guia_Recuperacion.docx"
}

# 6. Copiar codigo (excluye .venv, __pycache__, node_modules)
Write-Host ""
Write-Host "[4/4] Copiando codigo fuente..." -ForegroundColor Yellow
$excluir = @(".venv", "__pycache__", "*.pyc", "node_modules", ".git", "alembic\versions\*.pyc")
robocopy "$raiz" "$destino\codigo" /E /XD ".venv" "__pycache__" "node_modules" ".git" /XF "*.pyc" /NFL /NDL /NJH /NJS | Out-Null
Write-Host "      OK - codigo copiado" -ForegroundColor Green

# 7. Comprimir todo en ZIP
Write-Host ""
Write-Host "Comprimiendo en ZIP..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "C:\backup_becbuc" | Out-Null
Compress-Archive -Path "$destino\*" -DestinationPath $zipFinal -Force
Write-Host "      OK" -ForegroundColor Green

# 8. Limpiar carpeta temporal
Remove-Item -Recurse -Force $destino

# 9. Copiar a OneDrive
Write-Host ""
Write-Host "Copiando a OneDrive..." -ForegroundColor Yellow
if (Test-Path (Split-Path $onedrive -Parent)) {
    New-Item -ItemType Directory -Force -Path $onedrive | Out-Null
    Copy-Item $zipFinal -Destination $onedrive -Force
    Write-Host "      OK - copiado a OneDrive" -ForegroundColor Green

    # Mantener solo los ultimos 5 backups en OneDrive
    $viejos = Get-ChildItem "$onedrive\BECBUC_backup_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5
    foreach ($v in $viejos) { Remove-Item $v.FullName -Force }
    if ($viejos.Count -gt 0) {
        Write-Host ("      Eliminados {0} backup(s) antiguos de OneDrive" -f $viejos.Count) -ForegroundColor DarkGray
    }
} else {
    Write-Host "      AVISO: OneDrive no encontrado en la ruta configurada." -ForegroundColor DarkYellow
    Write-Host "      El ZIP queda en C:\backup_becbuc\" -ForegroundColor DarkYellow
}

# 10. Resumen
$zipSize = (Get-Item $zipFinal).Length / 1MB
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Backup completado!" -ForegroundColor Green
Write-Host ("  Local:    {0}" -f $zipFinal) -ForegroundColor White
Write-Host ("  OneDrive: {0}" -f "$onedrive\BECBUC_backup_$fecha.zip") -ForegroundColor White
Write-Host ("  Tamanio:  {0:N1} MB" -f $zipSize) -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
