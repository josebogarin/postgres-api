# reorg_fase_a.ps1 — Reorganizacion FASE A (segura, sin impacto en el server):
#   - mueve todos los .bat de la raiz a  bat\
#   - reorganiza  documentacion\  en subdirectorios (migraciones, fixes_oneoff, manuales_pdf, md)
# Log a reorg_fase_a_out.txt. No toca backend\ ni HTML.

$ErrorActionPreference = 'Continue'
$raiz = 'C:\proyecto FAST API'
$log  = Join-Path $raiz 'reorg_fase_a_out.txt'
Set-Location $raiz
"==== REORG FASE A  $(Get-Date -Format 'yyyy-MM-dd HH:mm') ====" | Out-File $log
function L($m){ $m | Out-File $log -Append }

# ---------- 1) .bat -> bat\ ----------
$batDir = Join-Path $raiz 'bat'
New-Item -ItemType Directory -Force -Path $batDir | Out-Null
$bats = Get-ChildItem -Path $raiz -Filter *.bat -File
$n = 0
foreach ($b in $bats) {
    # no mover el launcher que se este ejecutando (por si acaso)
    try { Move-Item -LiteralPath $b.FullName -Destination $batDir -Force; $n++ }
    catch { L ("  no se pudo mover {0}: {1}" -f $b.Name, $_.Exception.Message) }
}
L ("[1] .bat movidos a bat\ : {0} de {1}" -f $n, $bats.Count)

# ---------- 2) documentacion\ en subdirectorios ----------
$doc = Join-Path $raiz 'documentacion'
if (Test-Path $doc) {
    $sub = @{
        migraciones   = Join-Path $doc 'migraciones'
        fixes_oneoff  = Join-Path $doc 'fixes_oneoff'
        manuales_pdf  = Join-Path $doc 'manuales_pdf'
        md            = Join-Path $doc 'md'
    }
    foreach ($p in $sub.Values) { New-Item -ItemType Directory -Force -Path $p | Out-Null }

    $cPdf=0; $cMd=0; $cMig=0; $cFix=0
    # PDFs
    foreach ($f in Get-ChildItem -Path $doc -Filter *.pdf -File) {
        Move-Item -LiteralPath $f.FullName -Destination $sub.manuales_pdf -Force; $cPdf++
    }
    # MD
    foreach ($f in Get-ChildItem -Path $doc -Filter *.md -File) {
        Move-Item -LiteralPath $f.FullName -Destination $sub.md -Force; $cMd++
    }
    # SQL: migracion/vistas/drop/depuracion/seed/v_ -> migraciones ; resto -> fixes_oneoff
    foreach ($f in Get-ChildItem -Path $doc -Filter *.sql -File) {
        if ($f.Name -match '^(migracion|vistas|drop|depuracion|seed|v_|migrate)') {
            Move-Item -LiteralPath $f.FullName -Destination $sub.migraciones -Force; $cMig++
        } else {
            Move-Item -LiteralPath $f.FullName -Destination $sub.fixes_oneoff -Force; $cFix++
        }
    }
    L ("[2] documentacion: PDFs={0} MD={1} migraciones={2} fixes_oneoff={3}" -f $cPdf,$cMd,$cMig,$cFix)
    # cualquier otro archivo suelto queda como esta
    $restantes = Get-ChildItem -Path $doc -File | Where-Object { $_.Extension -notin @('.sql','.pdf','.md') }
    L ("    otros archivos que quedaron en documentacion\ (raiz): {0}" -f $restantes.Count)
} else {
    L "[2] No existe carpeta documentacion\"
}

L "==== FIN FASE A ===="
Start-Process notepad.exe $log
