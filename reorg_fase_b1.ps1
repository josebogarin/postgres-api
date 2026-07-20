# reorg_fase_b1.ps1 — FASE B1 (segura): mover SOLO backups HTML a backend\static\_backup_html\
# NO toca HTML activos, ni main.py, ni links internos.
#   1) commit checkpoint  2) mover backups  3) commit "Reorg fase B1"  4) verificar serving HTTP
$ErrorActionPreference = 'Continue'
$raiz = 'C:\proyecto FAST API'
$stat = Join-Path $raiz 'backend\static'
$dst  = Join-Path $stat '_backup_html'
$log  = Join-Path $raiz 'reorg_fase_b1_out.txt'
Set-Location $raiz
"==== REORG FASE B1  $(Get-Date -Format 'yyyy-MM-dd HH:mm') ====" | Out-File $log
function L($m){ $m | Out-File $log -Append }

# ---------- 0) commit checkpoint (estado actual antes de mover) ----------
L "[0] Commit checkpoint (pre-B1)..."
git add -A 2>&1 | Out-Null
git commit -m "Checkpoint pre-B1: scripts verificacion item F" 2>&1 | ForEach-Object { L ("    " + $_) }

# ---------- 1) mover SOLO backups ----------
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$moved = @()
# *.bak en la raiz de static (no recursivo): incluye .bak, .gl5.bak, .mem.bak, .logout.bak
foreach ($f in Get-ChildItem -Path $stat -Filter *.bak -File) {
    Move-Item -LiteralPath $f.FullName -Destination $dst -Force; $moved += $f.Name
}
# backups .html por nombre (solo los que contienen 'backup' -> sesion50). NO toca activos.
foreach ($f in Get-ChildItem -Path $stat -File | Where-Object { $_.Extension -eq '.html' -and $_.Name -match 'backup' }) {
    Move-Item -LiteralPath $f.FullName -Destination $dst -Force; $moved += $f.Name
}
L ("[1] backups movidos a _backup_html\ : {0}" -f $moved.Count)
foreach ($m in $moved) { L ("      - " + $m) }

# ---------- 2) commit fase B1 ----------
L "[2] Commit 'Reorg fase B1'..."
git add -A 2>&1 | Out-Null
git commit -m "Reorg fase B1 - backups HTML a backend/static/_backup_html/" 2>&1 | ForEach-Object { L ("    " + $_) }
L "    ultimos commits:"
git log --oneline -3 2>&1 | ForEach-Object { L ("      " + $_) }

# ---------- 3) verificar serving HTTP (activos NO tocados) ----------
L "[3] Verificacion HTTP (uvicorn :8000) — deben dar 200:"
$urls = @('/BECBUC-portal','/live','/login','/static/becbuc-live-playoffs.html',
          '/static/BECBUC-movil.html','/static/BECBUC-portal.html','/static/becbuc-live.html')
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri ("http://localhost:8000" + $u) -UseBasicParsing -TimeoutSec 12
        L ("    {0,-40} -> {1}" -f $u, $r.StatusCode)
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        L ("    {0,-40} -> ERROR {1} {2}" -f $u, $code, $_.Exception.Message)
    }
}
L "==== FIN FASE B1 ===="
Start-Process notepad.exe $log
