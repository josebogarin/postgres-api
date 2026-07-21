# Copia los logos oficiales guardados en documentacion\iconos-copas a backend\static\logos
# con los nombres base que espera el Live (mundial, champions, europa-league,
# copa-america, sudamericana, libertadores). La Eurocopa usa estrella (no logo).
$srcDir = 'C:\proyecto FAST API\documentacion\iconos-copas'
$dstDir = 'C:\proyecto FAST API\backend\static\logos'
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

$stylized = @('mundial.svg','eurocopa.svg','copa-america.svg','libertadores.svg','sudamericana.svg')

$rules = [ordered]@{
  'mundial'       = { param($n) $n -match 'mundial|world|fifa' }
  'champions'     = { param($n) $n -match 'champion' }
  'europa-league' = { param($n) $n -match 'europa' }
  'eurocopa'      = { param($n) ($n -match 'euro') -and ($n -notmatch 'europa') }
  'copa-america'  = { param($n) ($n -match 'america') -and ($n -notmatch 'sudameric') }
  'sudamericana'  = { param($n) $n -match 'sudameric' }
  'libertadores'  = { param($n) $n -match 'libertad' }
}

$all = Get-ChildItem $srcDir -File | Where-Object { $_.Extension -match '\.(png|svg|webp|jpg|jpeg)$' }
foreach ($base in $rules.Keys) {
  $rule = $rules[$base]
  $cands = $all | Where-Object { & $rule ($_.Name.ToLower()) }
  if (-not $cands) { Write-Host "  (sin fuente) $base" -ForegroundColor Yellow; continue }
  $best = $cands | Sort-Object `
    @{ Expression = { if ($_.Name -match 'oficial|official|logotype|white|ucl') { 0 } else { 1 } } }, `
    @{ Expression = { if ($stylized -contains $_.Name.ToLower()) { 1 } else { 0 } } }, `
    @{ Expression = { if ($_.Extension -match '\.svg$') { 1 } else { 0 } } }, `
    @{ Expression = { $_.Length }; Descending = $true } | Select-Object -First 1
  $target = "$base$($best.Extension.ToLower())"
  Copy-Item $best.FullName (Join-Path $dstDir $target) -Force
  Write-Host "  OK  $target  <-  $($best.Name)" -ForegroundColor Green
}
Write-Host "`n=== /static/logos ===" -ForegroundColor Cyan
Get-ChildItem $dstDir -File | Select-Object Name, Length
