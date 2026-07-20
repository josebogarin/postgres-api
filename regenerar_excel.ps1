$ErrorActionPreference = "Continue"
$base = "C:\proyecto FAST API"
$log  = "$base\regenerar_excel_log.txt"

"=== REGENERAR BECBUC_verificacion.xlsx ===" | Out-File $log
(Get-Date).ToString("yyyy-MM-dd HH:mm:ss") | Add-Content $log

# Verificar que el servidor esta corriendo
$svr = try { Invoke-WebRequest "http://localhost:8000/api/v1/torneo/activas" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop; "ok" } catch { "fail" }
if ($svr -ne "ok") {
    "ERROR: Servidor no responde en localhost:8000. Iniciar uvicorn primero." | Add-Content $log
    Get-Content $log
    exit 1
}
"Servidor OK." | Add-Content $log

# Generar Excel
"Ejecutando generar_excel_becbuc.py..." | Add-Content $log
$pyOut = & "$base\backend\.venv\Scripts\python.exe" "$base\generar_excel_becbuc.py" 2>&1
$pyOut | Add-Content $log

if (Test-Path "$base\BECBUC_verificacion.xlsx") {
    $size = (Get-Item "$base\BECBUC_verificacion.xlsx").Length
    $ts   = (Get-Item "$base\BECBUC_verificacion.xlsx").LastWriteTime
    "Excel generado: $size bytes, $ts" | Add-Content $log
    "OK" | Add-Content $log
} else {
    "ERROR: No se creo el archivo Excel." | Add-Content $log
}

# Comparar de nuevo
"Comparando Excel regenerado vs BD..." | Add-Content $log
$cmpOut = & "$base\backend\.venv\Scripts\python.exe" "$base\comparar_excel_vs_bd_full.py" 2>&1
$cmpOut | Add-Content $log

Get-Content $log
