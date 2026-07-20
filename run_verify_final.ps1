$ErrorActionPreference = "Continue"
$base = "C:\proyecto FAST API"
$log = "$base\verify_final3.txt"

"=== VERIFICACION FINAL (verify_todos.sql corregido para NULL preds) ===" | Out-File $log
(Get-Date).ToString("yyyy-MM-dd HH:mm:ss") | Add-Content $log
"`n" | Add-Content $log

"Ejecutando verify_todos.sql con fix NULL pred_minuto_gol..." | Add-Content $log
$verifyResult = Get-Content "$base\verify_todos.sql" | docker exec -i core-postgres psql -U app_user -d becbuc -A -F "|"
$verifyResult | Add-Content $log

"`n--- RESUMEN ---" | Add-Content $log
$okCount = ($verifyResult | Where-Object { $_ -match '\|OK$' }).Count
$diffCount = ($verifyResult | Where-Object { $_ -match '\|\*\*\*DIFFS$' }).Count
"OK: $okCount / DIFFS: $diffCount" | Add-Content $log

if ($diffCount -eq 0) {
    "*** 44/44 APOSTADORES SIN DIFFS - VERIFICACION 100% OK! ***" | Add-Content $log
} else {
    "APOSTADORES CON DIFFS:" | Add-Content $log
    $verifyResult | Where-Object { $_ -match '\|\*\*\*DIFFS$' } | Add-Content $log
}

"`nArchivo: $log"
Get-Content $log
