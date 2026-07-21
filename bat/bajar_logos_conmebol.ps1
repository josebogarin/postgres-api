$dest = 'C:\proyecto FAST API\documentacion\iconos-copas'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$urls = @{
  'libertadores-oficial.png' = 'https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-libertadores.png'
  'sudamericana-oficial.png' = 'https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-sudamericana.png'
  'conmebol-oficial.svg'     = 'https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-conmebol.svg'
}
foreach ($k in $urls.Keys) {
  try {
    Invoke-WebRequest -Uri $urls[$k] -OutFile (Join-Path $dest $k) -Headers @{ 'User-Agent' = 'Mozilla/5.0' } -UseBasicParsing
    Write-Host "  OK  $k" -ForegroundColor Green
  } catch {
    Write-Host "  ERROR $k : $($_.Exception.Message)" -ForegroundColor Red
  }
}
Get-ChildItem $dest -Filter *oficial* | Select-Object Name, Length
