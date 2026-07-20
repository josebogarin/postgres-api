<#
.SYNOPSIS
  Smoke tests completos contra el backend FastAPI en ejecucion.
  Requiere que el servidor este corriendo en localhost:8000.

.EXAMPLE
  cd "C:\proyecto FAST API\backend"
  .\test_api.ps1
#>

$BASE    = "http://localhost:8000/api/v1"
$EMAIL   = "admin@example.com"
$PASS    = "changeme123"
$PASS_WR = "wrong-password"

# ── Contadores ───────────────────────────────────────────────────────────────
$script:ok   = 0
$script:fail = 0
$script:skip = 0

# ── Helpers ──────────────────────────────────────────────────────────────────
function Pass($name) {
    Write-Host "  [PASS] $name" -ForegroundColor Green
    $script:ok++
}
function Fail($name, $detail) {
    Write-Host "  [FAIL] $name - $detail" -ForegroundColor Red
    $script:fail++
}
function Skip($name, $reason) {
    Write-Host "  [SKIP] $name - $reason" -ForegroundColor Yellow
    $script:skip++
}
function Section($title) {
    Write-Host ""
    Write-Host "-- $title " -ForegroundColor Cyan
}

function Invoke-API {
    param(
        [string]$Method,
        [string]$Path,
        [hashtable]$Body = $null,
        [string]$Token  = $null
    )
    $uri     = "$BASE$Path"
    $headers = @{ "Content-Type" = "application/json" }
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }

    try {
        $params = @{ Method = $Method; Uri = $uri; Headers = $headers; TimeoutSec = 10 }
        if ($Body) { $params["Body"] = ($Body | ConvertTo-Json -Compress) }
        $resp = Invoke-WebRequest @params -ErrorAction Stop
        return @{ Code = [int]$resp.StatusCode; Data = ($resp.Content | ConvertFrom-Json -ErrorAction SilentlyContinue) }
    } catch {
        $code = 0
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        $raw  = $null
        try { $raw = ($_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue) } catch {}
        $msg = $_.Exception.Message
        if ($_.Exception.InnerException) { $msg += " | " + $_.Exception.InnerException.Message }
        return @{ Code = $code; Data = $raw; Error = $msg }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "================================================" -ForegroundColor White
Write-Host "  FastAPI Smoke Tests  $BASE" -ForegroundColor White
Write-Host "================================================" -ForegroundColor White

# ── 1. HEALTH ────────────────────────────────────────────────────────────────
Section "1. HEALTH"

$r = Invoke-API GET "/health"
if ($r.Code -eq 200 -and $r.Data.status -eq "ok") { Pass "GET /health" }
else { Fail "GET /health" "status=$($r.Code)" }

$r = Invoke-API GET "/health/db"
if ($r.Code -eq 200 -and $r.Data.status -eq "ok") { Pass "GET /health/db" }
else { Fail "GET /health/db" "status=$($r.Code) - DB posiblemente caida" }

# ── 2. AUTH ──────────────────────────────────────────────────────────────────
Section "2. AUTH"

# Login correcto
$r = Invoke-API POST "/auth/login" @{ email = $EMAIL; password = $PASS }
if ($r.Code -eq 200 -and $r.Data.access_token) {
    Pass "POST /auth/login (credenciales validas)"
    $ACCESS  = $r.Data.access_token
    $REFRESH = $r.Data.refresh_token
} else {
    Fail "POST /auth/login" "status=$($r.Code) $($r.Data.detail)"
    $ACCESS = $null; $REFRESH = $null
}

# Login con password incorrecta
$r = Invoke-API POST "/auth/login" @{ email = $EMAIL; password = $PASS_WR }
if ($r.Code -eq 401) { Pass "POST /auth/login (password incorrecta -> 401)" }
else { Fail "POST /auth/login password incorrecta" "esperado 401, recibido $($r.Code)" }

# GET /me
if ($ACCESS) {
    $r = Invoke-API GET "/auth/me" -Token $ACCESS
    if ($r.Code -eq 200 -and $r.Data.email -eq $EMAIL) { Pass "GET /auth/me" }
    else { Fail "GET /auth/me" "status=$($r.Code)" }
} else { Skip "GET /auth/me" "sin token" }

# GET /me sin token -> 403/401
$r = Invoke-API GET "/auth/me"
if ($r.Code -in 401,403) { Pass "GET /auth/me sin token -> $($r.Code)" }
else { Fail "GET /auth/me sin token" "esperado 401/403, recibido $($r.Code)" }

# Refresh token
if ($REFRESH) {
    $r = Invoke-API POST "/auth/refresh" @{ refresh_token = $REFRESH }
    if ($r.Code -eq 200 -and $r.Data.access_token) {
        Pass "POST /auth/refresh"
        $ACCESS = $r.Data.access_token   # usar token renovado
    } else { Fail "POST /auth/refresh" "status=$($r.Code)" }
} else { Skip "POST /auth/refresh" "sin refresh token" }

# ── 3. USERS ─────────────────────────────────────────────────────────────────
Section "3. USERS"

$TEST_EMAIL = "smoketest_$(Get-Random)@test.com"
$USER_ID    = $null

if ($ACCESS) {
    # Listar usuarios
    $r = Invoke-API GET "/users/" -Token $ACCESS
    if ($r.Code -eq 200) { Pass "GET /users/ (lista)" }
    else { Fail "GET /users/" "status=$($r.Code)" }

    # Crear usuario
    $r = Invoke-API POST "/users/" @{ email = $TEST_EMAIL; password = "Test1234!"; full_name = "Smoke Test" } -Token $ACCESS
    if ($r.Code -eq 201 -and $r.Data.email -eq $TEST_EMAIL) {
        Pass "POST /users/ (crear)"
        $USER_ID = $r.Data.id
    } else { Fail "POST /users/ crear" "status=$($r.Code) $($r.Data.detail)" }

    # Email duplicado -> 409
    $r = Invoke-API POST "/users/" @{ email = $TEST_EMAIL; password = "Test1234!" } -Token $ACCESS
    if ($r.Code -eq 409) { Pass "POST /users/ email duplicado -> 409" }
    else { Fail "POST /users/ duplicado" "esperado 409, recibido $($r.Code)" }

    # Obtener por ID
    if ($USER_ID) {
        $r = Invoke-API GET "/users/$USER_ID" -Token $ACCESS
        if ($r.Code -eq 200 -and $r.Data.id -eq $USER_ID) { Pass "GET /users/{id}" }
        else { Fail "GET /users/{id}" "status=$($r.Code)" }

        # Actualizar
        $r = Invoke-API PATCH "/users/$USER_ID" @{ full_name = "Updated Name" } -Token $ACCESS
        if ($r.Code -eq 200 -and $r.Data.full_name -eq "Updated Name") { Pass "PATCH /users/{id}" }
        else { Fail "PATCH /users/{id}" "status=$($r.Code)" }
    }

    # ID inexistente -> 404
    $fakeId = [guid]::NewGuid().ToString()
    $r = Invoke-API GET "/users/$fakeId" -Token $ACCESS
    if ($r.Code -eq 404) { Pass "GET /users/{id} inexistente -> 404" }
    else { Fail "GET /users/{id} inexistente" "esperado 404, recibido $($r.Code)" }

} else { Skip "USERS" "sin token de admin" }

# ── 4. ROLES ─────────────────────────────────────────────────────────────────
Section "4. ROLES"

$ROLE_ID = $null

if ($ACCESS) {
    # Listar roles
    $r = Invoke-API GET "/roles/" -Token $ACCESS
    if ($r.Code -eq 200) { Pass "GET /roles/ (lista)" }
    else { Fail "GET /roles/" "status=$($r.Code)" }

    # Crear rol
    $roleName = "smoke-role-$(Get-Random)"
    $r = Invoke-API POST "/roles/" @{ name = $roleName; description = "Smoke test role" } -Token $ACCESS
    if ($r.Code -eq 201) {
        Pass "POST /roles/ (crear)"
        $ROLE_ID = $r.Data.id
    } else { Fail "POST /roles/ crear" "status=$($r.Code) $($r.Data.detail)" }

    # Actualizar rol
    if ($ROLE_ID) {
        $r = Invoke-API PATCH "/roles/$ROLE_ID" @{ description = "Updated" } -Token $ACCESS
        if ($r.Code -eq 200) { Pass "PATCH /roles/{id}" }
        else { Fail "PATCH /roles/{id}" "status=$($r.Code)" }
    }

    # Asignar rol a usuario
    if ($USER_ID -and $ROLE_ID) {
        $r = Invoke-API POST "/users/$USER_ID/roles" @{ role_id = $ROLE_ID } -Token $ACCESS
        if ($r.Code -eq 200) { Pass "POST /users/{id}/roles (asignar rol)" }
        else { Fail "POST /users/{id}/roles" "status=$($r.Code) $($r.Data.detail)" }

        # Quitar rol
        $r = Invoke-API DELETE "/users/$USER_ID/roles/$ROLE_ID" -Token $ACCESS
        if ($r.Code -eq 200) { Pass "DELETE /users/{id}/roles/{role_id} (quitar rol)" }
        else { Fail "DELETE /users/{id}/roles/{role_id}" "status=$($r.Code)" }
    }

} else { Skip "ROLES" "sin token de admin" }

# ── 5. APPLICATIONS ──────────────────────────────────────────────────────────
Section "5. APPLICATIONS"

$APP_ID  = $null
$appSlug = "smoke-app-$(Get-Random)"

if ($ACCESS) {
    # Listar apps
    $r = Invoke-API GET "/applications/" -Token $ACCESS
    if ($r.Code -eq 200) { Pass "GET /applications/ (lista)" }
    else { Fail "GET /applications/" "status=$($r.Code)" }

    # Crear app
    $r = Invoke-API POST "/applications/" @{ slug = $appSlug; name = "Smoke App"; description = "test" } -Token $ACCESS
    if ($r.Code -eq 201) {
        Pass "POST /applications/ (crear)"
        $APP_ID = $r.Data.id
    } else { Fail "POST /applications/ crear" "status=$($r.Code) $($r.Data.detail)" }

    if ($APP_ID) {
        # Obtener por ID
        $r = Invoke-API GET "/applications/$APP_ID" -Token $ACCESS
        if ($r.Code -eq 200) { Pass "GET /applications/{id}" }
        else { Fail "GET /applications/{id}" "status=$($r.Code)" }

        # Actualizar
        $r = Invoke-API PATCH "/applications/$APP_ID" @{ description = "updated" } -Token $ACCESS
        if ($r.Code -eq 200) { Pass "PATCH /applications/{id}" }
        else { Fail "PATCH /applications/{id}" "status=$($r.Code)" }

        # Asignar app a usuario
        if ($USER_ID) {
            $r = Invoke-API POST "/users/$USER_ID/applications" @{ application_id = $APP_ID } -Token $ACCESS
            if ($r.Code -eq 200) { Pass "POST /users/{id}/applications (asignar app)" }
            else { Fail "POST /users/{id}/applications" "status=$($r.Code)" }
        }
    }

    # Slug duplicado -> 409
    $r = Invoke-API POST "/applications/" @{ slug = $appSlug; name = "Dup" } -Token $ACCESS
    if ($r.Code -eq 409) { Pass "POST /applications/ slug duplicado -> 409" }
    else { Fail "POST /applications/ duplicado" "esperado 409, recibido $($r.Code)" }

} else { Skip "APPLICATIONS" "sin token de admin" }

# ── 6. AUDIT LOGS ────────────────────────────────────────────────────────────
Section "6. AUDIT LOGS"

if ($ACCESS) {
    $r = Invoke-API GET "/audit-logs/" -Token $ACCESS
    if ($r.Code -eq 200) { Pass "GET /audit-logs/ (lista)" }
    else { Fail "GET /audit-logs/" "status=$($r.Code)" }

    # Sin token -> 401/403
    $r = Invoke-API GET "/audit-logs/"
    if ($r.Code -in 401,403) { Pass "GET /audit-logs/ sin token -> $($r.Code)" }
    else { Fail "GET /audit-logs/ sin token" "esperado 401/403, recibido $($r.Code)" }
} else { Skip "AUDIT LOGS" "sin token" }

# ── 7. ADMIN - tablas y CRUD generico ────────────────────────────────────────
Section "7. ADMIN (CRUD generico)"

if ($ACCESS) {
    # Listar tablas
    $r = Invoke-API GET "/admin/tables" -Token $ACCESS
    if ($r.Code -eq 200 -and $r.Data.Count -gt 0) {
        Pass "GET /admin/tables (lista $($r.Data.Count) tablas)"
        $firstTable = $r.Data[0].name
    } else { Fail "GET /admin/tables" "status=$($r.Code)"; $firstTable = "users" }

    # Schema de tabla
    $r = Invoke-API GET "/admin/tables/users" -Token $ACCESS
    if ($r.Code -eq 200 -and $r.Data.columns) { Pass "GET /admin/tables/users (schema)" }
    else { Fail "GET /admin/tables/users" "status=$($r.Code)" }

    # Tabla inexistente -> 404
    $r = Invoke-API GET "/admin/tables/tabla_que_no_existe" -Token $ACCESS
    if ($r.Code -eq 404) { Pass "GET /admin/tables/{inexistente} -> 404" }
    else { Fail "GET /admin/tables/{inexistente}" "esperado 404, recibido $($r.Code)" }

    # Listar filas de users
    $r = Invoke-API GET "/admin/tables/users/rows?limit=5" -Token $ACCESS
    if ($r.Code -eq 200 -and $r.Data.PSObject.Properties.Name -contains "items") {
        Pass "GET /admin/tables/users/rows (lista paginada, total=$($r.Data.total))"
    } else { Fail "GET /admin/tables/users/rows" "status=$($r.Code)" }

    # Busqueda libre
    $r = Invoke-API GET "/admin/tables/users/rows?q=admin" -Token $ACCESS
    if ($r.Code -eq 200) { Pass "GET /admin/tables/users/rows?q=admin (busqueda)" }
    else { Fail "GET /admin/tables/users/rows?q=" "status=$($r.Code)" }

    # DDL: agregar columna de prueba
    $testCol = "smoke_col_$(Get-Random -Maximum 9999)"
    $r = Invoke-API POST "/admin/tables/roles/columns" @{
        col_name = $testCol; col_type = "text"; nullable = $true
    } -Token $ACCESS
    if ($r.Code -eq 200) {
        Pass "POST /admin/tables/roles/columns (agregar columna '$testCol')"

        # DDL: eliminar la columna (esperar que el pool se estabilice tras el ADD)
        Start-Sleep -Milliseconds 800
        $r2 = Invoke-API DELETE "/admin/tables/roles/columns/$testCol" -Token $ACCESS
        if ($r2.Code -eq 200) { Pass "DELETE /admin/tables/roles/columns/$testCol (eliminar columna)" }
        else { Fail "DELETE columna" "status=$($r2.Code) error=$($r2.Error)" }
    } else { Fail "POST /admin/tables/roles/columns" "status=$($r.Code) $($r.Data.detail)" }

} else { Skip "ADMIN" "sin token" }

# ── 8. LIMPIEZA ──────────────────────────────────────────────────────────────
Section "8. LIMPIEZA (eliminar datos de prueba)"

if ($ACCESS) {
    if ($USER_ID) {
        $r = Invoke-API DELETE "/users/$USER_ID" -Token $ACCESS
        if ($r.Code -eq 204) { Pass "DELETE /users/{id} (limpiar usuario test)" }
        else { Fail "DELETE /users/{id}" "status=$($r.Code)" }
    }
    if ($ROLE_ID) {
        $r = Invoke-API DELETE "/roles/$ROLE_ID" -Token $ACCESS
        if ($r.Code -eq 204) { Pass "DELETE /roles/{id} (limpiar rol test)" }
        else { Fail "DELETE /roles/{id}" "status=$($r.Code)" }
    }
    if ($APP_ID) {
        $r = Invoke-API DELETE "/applications/$APP_ID" -Token $ACCESS
        if ($r.Code -eq 204) { Pass "DELETE /applications/{id} (limpiar app test)" }
        else { Fail "DELETE /applications/{id}" "status=$($r.Code)" }
    }
} else { Skip "LIMPIEZA" "sin token" }

# ── RESUMEN ──────────────────────────────────────────────────────────────────
$total = $script:ok + $script:fail + $script:skip
Write-Host ""
Write-Host "================================================" -ForegroundColor White
Write-Host "  RESUMEN DE TESTS" -ForegroundColor White
Write-Host "================================================" -ForegroundColor White
Write-Host "  Total : $total" -ForegroundColor White
Write-Host "  PASS  : $($script:ok)" -ForegroundColor Green
Write-Host "  FAIL  : $($script:fail)" -ForegroundColor $(if ($script:fail -gt 0) {"Red"} else {"Green"})
Write-Host "  SKIP  : $($script:skip)" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor White
Write-Host ""

if ($script:fail -eq 0) {
    Write-Host "TODOS LOS TESTS PASARON" -ForegroundColor Green
} else {
    Write-Host "$($script:fail) test(s) fallaron - revisa los [FAIL] arriba" -ForegroundColor Red
    exit 1
}
