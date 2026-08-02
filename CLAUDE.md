# BECBUC — Guía estable del proyecto

BECBUC es un pozo de apuestas deportivas entre amigos. Backend FastAPI (puerto 8000) +
Live nuevo React/Next (`frontend-becbuc/`, servido en `/static/v2/`). Se apuesta partido
por partido en torneos de **clubes** (Libertadores, Sudamericana) y de **selecciones**
(Copa del Mundo, ya cerrada).

> Este archivo es **solo información estable**. El estado vivo está en **ESTADO.md**; la
> bitácora de decisiones técnicas en **docs/decisiones.md**; el histórico completo, en git.

## Stack

- Backend: Python + FastAPI + uvicorn, puerto 8000.
- BD torneo: PostgreSQL 16 en Docker → base **becbuc** (datos del torneo).
- BD backend: PostgreSQL 16 en Docker → base **app_db** (users, auth, config del portal). Son BDs distintas.
- Contenedor: `core-postgres` (siempre `-U app_user`; el rol `postgres` NO existe en Docker).
- Frontend: (1) Portal HTML estático `/static/BECBUC-portal.html` (+ `BECBUC-movil.html`);
  (2) Live nuevo React en `frontend-becbuc/` → export a `/static/v2/`.
- Auth: JWT — roles superadmin / admin / apostador.

## Directorios

```
C:\proyecto FAST API\             <- BECBUC (FastAPI, puerto 8000)
  backend\                        <- código Python
  backend\static\BECBUC-portal.html / BECBUC-movil.html   <- portal web
  backend\static\v2\              <- Live nuevo (build de frontend-becbuc; se regenera)
  frontend-becbuc\                <- Live nuevo (React/Next, fuente)
  documentacion\                  <- SQLs, PDFs, seeds, reglamentos
  bat\                            <- scripts .bat (usan %~dp0.. para ser portables)
  docs\                           <- documentación (decisiones.md, etc.)
C:\proyectos\                     <- RBAC separado (Flask, puerto 5000). NO mezclar.
```

## Levantar el entorno

