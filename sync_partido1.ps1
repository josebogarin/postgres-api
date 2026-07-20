# sync_partido1.ps1
# Recupera todos los datos de API-Football para el fixture 1499252 (partido_id=1)
# y los guarda en la base de datos becbuc.

$API_KEY     = "f13bee776659e2c20c715a81ecff2307"
$FIXTURE_ID  = 1499252
$PARTIDO_ID  = 1
$DB_CONTAINER = "core-postgres"
$DB_USER     = "app_user"
$DB_NAME     = "becbuc"

Write-Host "==> Consultando API-Football fixture $FIXTURE_ID ..."

$headers = @{
    "x-rapidapi-key"  = $API_KEY
    "x-rapidapi-host" = "v3.football.api-sports.io"
}
$url = "https://v3.football.api-sports.io/fixtures?id=$FIXTURE_ID"
$resp = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

if ($resp.errors -and $resp.errors.PSObject.Properties.Count -gt 0) {
    Write-Host "ERROR API: $($resp.errors | ConvertTo-Json)"
    exit 1
}

$fixture = $resp.response[0]
if (-not $fixture) {
    Write-Host "No se encontro fixture $FIXTURE_ID en API-Football"
    exit 1
}

# ── Goles ─────────────────────────────────────────────────────────────────────
$golesLocal     = $fixture.goals.home
$golesVisitante = $fixture.goals.away
$estado         = switch ($fixture.fixture.status.short) {
    "FT"  { "finalizado" }
    "AET" { "finalizado" }
    "PEN" { "finalizado" }
    "1H"  { "en_juego" }
    "HT"  { "en_juego" }
    "2H"  { "en_juego" }
    "ET"  { "en_juego" }
    "P"   { "en_juego" }
    default { "pendiente" }
}

Write-Host "   Goles: local=$golesLocal visitante=$golesVisitante estado=$estado"

# ── Penales tanda ──────────────────────────────────────────────────────────────
$penalesLocal     = $null
$penalesVisitante = $null
if ($fixture.score.penalty.home -ne $null) {
    $penalesLocal     = $fixture.score.penalty.home
    $penalesVisitante = $fixture.score.penalty.away
    Write-Host "   Penales tanda: local=$penalesLocal visitante=$penalesVisitante"
}

# ── Eventos: amarillas, rojas, minuto primer gol, VAR ─────────────────────────
$amarillas      = 0
$rojas          = 0
$minutoPrimerGol = $null
$var            = 0
$goalTypes      = @("Normal Goal","Missed Penalty","Own Goal")
$invalidGoals   = @("Goal Disallowed","Goal Cancelled","Offside Goal")

$localTeamId    = $fixture.teams.home.id
$visitTeamId    = $fixture.teams.away.id

foreach ($ev in $fixture.events) {
    $type   = $ev.type
    $detail = $ev.detail
    $min    = $ev.time.elapsed

    if ($type -eq "Card") {
        if ($detail -eq "Yellow Card")              { $amarillas++ }
        elseif ($detail -in @("Red Card","Yellow Red Card")) { $rojas++ }
    }
    elseif ($type -eq "Goal" -and $detail -notin $invalidGoals) {
        if ($minutoPrimerGol -eq $null) {
            $minutoPrimerGol = [int]$min
        }
    }
    elseif ($type -eq "Var") {
        $var++
    }
}

Write-Host "   Amarillas=$amarillas Rojas=$rojas VAR=$var MinutoPrimerGol=$minutoPrimerGol"

# ── Construir SQL ──────────────────────────────────────────────────────────────
$setParts = @(
    "goles_local = $golesLocal",
    "goles_visitante = $golesVisitante",
    "estado = '$estado'",
    "amarillas = $amarillas",
    "rojas = $rojas",
    "decisiones_var = $var"
)

if ($minutoPrimerGol -ne $null) {
    $setParts += "minuto_primer_gol = $minutoPrimerGol"
} else {
    $setParts += "minuto_primer_gol = NULL"
}

if ($penalesLocal -ne $null) {
    $setParts += "penales_local = $penalesLocal"
    $setParts += "penales_visitante = $penalesVisitante"
} else {
    $setParts += "penales_local = NULL"
    $setParts += "penales_visitante = NULL"
}

$setClause = $setParts -join ", "
$sql = "UPDATE partido SET $setClause WHERE id = $PARTIDO_ID; SELECT id, goles_local, goles_visitante, estado, amarillas, rojas, decisiones_var, minuto_primer_gol FROM partido WHERE id = $PARTIDO_ID;"

Write-Host "`n==> Ejecutando en BD ..."
Write-Host $sql

$sql | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME

Write-Host "`n==> Listo. Partido $PARTIDO_ID actualizado con datos de API-Football."
