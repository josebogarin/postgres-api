# Mata procesos anteriores
Stop-Process -Name "cloudflared" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "ngrok" -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# Inicia cloudflared y captura output
$logFile = "C:\proyecto FAST API\cloudflared.log"
"" | Out-File $logFile

$proc = Start-Process -FilePath "C:\proyecto FAST API\cloudflared.exe" `
  -ArgumentList "tunnel", "--url", "http://localhost:8000" `
  -RedirectStandardOutput $logFile `
  -RedirectStandardError "C:\proyecto FAST API\cloudflared_err.log" `
  -NoNewWindow -PassThru

Write-Host "Cloudflared PID: $($proc.Id)"
Write-Host "Esperando URL..."
Start-Sleep 8

# Leer URL del log de error (cloudflared escribe la URL a stderr)
$errLog = Get-Content "C:\proyecto FAST API\cloudflared_err.log" -ErrorAction SilentlyContinue
$url = $errLog | Where-Object { $_ -match "trycloudflare\.com" } | Select-Object -First 1
if ($url) {
    Write-Host "URL: $url"
    $url | Out-File "C:\proyecto FAST API\cloudflared_url.txt"
} else {
    $errLog[-10..-1] | Out-File "C:\proyecto FAST API\cloudflared_url.txt"
}