Servidor (uvicorn):
```
cd "C:\proyecto FAST API\backend"
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
Portal: http://localhost:8000/static/BECBUC-portal.html · Live: http://localhost:8000/static/v2/

Docker / Postgres:
```
docker exec -it core-postgres psql -U app_user -d becbuc
docker exec core-postgres psql -U app_user -d becbuc -c "\dt"
Get-Content "C:\proyecto FAST API\documentacion\archivo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
```
Conexión externa (psycopg2, scripts): host=localhost port=5432 dbname=becbuc user=app_user password=superpassword.

Backup: `cd "C:\proyecto FAST API"; .\backup_becbuc.ps1`  (destino `C:\backup_becbuc\` + OneDrive).

Acceso externo (ngrok, plan Free, cuenta jose.bogarin@gmail.com):
```
cd "C:\proyecto FAST API"; .\ngrok.exe http 8000     (monitor: http://127.0.0.1:4040)
```
La URL de ngrok CAMBIA en cada reinicio (se avisa la del día). Rutas amigables en main.py:
`/becbuc-live` → `/static/v2/`, `/reglamento` → PDF del reglamento de clubes.

Rebuild + deploy del Live nuevo: `bat\rebuild_reiniciar.bat` (cierra uvicorn si está, recompila
`frontend-becbuc`, copia a `static/v2`, reinicia uvicorn).

## Reglas del proyecto

- **Privacidad**: nunca exponer el nombre real. Usar `apostador`/`username`/alias, nunca `nombre` primero.
- **apostador = username**: en `app_db.users` NO existe columna `apostador`; el alias es `username`.
  En scripts/SQL contra app_db usar SIEMPRE `username`.
- **Tanda de penales**: son 2 ítems separados — Ol (local) y Ov (visitante), 2 pts c/u. No combinarlos.
- **Tipos de torneo**: CLUBES (Libertadores, Sudamericana, Champions) NO tienen 3er puesto → de
  semis directo a la final. SELECCIONES (Mundial, Eurocopa, Copa América) SÍ tienen 3er puesto.
- **Reglamento por defecto**: un torneo sin reglamento propio usa el de Copa del Mundo
  (`registry.get_engine()` cae a `CopasMundoScoringEngine`, no al legacy 3/1/0).
- **Torneo cerrado = solo lectura** en el Live (`torneo.cerrado=TRUE` → MiProno no edita).
- **Estructura del playoff FIJA por seeding (`p.id`), NUNCA por fecha.** El bracket de clubes
  (`bracket-clubes`) ordena las llaves por `p.id`; cambiar fechas no debe reordenar el cuadro.
- **Fase KO cerrada**: cuando TODOS los partidos de una fase están finalizados, la fase se
  bloquea (`fase.bloqueada`) y no se editan más apuestas. El avance de clubes es automático
  (`clubes_bracket.avanzar_bracket_clubes`, posicional `Gan.{L}{k}` por agregado + penales).
- **Hora Paraguay = UTC−3 fijo** (Paraguay = Argentina, sin horario de verano desde 2024). Se
  guarda en UTC; el Live convierte a `America/Asuncion`.
- **Fecha/hora de partidos KO**: fuente = **ESPN** (API-Football trae placeholders). Ver skills
  `espn-horarios-fixtures` y `becbuc-fechas-fases-live`.
- **Reglamento oficial prevalece** sobre lógica anterior (ver tabla de puntajes más abajo).

## Base de datos

**becbuc** (torneo): `competicion` (+codigo), `torneo` (+cerrado, api_season, mostrar_live),
`equipo` (+nombre_es, codigo_iso, api_team_id, logo_url, fifa_ranking, fair_play_pts),
`fase` (+tipo, orden, bloqueada), `partido` (goles, penales_local/visitante, minuto_primer_gol,
amarillas, rojas, decisiones_var, penales_partido, sustituciones, equipo_clasificado_id,
api_fixture_id, eventos_api, fecha), `participacion`, `apuesta` (pred_*, pred_sustituciones,
pred_comodin, pred_penales_local/visitante_tanda, pred_equipo_clasifica, nombre_apostador,
numero_fifa), `apuesta_global` (A–G), `puntaje_detalle`, `puntaje_global`, `puntaje_item`,
`apostador_clasificados`, `auditoria_apuestas`, `mensaje_admin`.

**app_db** (backend/usuarios): `users` (username, nombre, telefono, becbuc_pin), `roles`,
`user_roles`, `sistema` (compartida con otros proyectos — cambios de esquema pueden romper el
arranque; ver historial git), etc.

## Arquitectura backend

Scoring engine — patrón **Strategy + Registry** (una competencia = un engine):
```
backend/app/services/scoring/
  base.py · registry.py · calculator.py · clubes_calculator.py · clubes_bracket.py
  engines/copa_mundo_2026.py   (reglamento Mundial)
  engines/copa_clubes.py       (reglamento nuevo de clubes: H/I por fase, Cambios, comodín, cruce, tanda)
  engines/default.py           (legacy 3/1/0, opt-in explícito)
```
Archivos clave: `apostador_bets.py` (God file, `/bets/*`: pronósticos, ranking, scoring, live),
`clubes_scoring.py` (endpoints de clubes + `/bets/partido-detalle/{id}`), `torneo_service.py`,
`bracket_service.py`, `ko_scoring.py`, `table_crud.py`, `repositories/ranking_repo.py`,
`services/reportes/*` (Excel), `services/sync_api_football.py`.

Endpoints clave: `POST /api/v1/auth/login` · `/bets/{grupos,mi-bracket,bracket-real,bracket-clubes,
ranking,apostadores,mis-partidos,live-panel,partido-detalle}` · `POST /bets/{guardar-apuestas,
live-guardar-apuestas,calcular-puntajes/{tid},calcular-puntajes-clubes/{tid},avanzar-bracket,avanzar-bracket-clubes/{tid},
sync-resultados}` · PIN: `/bets/{live-pin-estado,live-set-pin,live-verify-pin,live-recuperar-pin}` ·
`GET /torneo/activas` · `/torneo/buscar-liga` · `POST /torneo/importar-liga`.

## Frontend

- **Portal web** (`BECBUC-portal.html` + `BECBUC-movil.html`): admin/config, competiciones,
  reglamentos, monitoreo. Se mantiene como está (no se reescribe).
- **Live nuevo** (`frontend-becbuc/`): login por **PIN** (4 dígitos; admin PIN 1964 = solo lectura;
  recuperar por celular) → selector de torneo → tabs Playoff / Grupos / En Vivo / Pronós. / Puntaje.
  Componentes: BracketClubes, BracketTree, EnVivo, GruposView, MiProno, MatchReplay (popup replay
  minuto a minuto). Muestra nombre+apodo del apostador en sesión.

Reglamento oficial (Mundial — tabla de puntajes, referencia estable):
```
Concepto            | GR | 16avos | 8vos | 4tos | Semis | 3P | Final
H Resultado         |  4 |   6    |   8  |  10  |  12   | 14 |  20
I Marcador exacto   |  8 |  12    |  16  |  20  |  24   | 28 |  40
J Amarillas / K Rojas / L VAR / M Pen.juego / N Min.gol : 1 en toda fase
O Penales tanda     | -- |  2/eq  ...  2/eq  (KO)      P Equipo clasifica | 1..12 por fase
Globales A–G (una vez): A Campeón 20 · B Finalistas 10/eq (máx 20) · C Goleador 20 ·
  D Peor equipo 20 · E Mayor goleada 10+10 · F Etapa Paraguay 6 · G Goles Paraguay 6 (total 112).
Paraguay: DOBLE puntaje en conceptos de partido (no globales).
```
El reglamento **nuevo de clubes** (Opción C) está en `documentacion/reglamentos/` (Word+PDF) e
implementado en `engines/copa_clubes.py`.

## Credenciales (NO CAMBIAR)

```
jose (admin):  username=jose  password=catalina
apostadores:   password=becbuc2026  (ids 9-53)
Live nuevo:    auto-login jose/catalina en lib/api.ts (endpoints públicos)
```

## Protocolo de sesión
### Al iniciar
1. Leer este archivo y ESTADO.md.
2. Ejecutar `git log --oneline -20` y `git status` para verificar el
   estado real del repo (el .md puede estar desactualizado; el repo no).
3. Resumir en qué punto quedó el trabajo y confirmar el próximo paso
   con el usuario ANTES de modificar cualquier archivo.
### Durante
- Cada decisión técnica no trivial se registra en docs/decisiones.md
  en el momento, no al final.
### Al cerrar
1. Reescribir ESTADO.md completo (NO agregar abajo — se reescribe).
2. Sugerir un mensaje de commit descriptivo de la sesión.
### Reglas de los archivos
- CLAUDE.md: solo información estable. Si algo cambia semana a semana,
  no va acá.
- ESTADO.md: se sobrescribe cada sesión. El histórico vive en git.
- Nunca dar por hecho el contenido de ESTADO.md sin contrastarlo con
  git status.

## Regla anti-truncamiento (obligatoria)
El Edit tool trunca archivos silenciosamente cuando el contenido nuevo
es mayor que el original. No da error. Por eso:
### Antes de editar cualquier archivo
1. Registrar tamaño: `(Get-Item archivo).Length` y `(Get-Content archivo).Count`
2. Hacer copia: `Copy-Item archivo archivo.bak`
### Cómo editar
- Archivos < 300 líneas: reescribir COMPLETO con Write. Nunca edición parcial.
- Archivos > 300 líneas: no usar Edit para agregar contenido. Escribir el
  bloque nuevo en un archivo temporal y appendear con:
  `Add-Content -Path archivo -Value (Get-Content temp.md -Raw)`
- Nunca hacer varias ediciones seguidas sin verificar entre una y otra.
### Después de editar (SIEMPRE)
1. Volver a medir bytes y líneas. Reportar antes → después.
2. Si el archivo creció en contenido pero bajó o quedó igual en bytes:
   está truncado. Restaurar el .bak y avisar.
3. Verificar que el final del archivo es el esperado:
   `Get-Content archivo -Tail 10`
4. Para .py: `python -m py_compile archivo`
### Nunca
- Declarar un archivo "listo" sin haber verificado el conteo posterior.
- Asumir que la edición salió bien porque el tool no dio error.
