# buscar_y_sync_partido1.ps1
# 1. Busca el fixture Mexico vs Sudafrica en la Copa del Mundo 2026 (liga 1)
# 2. Muestra el fixture encontrado para confirmar
# 3. Actualiza api_fixture_id en partido_id=1 y guarda todos los datos del partido

$API_KEY      = "f13bee776659e2c20c715a81ecff2307"
$PARTIDO_ID   = 1
$LEAGUE_ID    = 1       # FIFA World Cup en API-Football
$SEASON       = 2026
$DB_CONTAINER = "core-postgres"
$DB_USER      = "app_user"
$DB_NAME      = "becbuc"

$headers = @{
    "x-rapidapi-key"  = $API_KEY
    "x-rapidapi-host" = "v3.football.api-sports.io"
}

# ── Paso 1: Buscar todos los fixtures finalizados de la liga/temporada ─────────
Write-Host "==> Buscando fixtures finalizados World Cup 2026 ..."
$url = "https://v3.football.api-sports.io/fixtures?league=$LEAGUE_ID&season=$SEASON&status=FT"
$resp = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

if ($resp.errors -and ($resp.errors | ConvertTo-Json) -ne "{}") {
    Write-Host "ERROR API: $($resp.errors | ConvertTo-Json)"
    exit 1
}

$fixtures = $resp.response
Write-Host "   Total fixtures FT encontrados: $($fixtures.Count)"

# ── Paso 2: Filtrar Mexico vs Sudafrica ───────────────────────────────────────
$match = $fixtures | Where-Object {
    ($_.teams.home.name -match "Mexico|México" -and $_.teams.away.name -match "South Africa|Sudafrica|Sud.frica") -or
    ($_.teams.away.name -match "Mexico|México" -and $_.teams.home.name -match "South Africa|Sudafrica|Sud.frica")
}

if (-not $match) {
    Write-Host "`n No se encontro Mexico vs Sudafrica en FT. Buscando todos los estados..."
    $url2 = "https://v3.football.api-sports.io/fixtures?league=$LEAGUE_ID&season=$SEASON"
    $resp2 = Invoke-RestMethod -Uri $url2 -Headers $headers -Method Get
    $fixtures2 = $resp2.response
    Write-Host "   Total fixtures (todos los estados): $($fixtures2.Count)"

    # Mostrar primeros 20 para referencia
    Write-Host "`n   Primeros partidos encontrados:"
    $fixtures2 | Select-Object -First 20 | ForEach-Object {
        Write-Host "   ID=$($_.fixture.id) | $($_.teams.home.name) vs $($_.teams.away.name) | Estado=$($_.fixture.status.short) | Fecha=$($_.fixture.date)"
    }

    $match = $fixtures2 | Where-Object {
        ($_.teams.home.name -match "Mexico|México" -and $_.teams.away.name -match "South Africa|Sudafrica|Sud.frica") -or
        ($_.teams.away.name -match "Mexico|México" -and $_.teams.home.name -match "South Africa|Sudafrica|Sud.frica")
    }
}

if (-not $match) {
    Write-Host "`nNo se encontro el partido. Listando todos los partidos disponibles:"
    ($fixtures + $fixtures2) | Sort-Object { $_.fixture.date } | ForEach-Object {
        Write-Host "  ID=$($_.fixture.id) | $($_.teams.home.name) $($_.goals.home)-$($_.goals.away) $($_.teams.away.name) | $($_.fixture.status.short)"
    }
    exit 1
}

# Tomar el primero si hay varios
$f = if ($match -is [array]) { $match[0] } else { $match }
$fixtureId = $f.fixture.id

Write-Host "`n==> Fixture encontrado:"
Write-Host "   ID        : $fixtureId"
Write-Host "   Partido   : $($f.teams.home.name) $($f.goals.home) - $($f.goals.away) $($f.teams.away.name)"
Write-Host "   Estado    : $($f.fixture.status.short)"
Write-Host "   Fecha     : $($f.fixture.date)"

# ── Paso 3: Obtener detalle completo con eventos y estadisticas ────────────────
Write-Host "`n==> Obteniendo detalle completo del fixture $fixtureId ..."
$urlDet = "https://v3.football.api-sports.io/fixtures?id=$fixtureId"
$respDet = Invoke-RestMethod -Uri $urlDet -Headers $headers -Method Get
$fixture = $respDet.response[0]

# Goles
$golesLocal     = $fixture.goals.home
$golesVisitante = $fixture.goals.away
$estado = switch ($fixture.fixture.status.short) {
    "FT"  { "finalizado" }
    "AET" { "finalizado" }
    "PEN" { "finalizado" }
    default { "en_juego" }
}

# Penales tanda
$penalesLocal     = $null
$penalesVisitante = $null
if ($null -ne $fixture.score.penalty.home) {
    $penalesLocal     = $fixture.score.penalty.home
    $penalesVisitante = $fixture.score.penalty.away
}

# Eventos
$amarillas       = 0
$rojas           = 0
$minutoPrimerGol = $null
$var             = 0
$invalidGoals    = @("Goal Disallowed","Goal Cancelled","Offside Goal")

foreach ($ev in $fixture.events) {
    $type   = $ev.type
    $detail = $ev.detail
    $min    = $ev.time.elapsed

    if ($type -eq "Card") {
        if ($detail -eq "Yellow Card") { $amarillas++ }
        elseif ($detail -in @("Red Card","Yellow Red Card")) { $rojas++ }
    }
    elseif ($type -eq "Goal" -and $detail -notin $invalidGoals) {
        if ($null -eq $minutoPrimerGol) { $minutoPrimerGol = [int]$min }
    }
    elseif ($type -eq "Var") { $var++ }
}

Write-Host "   Goles     : local=$golesLocal visitante=$golesVisitante"
Write-Host "   Amarillas : $amarillas | Rojas: $rojas | VAR: $var"
Write-Host "   Minuto 1G : $minutoPrimerGol"
if ($null -ne $penalesLocal) { Write-Host "   Penales   : $penalesLocal - $penalesVisitante" }

# ── Paso 4: Actualizar BD ─────────────────────────────────────────────────────
$minGolSql = if ($null -ne $minutoPrimerGol) { $minutoPrimerGol } else { "NULL" }
$penLSql   = if ($null -ne $penalesLocal)    { $penalesLocal }    else { "NULL" }
$penVSql   = if ($null -ne $penalesVisitante){ $penalesVisitante } else { "NULL" }

$sql = @"
UPDATE partido SET
    api_fixture_id    = $fixtureId,
    goles_local       = $golesLocal,
    goles_visitante   = $golesVisitante,
    estado            = '$estado',
    amarillas         = $amarillas,
    rojas             = $rojas,
    decisiones_var    = $var,
    minuto_primer_gol = $minGolSql,
    penales_local     = $penLSql,
    penales_visitante = $penVSql
WHERE id = $PARTIDO_ID;

SELECT id, api_fixture_id, goles_local, goles_visitante, estado,
       amarillas, rojas, decisiones_var, minuto_primer_gol,
       penales_local, penales_visitante
FROM partido WHERE id = $PARTIDO_ID;
"@

Write-Host "`n==> Actualizando partido_id=$PARTIDO_ID en BD ..."
$sql | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME

Write-Host "`n==> Listo."
