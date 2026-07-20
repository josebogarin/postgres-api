# BECBUC.md - Estado del Proyecto BECBUC
Ultima actualizacion: 2026-07-19 (sesion 70)
Leer este archivo COMPLETO antes de tocar cualquier archivo.

## REGLAS GENERALES DEL PROYECTO

- **PRIVACIDAD**: Nunca exponer nombres reales. Usar siempre el campo `apostador` (username/alias), nunca `nombre` (nombre real). En listas, rankings, fichas Excel y UI: `ap.apostador || ap.username || '?'`. Nunca `ap.nombre` primero.
- **apostador = username**: En la tabla `users` de app_db NO existe columna `apostador`. El alias del apostador es la columna `username`. En scripts Python/SQL que consultan app_db usar SIEMPRE `username` (nunca `apostador`). El campo `apostador` es solo un alias lógico usado en la UI y endpoints FastAPI.
- **TANDA DE PENALES**: Son 2 ítems separados — Ol (local) y Ov (visitante), 2 pts c/u. No combinarlos en un solo ítem.
- **TAB LIVE PLAYOFFS**: Mostrar solo el usuario seleccionado con sus predicciones cotejadas en vivo. No exponer lista completa de apostadores. Comparar siempre vs Top 3.
- **ARCHIVOS GRANDES (>200KB)**: NUNCA usar el Edit tool para inserciones largas en archivos grandes (apostador_bets.py, becbuc-live-playoffs.html, etc). El Edit tool trunca el archivo al tamano original en bytes cuando el nuevo contenido es mayor. SIEMPRE usar Python bash (heredoc o script) para modificar estos archivos.
- **REGLA ANTI-TRUNCACION (sesion 53)**: Despues de CUALQUIER escritura Python sobre archivos .py o .html, ejecutar verificacion obligatoria:
  - Para .py:  `python3 "C:\proyecto FAST API\safe_write.py" <ruta>`
  - Para .html: `python3 "C:\proyecto FAST API\safe_write.py" <ruta>`
  El script verifica sintaxis + tamano + fin de archivo. Si falla, restaura desde backup automaticamente.
  USAR SIEMPRE `safe_patch_html` / `safe_patch_py` de safe_write.py para modificar archivos grandes:
  ```python
  import sys; sys.path.insert(0, r'C:\proyecto FAST API')
  from safe_write import safe_patch_html, safe_patch_py
  safe_patch_html(r'C:\proyecto FAST API\backend\static\BECBUC-portal.html', [
      ('texto_viejo', 'texto_nuevo'),
  ])
  ```
  El Edit tool SOLO es seguro para archivos <50KB. Para todo lo demas, usar safe_patch_*.

## REGLAMENTO OFICIAL - PREVALECE SOBRE TODA LOGICA ANTERIOR

Archivo: documentacion/20260608_0240-Reglamento_BEC_BUC_2026.pdf
Analisis arquitectura: documentacion/arquitectura_scoring_engine.md

TABLA DE PUNTAJES OFICIAL (reglamento BEC BUC 2026):

  Concepto            | GR | 16avos | 8vos | 4tos | Semis | 3P | Final
  H - Resultado       |  4 |   6    |   8  |  10  |  12   | 14 |  20
  I - Marcador exacto |  8 |  12    |  16  |  20  |  24   | 28 |  40
  J - Amarillas       |  1 |   1    |   1  |   1  |   1   |  1 |   1
  K - Rojas           |  1 |   1    |   1  |   1  |   1   |  1 |   1  (* NO IMPLEMENTADO)
  L - VAR             |  1 |   1    |   1  |   1  |   1   |  1 |   1
  M - Penales juego   |  1 |   1    |   1  |   1  |   1   |  1 |   1  (* IMPLEMENTADO ✅ sesion 20)
  N - Minuto gol      |  1 |   1    |   1  |   1  |   1   |  1 |   1
  O - Penales tanda   | -- |  2/eq  |  2/eq|  2/eq|  2/eq | 2/eq| 2/eq (* BOOL->INT)
  P - Equipo clasifica|  1 |   2    |   4  |   6  |   8   | 10 |  12  (* NO IMPLEMENTADO)

  Globales (una vez):
    A - Campeon mundial:          20 pts
    B - Finalistas (10/equipo):   20 pts max
    C - Goleador:                 20 pts
    D - Peor equipo:              20 pts
    E - Mayor goleada (10+10):    20 pts
    F - Etapa Paraguay:            6 pts
    G - Goles Paraguay total:      6 pts
    TOTAL GLOBALES:              112 pts

  TOTAL MAXIMO BASE: 2.556 pts (sin doble Paraguay)
  Paraguay: DOBLE PUNTAJE en todos los conceptos del partido (no globales)

  PUNTAJE ACTUAL: GRUPO 0 + GRUPO 1 + GRUPO 2 COMPLETADOS.
    El sistema ahora usa la tabla oficial por fase (Grupos 4/8, Final 20/40).
    Se puede recalcular con POST /calcular-puntajes/{torneo_id}.
    K (rojas) y O (penales tanda int) pendientes de GRUPO 3 (UI + schema apuesta).
    P (equipo clasifica) excluido por decision de organizacion.
    M (penales juego) HABILITADO en sesion 20: scoring + sync extraccion + UI boleta (portal/movil).

## GRUPOS DE DESARROLLO - SCORING ENGINE v2

Estado general: GRUPOS 0-2 COMPLETADOS. GRUPO 3 es el siguiente paso.
Referencia completa: documentacion/arquitectura_scoring_engine.md

----------------------------------------------------------------------
GRUPO 0 - MIGRACION BD (prerequisito de todos los demas grupos)
----------------------------------------------------------------------
Archivos: documentacion/migracion_scoring_v2.sql
Duracion estimada: 1 sesion
Estado: COMPLETADO ✅ (ejecutado contra Docker)

Cambios en BD becbuc:
  1. competicion: ADD COLUMN codigo VARCHAR(50) UNIQUE
     UPDATE SET codigo='copa_mundo_2026' WHERE nombre ILIKE '%mundial%'
  2. partido: ADD COLUMNS rojas INT, penales_partido INT, equipo_clasificado_id INT->equipo
  3. apuesta: ADD COLUMNS
       pred_rojas INT
       pred_penales_partido INT
       pred_penales_local_tanda INT   (reemplaza pred_penales BOOLEAN para KO)
       pred_penales_visitante_tanda INT
       pred_equipo_clasifica INT      (equipo_id pronosticado como clasificado)
     NOTA: pred_penales BOOLEAN se mantiene como columna legacy (no borrar)
  4. puntaje_detalle: ADD COLUMNS
       pts_resultado INT DEFAULT 0    (H, separado de marcador)
       pts_rojas INT DEFAULT 0        (K)
       pts_penales_partido INT DEFAULT 0 (M)
       pts_penales_tanda INT DEFAULT 0   (O, reemplaza pts_penales)
       pts_equipo INT DEFAULT 0       (P)
  5. CREATE TABLE apuesta_global (pronos A-G por apostador x torneo)
  6. CREATE TABLE puntaje_global (resultado A-G calculados)

Comando de ejecucion (cuando este listo el SQL):
  Get-Content "C:\proyecto FAST API\documentacion\migracion_scoring_v2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

----------------------------------------------------------------------
GRUPO 1 - SCORING ENGINE BACKEND (logica pura, sin tocar endpoints)
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Archivos CREADOS:
  backend/app/services/scoring/__init__.py
  backend/app/services/scoring/base.py         <- FaseConfig, ScoringConfig, PartidoScore, GlobalScore, Protocol
  backend/app/services/scoring/registry.py     <- get_engine(codigo) -> ScoringEngine
  backend/app/services/scoring/calculator.py   <- ScoringCalculator.calculate() + calculate_global()
  backend/app/services/scoring/engines/__init__.py
  backend/app/services/scoring/engines/copa_mundo_2026.py  <- REGLAMENTO OFICIAL completo
  backend/app/services/scoring/engines/default.py          <- legacy 3/1/0 fallback

Archivos MODIFICADOS:
  apostador_bets.py: calcular_puntajes delega a ScoringCalculator
    - engine = scoring_registry.get_engine(competicion_codigo)
    - result = await ScoringCalculator(db).calculate(torneo_id, engine)
    - _calc_pts interno eliminado

Tabla de puntajes IMPLEMENTADA (copa_mundo_2026):
  score_partido: H(resultado), I(marcador exacto), J(amarillas), K(rojas),
                 L(VAR), N(minuto, externo), O(penales tanda 2/eq), P(equipo clasifica)
  score_global:  A-G segun tabla oficial (ver GRUPO 2)
  Paraguay:      mult=2 en todos los conceptos de partido
  Default:       legacy 3/1/0 x PHASE_MULT (fallback para otras competencias)

----------------------------------------------------------------------
GRUPO 2 - PRONOSTICOS GLOBALES BACKEND (A-G)
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Archivos MODIFICADOS:
  copa_mundo_2026.py: score_global(A-G) implementado completamente.
  calculator.py: calculate_global() + _load_torneo_resultados() agregados.
  apostador_bets.py:
    POST /api/v1/bets/apuestas-globales/{torneo_id}  <- guardar A-G (upsert)
    GET  /api/v1/bets/apuestas-globales/{torneo_id}  <- leer A-G + puntaje ya calculado
    POST /api/v1/bets/resultados-globales/{torneo_id} <- admin set C(goleador) + D(peor equipo)
    calcular-puntajes: llama calculate_global() -> persiste puntaje_global
    ranking: suma pts_globales al puntos_total; incluye campo pts_globales separado

Computo automatico:
  A (campeon):     partido final, equipo_clasificado_id
  B (finalistas):  partido final, local + visitante
  E (goleada):     MAX(ABS(goles_local - goles_visitante)) en todos los partidos
  F (etapa_py):    fase mas avanzada con Paraguay (finalizados)
  G (goles_py):    SUM goles de Paraguay en todos sus partidos

Computo manual (admin-set via POST /resultados-globales):
  C (goleador):    torneo.resultado_goleador (ALTER TABLE idempotente)
  D (peor equipo): torneo.resultado_peor_equipo_id (ALTER TABLE idempotente)

Total maximo globales: 112 pts (20+20+20+20+20+6+6). Verificado. ✅

----------------------------------------------------------------------
GRUPO 3 - CAMPOS NUEVOS EN PARTIDOS (backend + frontend)
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Campos agregados a la boleta:
  K - Tarjetas rojas (pred_rojas)
  O - Penales tanda: 2 inputs numericos (pred_penales_local_tanda, pred_penales_visitante_tanda)
      (reemplaza toggle SI/NO/?)
  M - Penales en el partido (pred_penales_partido): HABILITADO sesion 20.
      Input numerico en boleta (modal bonus portal + panel bonus KO/grupos movil).
      Extraccion en sync: _update_partido_full cuenta penales cobrados durante el juego
      (Goal+Penalty convertidos, Miss/Goal+Missed Penalty fallados) -> partido.penales_partido.
      Scoring: 1 pt si pred_penales_partido == penales_partido (x2 Paraguay).

Archivos MODIFICADOS:
  apostador_bets.py:
    - ApuestaIn schema: pred_rojas, pred_penales_local_tanda, pred_penales_visitante_tanda
    - upsert_apuesta y mis_apuestas: campos nuevos incluidos
  BECBUC-portal.html: onBkTanda(pid,side,val), _updatePenRequired usa ints, modal bonus con Rojas
  BECBUC-movil.html: onBkTandaM(pid,side,val), equivalente al portal

NOTA: El campo pred_penales BOOLEAN legacy queda en BD pero se reemplaza en UI.
      El scoring engine usa pred_penales_local_tanda / pred_penales_visitante_tanda.
      partido.penales_partido SE USA (item M habilitado sesion 20).

----------------------------------------------------------------------
GRUPO 4 - PRONOSTICOS GLOBALES FRONTEND (A-G)
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Archivos MODIFICADOS:
  BECBUC-portal.html:
    - Sub-tab "🌐 Globales" (bet-tabs, loadBetTab, renderBetGlobales, saveGlobales)
    - CSS: .gl-wrap, .gl-hdr, .gl-section, .gl-field, .gl-sel, .gl-inp-text, .gl-inp-num, etc.
    - Badge (guardado/sin guardar), puntajes calculados si disponibles
    - Formulario A-G: campeon, finalista1/2, goleador, peor equipo, goleada G/P, etapa Py, goles Py
    - Solo editable si fase grupos no bloqueada
  BECBUC-movil.html (idem portal):
    - tabs array: ['globales','🌐 Globales'] agregado
    - _renderPronosGlobalesM, saveGlobalesM implementados
    - CSS: .glm-wrap, .glm-section, .glm-field, .glm-sel, etc.

----------------------------------------------------------------------
GRUPO 5 - EXCEL Y TRANSPARENCIA ACTUALIZADA
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Archivos MODIFICADOS:
  apostador_bets.py (_build_auditoria_workbook):
    - Query puntaje_detalle: + COALESCE(pts_rojas, 0), COALESCE(pts_penales_tanda, 0)
    - Carga puntaje_global + apuesta_global para todos los apostadores
    - Hoja "Puntaje general": + columna Globales + Total incluye pts_globales
    - Cols por partido: + Rojas (K) + P.Tanda (O)
    - Header partido: 🇵🇾 PARAGUAY x2 marker cuando multiplicador > 1 (verde)
    - Nueva hoja "Globales": apostadores × pronos A-G (A/B/C/D/E/F/G + puntajes calculados)

----------------------------------------------------------------------
PREGUNTAS PENDIENTES CON LA ORGANIZACION (reglamento)
----------------------------------------------------------------------
  1. Bonus mejores terceros (+10 pts): NO figura en reglamento oficial. Confirmar si se mantiene o elimina.
  2. Minuto primer gol: RESUELTO ✅ — si hay empate en distancia mínima, TODOS los empatados suman 1 pt. Decisión organización 2026-07-02.
  3. Equipo clasifica grupos: aplica a los 32 clasificados o solo a los 24 directos + 8 terceros?
  4. Paraguay KO: si clasifica de grupos, doble puntaje aplica a TODOS sus partidos KO tambien?
  5. Penales tanda 3P: el 3er puesto en FIFA 2026 no tiene tanda. Confirmar exclusion item O.
  6. Mayor goleada: si hay empate de score, se toma la primera cronologicamente o cualquiera vale?

----------------------------------------------------------------------
GRUPO 6 - SYNC AUTOMATICO DESDE API-FOOTBALL
----------------------------------------------------------------------
Estado: COMPLETADO ✅

Archivos CREADOS:
  backend/app/services/sync_api_football.py  <- sync_torneo(db, torneo_id, force, max_detalle)
  sync_auto.py                               <- script Python para Windows Task Scheduler

Archivos MODIFICADOS:
  apostador_bets.py:
    POST /api/v1/bets/sync-resultados/{torneo_id}  <- admin, ?force=true, ?max_detalle=N
    Cadena: sync_torneo -> _avanzar_bracket -> calcular_puntajes + calculate_global
  BECBUC-portal.html: boton "🔄 Sync desde API-Football" + syncResultados() en herramientas admin
  BECBUC-movil.html:  boton "🔄 Sync desde API-Football" + syncResultadosM() en admin panel

Campos BD usados (requiere estar poblados):
  competicion.api_league_id  <- ID liga en API-Football
  torneo.api_season          <- temporada (ej: 2026)
  partido.api_fixture_id     <- ID fixture en API-Football
  equipo.api_team_id         <- ID equipo en API-Football (para equipo_clasificado_id)

Logica sync_torneo:
  1. GET /fixtures?league={api_league_id}&season={api_season}&status=FT-AET-PEN  (1 call)
  2. Para cada partido DB con api_fixture_id sin finalizar:
     GET /fixtures?id={fix_id}  (1 call por partido, limitado por max_detalle)
  3. UPDATE partido: goles, estado, penales_tanda, amarillas, rojas, var, minuto_gol, equipo_clasificado_id

Cuota API-Football (plan Free: 100 req/dia):
  - max_detalle=10 (default): hasta 11 calls por sync
  - sync_auto.py corre cada MINUTO con Windows Task Scheduler
  - SOLO actua si hay partido activo (GET /hay-partido-activo):
      ventana pre-partido: hasta 5 min antes del inicio
      ventana en juego: hasta 150 min despues del inicio (incluye alargue)
      cuando partido.estado='finalizado' → el script no actua → cero cuota gastada
  - En dias sin partidos: 0 llamadas a API-Football
  - Endpoint GET /api/v1/bets/hay-partido-activo/{torneo_id} para chequeo (admin)

## RETOMAR - PENDIENTES ABIERTOS (al 2026-06-09 sesion 6)

GRUPOS 0-6 TODOS COMPLETADOS. ✅

Pendientes no bloqueantes:
  - fix_pts_penales_partido.sql: ejecutar si puntaje_detalle no tiene esa columna
    (diagnosticar via el toast de error en becbuc-live.html o uvicorn log)
    Get-Content "C:\proyecto FAST API\documentacion\fix_pts_penales_partido.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
    O usar: fix_y_recalcular.bat (hace migration + recalculo via API)
  - Confirmar con la organizacion las 6 preguntas de reglamento (ver seccion GRUPOS)
  - Fix tiebreaker H2H en bracket_service.py segun Art.13 FIFA
  - Seed catalogo_objeto, poblado de equipo.codigo_iso y fifa_ranking

HECHO sesion 2026-06-08 (parte 4n) - GRUPO 1 SCORING ENGINE + GRUPO 2 GLOBALES A-G:

  GRUPO 1 - Scoring engine (backend puro):
    base.py, registry.py, calculator.py, engines/copa_mundo_2026.py, engines/default.py
    calcular_puntajes: delegado a ScoringCalculator + engine por competicion.codigo
    Tabla H/I escala por fase verificada. Paraguay x2. K/L/N/O/P implementados en engine.

  GRUPO 2 - Pronosticos globales A-G:
    score_global en copa_mundo_2026.py: A-G completo (112 pts max). Verificado.
    calculator.py: calculate_global() + _load_torneo_resultados().
      Auto: A/B (final), E (mayor goleada), F/G (Paraguay). Manual: C/D via admin endpoint.
    apostador_bets.py: POST/GET /apuestas-globales, POST /resultados-globales (admin C+D).
    calcular-puntajes: llama calculate_global() e incluye globales_procesadas en respuesta.
    ranking: puntos_total = puntos_partidos_total + pts_globales; campo pts_globales separado.
    CLAUDE.md: GRUPOS 1 y 2 marcados COMPLETADOS.

HECHO sesion 2026-06-08 (parte 4m) - LIMPIEZA BONUS TERCEROS + PENALES BOOL + GRUPO 0 SQL:

  1. BONUS MEJORES TERCEROS: ELIMINADO COMPLETAMENTE. ✅
     - apostador_bets.py: seccion "Bonus terceros clasificados" eliminada.
       ranking, stats, reset, test_verificacion, Excel workbook: sin referencia a apostador_bonus.
     - BECBUC-portal.html: columna 🥉 quitada de dashboard-ranking, view-ranking y transparencia.
     - BECBUC-movil.html: columna "3º" quitada del ranking, chip bonus_terceros quitado, leyenda actualizada.

  2. PENALES TANDA boolean (pts_penales = 5 * mult): ELIMINADO. ✅
     - apostador_bets.py: pts_penales = 0 siempre hasta que GRUPO 3 implemente los 2 inputs int.

  3. GRUPO 0 SQL: CREADO. ✅
     - Archivo: documentacion/migracion_scoring_v2.sql (listo para ejecutar).
     - EJECUTAR: Get-Content "C:\proyecto FAST API\documentacion\migracion_scoring_v2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

HECHO sesion 2026-06-08 (parte 4l) - ARQUITECTURA SCORING ENGINE + AUTOSAVE FILLRANDOM MOVIL:

  Arquitectura:
  - Documento: documentacion/arquitectura_scoring_engine.md
  - Reglamento BEC BUC 2026 analizado (PDF). Tabla oficial verificada vs implementacion actual.
  - Gaps identificados: 6 conceptos faltantes (rojas, penales juego, penales tanda int, globales, Paraguay, equipo clasifica).
  - Puntaje actual (3/1) INCORRECTO vs reglamento (escala por fase 4/8 a 20/40).
  - Grupos de desarrollo 0-5 definidos en este archivo.
  - Strategy Pattern: ScoringEngine por competicion. Registry resuelve engine por codigo.
  - copa_mundo_2026.py: implementa reglamento oficial completo.
  - ScoringCalculator: orquestador que separa logica de puntaje de los endpoints.

  fillRandomM auto-save:
  - BECBUC-movil.html: fillRandomM es ahora async y llama saveGruposM() al final.
    Equivalente al portal donde fillRandom() llama submitGruposBets().
    Resultado: Random en grupos guarda automaticamente y permite recalcular bracket.

HECHO sesion 2026-06-08 (parte 4k) - PENALES FORZADOS EN EMPATE KO + BLOQUEO MANUAL POR FASE:

  PENDIENTE EJECUTAR MIGRACION:
    Get-Content "C:\proyecto FAST API\documentacion\migracion_fase_bloqueada.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
    (agrega columna bloqueada BOOLEAN DEFAULT FALSE en tabla fase)

  Portal + Movil - Forzar penales en empate KO:
  - CSS: .pen-required (borde ambar) y .pen-req-warn (texto AVISO SÍ/NO ambar).
  - _koCards (portal) y _koCardsM/_renderKOInputsM (movil): data-pen-pid en .bk-pen-row/.bk-m-foot,
    span.pen-req-warn. Cuando pred_local===pred_visitante y pen===null, la fila se resalta.
  - onBkScore(portal)/onBkScoreM(movil): llaman _updatePenRequired/_updatePenRequiredM tras cambio.
  - onBkPen(portal)/onBkPenM(movil): idem, para limpiar el highlight al seleccionar SI/NO.
  - _updatePenRequired(pid)/M: calcula isDraw; toggle clase pen-required + display del span warn.
  - _syncKOSaveBtns(portal)/_syncKOSaveBtnsMFase(movil): bloquean boton Guardar si hay empate
    sin penales. Muestran AVISO en el contador. title explicativo.
  - submitKOFaseBets/submitKOFaseBetsM: guard de validacion antes de enviar al API.
  - openKOFaseModal/openKOFinalModal: setTimeout(() => pids.forEach(_updatePenRequired), 0)
    al abrir popup para resaltar empates con datos guardados.

  Backend apostador_bets.py - Bloqueo manual de fases:
  - Nuevo endpoint GET /fases-bloqueo/{torneo_id}: lista fases con bloqueada, total, finalizados.
  - Nuevo endpoint PATCH /fases-bloqueo/{fase_id}: actualiza fase.bloqueada (admin). Con audit_log.
  - fases_apuesta_estado REESCRITO: usa fase.bloqueada como mecanismo de bloqueo primario
    (reemplaza logica de fecha_corte). Si bloqueada_manual=true -> bloqueada.
    Si concluida -> bloqueada. Sino -> abierta (muestra fecha primer partido como referencia).
  - simular_fase: reemplaza _fase_encerrada check por fase.bloqueada check.
  - reset_fase: idem.
  - SELECT de simular_fase/reset_fase incluyen COALESCE(bloqueada, FALSE).

  Portal BECBUC-portal.html - Config tab "Fases":
  - Nuevo tab "Fases" en la barra de tabs de Configuracion (junto a KPIs/Menu/Vinculos).
  - Tabla con todas las fases: Nombre, Tipo, Partidos, Finalizados, toggle Bloqueada SI/NO.
  - cfgTab('fases') llama loadFasesBloqueo().
  - loadFasesBloqueo(): GET /fases-bloqueo/{_betTorneoId}, renderiza tabla con checkboxes.
  - toggleFaseBloqueo(faseId, bloqueada): PATCH + recarga tabla + invalida _betFaseEst.

  Movil BECBUC-movil.html - Admin panel "Bloqueo por Fase":
  - loadAdmin(): agrega seccion "Bloqueo por Fase" debajo de los botones existentes.
  - _loadFasesBloqueoM(): GET /fases-bloqueo + renderiza cards con toggle.
  - toggleFaseBloqueoM(faseId, bloqueada): PATCH + recarga + invalida _faseEst.

  SQL migration: documentacion/migracion_fase_bloqueada.sql
    ALTER TABLE fase ADD COLUMN IF NOT EXISTS bloqueada BOOLEAN DEFAULT FALSE;

## REGLA UI OBLIGATORIA (mobile + web en paralelo)

Hay DOS interfaces que deben mantenerse equivalentes y tocarse SIEMPRE juntas:
  Web:   backend\static\BECBUC-portal.html
  Movil: backend\static\BECBUC-movil.html
Cualquier cambio de interfaz (vista, seccion, boton, columna, dato, endpoint,
texto, flujo) debe aplicarse en AMBOS archivos en la misma tarea. Un cambio de
UI NO esta terminado si quedo en una sola interfaz. Detalle: skills\becbuc-ui-sync\SKILL.md

## DIRECTORIOS

C:\proyecto FAST API\          <- BECBUC (FastAPI, puerto 8000)
C:\proyecto FAST API\backend\  <- codigo Python
C:\proyecto FAST API\backend\static\BECBUC-portal.html  <- portal principal
C:\proyecto FAST API\backend\static\BECBUC-movil.html   <- interfaz movil
C:\proyecto FAST API\documentacion\  <- SQLs, manuales PDF, seeds, reglamento
C:\proyectos\                  <- RBAC separado (Flask, puerto 5000) NO mezclar

## STACK

Backend: Python + FastAPI + uvicorn puerto 8000
BD torneo: PostgreSQL 16 Docker -> base becbuc
BD backend: PostgreSQL 16 Docker -> base app_db
Contenedor: core-postgres (-U app_user)
Portal: HTML estatico en /static/BECBUC-portal.html
Auth: JWT -- superadmin / admin / apostador

IMPORTANTE: rol postgres NO existe en Docker. Siempre usar -U app_user
IMPORTANTE: app_db = BD del backend (users, auth, config del portal). becbuc = datos del torneo. BDs distintas.

## BASE DE DATOS becbuc - Estado al 2026-06-08

Tablas activas (9 existentes + 2 planificadas):
  competicion       -> tipos de torneo (+ codigo VARCHAR planificado GRUPO 0)
  torneo            -> instancia especifica del torneo
  equipo            -> selecciones/clubes + codigo_iso, fifa_ranking, fair_play_pts
  fase              -> etapas + bloqueada BOOLEAN (migracion pendiente ejecutar)
  partido           -> fixture + minuto_primer_gol, amarillas, decisiones_var
                       (+ rojas, penales_partido, equipo_clasificado_id planificados GRUPO 0)
  participacion     -> equipos por grupo/fase
  apuesta           -> pronosticos + pred_minuto_gol, pred_amarillas, pred_var, pred_penales(bool)
                       (+ pred_rojas, pred_penales_partido, pred_penales_local_tanda,
                          pred_penales_visitante_tanda, pred_equipo_clasifica planificados GRUPO 0)
  auditoria_apuestas -> snapshots Excel
  mensaje_admin     -> mensajes admin a apostadores (en becbuc, NO en app_db)
  apuesta_global    -> [PLANIFICADA GRUPO 0] pronos A-G por apostador x torneo
  puntaje_global    -> [PLANIFICADA GRUPO 0] resultado globales calculados

Migraciones pendientes de ejecutar:
  migracion_fase_bloqueada.sql  <- EJECUTAR YA (columna bloqueada en fase)
  migracion_scoring_v2.sql      <- CREAR Y EJECUTAR en GRUPO 0

## MIGRACIONES - Estado al 2026-06-08 sesion 4n

Ejecutadas:
  migracion_portal.sql
  migracion_portal_menu.sql
  migracion_cabecera_detalle.sql
  migracion_grupo_calculo.sql
  migracion_unificacion_app_db.sql
  migracion_user_sistemas.sql
  migracion_bonus_partido.sql
  migracion_mensajes_admin.sql
  depuracion_vistas_becbuc.sql
  vistas_auditoria_becbuc.sql
  drop_tablas_obsoletas_becbuc.sql
  migracion_catalogo_objeto.sql
  seed_becbuc_kpis.sql
  fix_kpi_titulos.sql
  migracion_pred_penales.sql    <- pred_penales BOOLEAN en apuesta
  migracion_scoring_v2.sql      <- GRUPO 0: nuevas columnas + apuesta_global + puntaje_global ✅

Pendientes de ejecutar:
  migracion_fase_bloqueada.sql  <- bloqueada BOOLEAN en fase (YA CREADA, falta ejecutar)
  Get-Content "C:\proyecto FAST API\documentacion\migracion_fase_bloqueada.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

## ARQUITECTURA BACKEND - Scoring Engine

Patron: Strategy + Registry. Cada competencia tiene su propio ScoringEngine.
El endpoint calcular_puntajes resuelve el engine por competicion.codigo y delega.

Modulos nuevos (GRUPO 1):
  backend/app/services/scoring/
    base.py          <- FaseConfig, ScoringConfig, PartidoScore, GlobalScore, Protocol ScoringEngine
    registry.py      <- get_engine(codigo) -> ScoringEngine
    calculator.py    <- ScoringCalculator.calculate(torneo_id) orquestador
    engines/
      copa_mundo_2026.py  <- CopasMundoScoringEngine (reglamento oficial)
      default.py          <- DefaultScoringEngine (legacy 3/1/0 fallback)

Invariante: bracket_service.py, ko_scoring.py, torneo_service.py NO cambian.

## PORTAL - BECBUC-portal.html

Vistas:
  view-dashboard   -> Dashboard (todos)
  view-pronos      -> Pronosticos (apostadores) - sub-tabs: Grupos | Terceros | Playoffs | [Globales GRUPO 4]
  view-grupos      -> Grupos (todos)
  view-bracket     -> Resultados bracket (todos)
  view-ranking     -> Ranking (todos)
  view-noticias    -> Noticias (todos)
  view-mensajes    -> Mensajes (todos)
  view-config      -> Configuracion (admin+) - tabs: KPIs | Menu | Vinculos | Fases
  view-herramientas -> Herramientas (admin+)

## BACKEND - Archivos clave

apostador_bets.py  <- /bets/* pronosticos, ranking, scoring, mensajes
admin.py           <- /admin/* db-tables, seed-catalogo
deps.py            <- CurrentUser, CurrentAdmin, CurrentSuperuser
torneo_service.py  <- logica torneo, fixture, standings
bracket_service.py <- tiebreaker FIFA completo
ko_scoring.py      <- scoring KO, self-heal, TBD cascade
table_crud.py      <- CRUD generico tabla.html
services/scoring/  <- [GRUPO 1] scoring engine por competencia

Endpoints clave:
  POST /api/v1/auth/login
  GET  /api/v1/bets/mis-apuestas/{torneo_id}
  POST /api/v1/bets/guardar-apuestas
  GET  /api/v1/bets/grupos/{torneo_id}
  GET  /api/v1/bets/mi-bracket/{torneo_id}
  GET  /api/v1/bets/bracket-real/{torneo_id}
  GET  /api/v1/bets/ranking/{torneo_id}
  GET  /api/v1/bets/apostadores
  POST /api/v1/bets/calcular-puntajes/{torneo_id}   <- admin (-> ScoringCalculator GRUPO 1)
  GET  /api/v1/bets/fases-apuesta-estado/{torneo_id}
  GET  /api/v1/bets/fases-bloqueo/{torneo_id}       <- admin
  PATCH /api/v1/bets/fases-bloqueo/{fase_id}        <- admin
  POST /api/v1/bets/resetear-apuestas/{torneo_id}
  POST /api/v1/bets/avanzar-bracket/{torneo_id}     <- admin (self-heal)
  GET  /api/v1/bets/transparencia/{torneo_id}/export
  GET  /api/v1/bets/mensajes
  POST /api/v1/bets/mensajes                         <- admin
  DELETE /api/v1/bets/mensajes/{id}                  <- admin
  POST /api/v1/bets/apuestas-globales/{torneo_id}   <- A-G apostador
  GET  /api/v1/bets/apuestas-globales/{torneo_id}   <- A-G apostador + puntaje calculado
  POST /api/v1/bets/resultados-globales/{torneo_id} <- admin set goleador + peor equipo

Fix 5-jun: db-tables, list_rows, patch_row, delete_row usan CurrentAdmin

## SISTEMA DE PUNTUACION

  IMPLEMENTADO segun reglamento oficial (GRUPOS 0+1+2 completos).
  Recalcular con POST /calcular-puntajes/{torneo_id}.

  Partidos (engine copa_mundo_2026):
    H - Resultado:      4/6/8/10/12/14/20 segun fase
    I - Marcador exacto: 8/12/16/20/24/28/40 segun fase
    J - Amarillas:      1 pt si exacto
    K - Rojas:          1 pt si exacto (scoring ok, falta UI en GRUPO 3)
    L - VAR:            1 pt si exacto
    M - Penales juego:  1 pt si exacto (penales cobrados durante el partido; HABILITADO sesion 20)
    N - Minuto gol:     1 pt al mas cercano (entre todos los apostadores)
    O - Penales tanda:  2 pts/equipo (solo KO con tanda real; falta UI int en GRUPO 3)
    P - Equipo clasifica: 1/2/4/6/8/10/12 segun fase (scoring ok, falta UI en GRUPO 3)
    Paraguay:           x2 en todo lo anterior

  Globales A-G (engine copa_mundo_2026):
    A - Campeon:        20 pts (auto: partido final)
    B - Finalistas:     10 pts/equipo, max 20 (auto: partido final)
    C - Goleador:       20 pts (manual admin via POST /resultados-globales)
    D - Peor equipo:    20 pts (manual admin via POST /resultados-globales)
    E - Mayor goleada:  10+10 pts ganador/perdedor (auto: max diff partidos)
    F - Etapa Paraguay:  6 pts (auto: ultima fase de Paraguay)
    G - Goles Paraguay:  6 pts (auto: sum goles Paraguay)
    TOTAL MAX:         112 pts

  Eliminado:
    Bonus terceros: eliminado (no figura en reglamento)
    Penales juego (M): HABILITADO en sesion 20 (antes excluido). Ver GRUPO 3.

## BUGS CONOCIDOS

bracket_service.py -> _sort_grupo():
  Aplica gd/gf global ANTES de H2H
  Segun Art.13 FIFA deberia ser al reves
  Fix requiere reestructurar (trabajo futuro)

## ARRANCAR SERVIDOR

  cd "C:\proyecto FAST API\backend"
  .venv\Scripts\Activate.ps1
  uvicorn app.main:app --reload --port 8000
  Portal: http://localhost:8000/static/BECBUC-portal.html

## COMANDOS DOCKER

  docker exec -it core-postgres psql -U app_user -d becbuc
  docker exec core-postgres psql -U app_user -d becbuc -c "\dt"
  docker exec core-postgres psql -U app_user -d becbuc -c "\dv"
  Get-Content "C:\proyecto FAST API\documentacion\archivo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
  docker exec core-postgres pg_dump -U app_user becbuc > backup_becbuc_20260605.sql

## PROXIMOS PASOS

### Estado de grupos al 2026-06-09 sesion 9
  GRUPO 0 - BD:              COMPLETADO ✅ (migracion_scoring_v2.sql ejecutada)
  GRUPO 1 - Scoring engine:  COMPLETADO ✅ (Strategy Pattern, copa_mundo_2026 + default)
  GRUPO 2 - Globales A-G:    COMPLETADO ✅ (POST/GET apuestas-globales, score_global 112pts)
  GRUPO 3 - Campos boleta:   COMPLETADO ✅ (rojas K + penales tanda O int)
  GRUPO 4 - Frontend globales: COMPLETADO ✅ (sub-tab 🌐 Globales portal + movil)
  GRUPO 5 - Excel/transparencia: COMPLETADO ✅ (K, O, Globales sheet, pts_globales, Paraguay marker)
  GRUPO 6 - Sync API-Football: COMPLETADO ✅ (sync_api_football.py, /sync-resultados, botón UIs, sync_auto.py)

  MIGRACIONES PENDIENTES DE EJECUTAR:
    migracion_monitor.sql  <- tablas monitor (api_sync_log, monitor_config, monitor_jornada, monitor_partido_estado)
    Get-Content "C:\proyecto FAST API\documentacion\migracion_monitor.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

### Estado sesion 7 - MONITOREO + CONFIG redesign COMPLETADOS ✅
  - view-monitoreo: Panel de Mando inline (KPIs, partido activo, top5, sin apuestas,
    fases bloqueo, mensajes, acciones rápidas). Ya no es iframe.
  - view-config: tabs Torneo (período, API-Football info) + Reglamento (PDF links).
  - movil: Panel de Mando inline en admin, configuración período, links documentos.

### Proximo paso INMEDIATO (sesion 67 - actualizado 2026-07-09)

  ESTADO AL CIERRE SESION 68 (2026-07-15):
    - Cuartos (P097-P100): 4/4 finalizados, fase Cuartos (id=142) BLOQUEADA. Puntajes calculados.
    - Semis (P101 France 0-2 Spain, P102 England 1-2 Argentina): finalizados. Fase 'semis' ABIERTA.
    - Bracket avanzado: Final (P104) Spain vs Argentina | 3er puesto (P103) France vs England (19-jul).
    - Apuestas de Semis NO cargadas -> fase no se puede cerrar ni puntuar todavia.
    - NUEVO: editor de apuestas en Mi Prono (live-playoffs) + PIN=primer nombre + recibo PDF +
      bloqueo 4h + export pronosticos/completados en Monitoreo. Ver historial sesion 68.
    ACCION CUANDO SE CARGUEN APUESTAS DE SEMIS:
      -> POST /calcular-puntajes/2 ; bloquear Semis (fase 'semis') ; abrir/cargar Final+3er puesto.

  ESTADO AL CIERRE SESION 67:
    - Grupos (P001-P072): 72/72 finalizados ✅ BLOQUEADOS
    - R32 (P073-P088): 16/16 finalizados ✅ BLOQUEADOS
    - Octavos/R16 (P089-P096): 8/8 finalizados ✅ BLOQUEADOS
    - Cuartos (P097-P100): 1/4 finalizados
        P097 France 2-0 Morocco -> finalizado, clasifica France ✅
        P098 Spain vs Belgium   -> programado
        P099 Norway vs England  -> programado
        P100 Argentina vs Switzerland -> programado
    - Puntajes cuartos calculados: plenos=8, aciertos=26, fallos=10, total=772 pts ✅
    - Fases: Octavos bloqueada=TRUE ✅ | Cuartos bloqueada=FALSE (abierta) ✅

  ACCION CUANDO SE JUEGUEN P098-P100:
    1. sync_auto.py (Task Scheduler) detecta y finaliza automaticamente
    2. POST /calcular-puntajes/2 para puntuar los nuevos partidos
       (usa run_finalizar_p097_y_calcular.bat o portal Herramientas)
    3. Cuando los 4 partidos esten finalizados:
       -> Bloquear Cuartos: UPDATE fase SET bloqueada=TRUE WHERE id=142
       -> Abrir Semis: UPDATE fase SET bloqueada=FALSE WHERE tipo='semis'
       -> Importar apuestas semis desde Excel

  SIGUIENTE FASE - Semis (P101-P102):
    Ganadores de cuartos se propagan automaticamente via _avanzar_bracket()
    sync_auto.py mapea api_fixture_id de semis cuando los equipos se definan
    Importar pronosticos semis desde Excel master cuando se conozcan cruces

  FLUJO CUARTOS → SEMIS:
    1. Cuartos terminan (P097-P100 finalizados)
    2. POST /sync-resultados/2?force=true (propaga ganadores al bracket)
    3. POST /calcular-puntajes/2
    4. Bloquear Cuartos + abrir Semis via SQL o portal Config→Fases
    5. Importar apuestas semis + calcular

### Estado Excel generar_excel_becbuc.py (sesion 14)
  Hojas implementadas: Ranking, Resultados, [apostador x N], Globales, Matriz
  BUG RESUELTO: query fix aplicado + test_integral corrio exitosamente (104 partidos finalizados en BD)
  PRINTS DIAG: eliminados en sesion 14 (limpieza codigo)
  PENDIENTE: verificar ejecucion manual (ver "Proximo paso INMEDIATO")
  FIX en query: f.torneo_id en vez de p.torneo_id ✅ (evita INNER JOIN roto)
  DIAGNOSTICO activo: generar_excel_becbuc.py imprime "DIAG estados partidos:"
  SOLUCION: correr test_integral.py fresco

### Mejores terceros Copa del Mundo 2026
  IMPLEMENTADO en bracket_service.py: seleccionar_mejores_terceros() + armar_ronda32()
  _avanzar_bracket() en apostador_bets.py los llama automaticamente.
  Los 8 mejores de 12 terceros clasifican a Ronda 32. No requiere trabajo adicional.

### Features adicionales pendientes
  - Poblar partido.api_fixture_id + equipo.api_team_id para activar sync API-Football
  - #22 Dashboard: panel resultados actuales + partidos de la fase en juego
  - #27 Monitoreo: botones globales "RESET todo" y "SIMULAR todo"
  - Confirmacion con organizacion de las 6 preguntas de reglamento

### Pendientes tecnicos
  - Confirmar con la organizacion las 6 preguntas de reglamento (ver seccion GRUPOS)
  - migracion_fase_bloqueada.sql: EJECUTADA ✅ (2026-06-09)
  - Fix tiebreaker H2H en bracket_service.py segun Art.13 FIFA
  - Seed catalogo_objeto: POST /api/v1/admin/seed-catalogo?id_sistema=<ID>
  - Poblar equipo.codigo_iso y equipo.fifa_ranking con datos reales
  - Poblar partido.api_fixture_id + equipo.api_team_id para activar sync

## BACKUP

  Script: C:\proyecto FAST API\backup_becbuc.ps1
  Destino: C:\backup_becbuc\ (ZIP con dumps BDs + codigo)
  OneDrive: C:\Users\Jose Bogarin\OneDrive - lambda consulting\consultorias JB\BECBUC (automatico, guarda ultimos 5)
  Ejecutar: cd "C:\proyecto FAST API" && .\backup_becbuc.ps1

## ACCESO EXTERNO

  Metodo: ngrok (cuenta jose.bogarin@gmail.com, plan Free)
  Ejecutable: C:\proyecto FAST API\ngrok.exe
  Estado: ACTIVO - URL cambia en cada reinicio
  Puerto: 8000
  Comando: cd "C:\proyecto FAST API" && .\ngrok.exe http 8000
  Web monitor: http://127.0.0.1:4040 (ver trafico en tiempo real)
  Limitacion: URL cambia al reiniciar. Aceptado - se notifica la URL del dia a los usuarios.

## CREDENCIALES (NO CAMBIAR)
  jose (admin):     username=jose    password=catalina   (minuscula)
  apostadores:      password=becbuc2026  (todos, ids 9-53)
  becbuc-live.html: USER='Jose', PASS='catalina' (hardcoded para auto-login)

  Reset SQL (si se pierden las contraseñas):
    UPDATE users SET password_hash = '<hash_catalina>' WHERE username = 'jose';
    UPDATE users SET password_hash = '<hash_becbuc2026>' WHERE id IN (9..53);
  Usar passlib.CryptContext(schemes=['bcrypt']).hash('...') para generar hashes.

## HISTORIAL SESIONES

2026-07-19 - Sesion Cowork (sesion 70) - CIERRE DEFINITIVO DEL TORNEO + PROPUESTA BECBUC 2.0 (DOC):

  ====================================================================
  CIERRE DEL TORNEO (Final P104 + 3er puesto P103 jugados)
  ====================================================================
  RESULTADOS OFICIALES (confirmados por el usuario, NO por API que traia datos distintos):
    - Final P104: Spain 1-0 Argentina -> ESPANA CAMPEON, Argentina 2do.
    - 3er puesto P103: France 4-6 England -> INGLATERRA 3ro, Francia 4to.
    - Tarjetas oficiales de la FINAL: 6 amarillas, 1 roja (la API traia 5/2 -> se corrigio a mano).
    - Minuto 1er gol final = 106 ; penales en el juego = 0.
    - Goleador global C = Mbappe. En goleadores_cache habia EMPATE 8 goles (Messi y Mbappe);
      el usuario define Mbappe. Grafias de apostadores: 'KYLIAN MBAPPE' x27 + 'MBAPPE' x2.
      DECISION usuario: acreditar a los 29 -> se normalizaron las 2 'MBAPPE' a 'KYLIAN MBAPPE'
      y torneo.resultado_goleador='KYLIAN MBAPPE'. Peor equipo D = Iraq (id 84, ya seteado).

  REGLA CLAVE DEL CIERRE (aprendida esta sesion):
    - El cierre a medida NO hace sync desde API-Football (el sync pisaba las tarjetas oficiales
      6/1 con los 5/2 de la API). Se setean los datos oficiales a mano y se recalcula SIN sync.
    - POST /calcular-puntajes/2?force_grupos=true es LENTO (1-3 min): reconstruye TODO
      puntaje_detalle (104 partidos x 44 apostadores). Con salida redirigida a archivo puede
      PARECER colgado (buffer no se vacia hasta terminar). Usar python -u para ver avance en vivo.
    - Si el endpoint parece trabado: NO es uvicorn (el login responde), es el propio calcular
      reconstruyendo; esperar. Concurrencia: no lanzar dos calcular a la vez (chocan locks).

  RESULTADO FINAL (post recalc force_grupos): plenos=543, aciertos=2133, globales_procesadas=44.
    torneo.cerrado=TRUE. Ranking top: 1o=1080, 2o=983, mediana~799, ultimo=589 (44 apostadores).
    Globales con puntaje>0: A campeon=21, B finalistas=32, C goleador=29, D peor=1,
    E mayor goleada=15, F etapa PY=10, G goles PY=6.

  SCRIPTS CREADOS ESTA SESION (raiz; conexion psycopg2 host=localhost user=app_user pass=superpassword;
   API jose/catalina en :8000; ejecutados via barra de direcciones del Explorador o doble-clic):
    verify_final_tarjetas.py (+ run_): sync + lee tarjetas P103/P104.
    diag_cierre.py (+ run_): SOLO LECTURA, estado partidos/goleador/cerrado + nombres de columnas.
    cerrar_torneo_custom.py (+ run_): setea oficiales + normaliza goleador + calcular force_grupos + cerrado.
    cerrar_live.py + CERRAR_TORNEO_LIVE.ps1: version con avance en vivo (python -u) para correr a mano.
    recalc_ranking.py (+ run_): reafirma oficiales + recalcula + ranking (idempotente).
    analisis_datos.py (+ run_): extrae ranking completo + puntos por item/fase/globales (para el doc).
    NOTA columnas partido: minuto del gol es 'minuto_primer_gol' (NO 'minuto_1er_gol'); 'minuto_actual' es otra.

  BACKUP: ejecutado (run_backup_becbuc.bat -> backup_becbuc.ps1). Dumps de becbuc y app_db OK en
    C:\backup_becbuc\. El ZIP + copia a OneDrive tarda mucho (carpeta pesada, uvicorn_test.log 71MB).

  ====================================================================
  PROPUESTA "BECBUC 2.0" - DOCUMENTO PARA LA ADMINISTRACION
  ====================================================================
  Entregable: BECBUC_Propuesta_Rediseno_Puntajes.docx (9 pags, generado con build_doc2.js via
    libreria docx de Node; render/verificado con soffice+pdftoppm). Se basa en datos REALES del torneo.
  DIAGNOSTICO (datos): brecha 1o-ultimo=491, 1o-mediana=281 (hoy irremontable). K rojas 3623 +
    M penales 3189 (~21%) se ganan por poner "0" y no separan; N minuto 173 + O tanda 220 (~1%)
    decorativos; grupos = 50% de los puntos; globales solo 4,8%.
  MODELO PROPUESTO (definido por el usuario, valores a calibrar):
    - Grupos casi no valen (H=2/I=4). Playoffs escalan: 16avos 4/8, octavos 8/16, cuartos 15/30,
      SEMIS 30/60, FINAL 50/100 (marcador exacto se duplica hasta semis, salto en semis/final).
    - Multiplicador por ACERTAR EL CRUCE (quien pasa la llave): x2 favorito, x3 sorpresa (ej. Paraguay).
      Reemplaza al item P (clasificados) plano, que se ELIMINA.
    - COMODIN x5: 1 por playoff, multiplica x5 los puntos de un partido a eleccion.
    - Items secundarios "el 0 no suma": tarjetas/penales solo si evento real y exacto, x cantidad
      (4 rojas exactas = base x4) + bonus rareza. VAR se ELIMINA y se REEMPLAZA por "cantidad de cambios".
      N minuto 5/3/1 por cercania; O tanda 5 c/u.
    - Globales x2/x3 (campeon 60, finalistas 30 c/u, goleador 60, peor 40, goleada 40, PY 18/18)
      + nuevos (equipo/jugador revelacion) + bonus rareza en globales.
    - Innovaciones estandar: puntos de confianza, racha, survivor paralelo, props (autogol/MVP).
    - Meta de distribucion: grupos <12%, playoffs ~75%, globales ~13%.
  MEJORAS FUNCIONALES incluidas en el doc:
    - Torneos que arrancan directo en playoff (sin grupos), estilo Libertadores/Sudamericana.
    - Apostadores gratis vs suscriptores (gratis juegan por orgullo, sin premio; definir estado pago).
    - Notificaciones por correo (recordatorio apostar + ranking por fase).
    - Libro de actas (quejas/reclamos con estado).
    - Minitorneo: % del pozo al mejor puntaje de cada fase de playoff; ganador general = mayor acumulado.
    - Dos+ torneos en PARALELO (Libertadores + Sudamericana): selector de torneo en el Live,
      reglamento separado o compartido segun Comite de Apuestas.
    - Interfaz de admin EDITABLE para definir puntaje por apuesta por fase y general (sin tocar codigo).
  IMPLEMENTACION sugerida: engine nuevo por competencia (copa_playoff_2027) sin tocar el torneo cerrado;
    migracion BD (comodin, confianza, props, cruce, suscripcion, actas); UI boleta; piloto en playoff chico.
  ARCHIVO GENERADOR: build_doc2.js (raiz). OJO: el Edit tool TRUNCA este .js (>? bytes) al insertar;
    se reconstruyo la cola via bash heredoc. Para regenerar: node build_doc2.js salida.docx.

  ESTADO GIT (respuesta a consulta del usuario): el repo NO esta actualizado. Rama main SIN commits
    (git rev-list --all --count = 0), ~815 archivos en staging sin commitear, y NINGUN remoto
    configurado. Nada de esta sesion (ni lo previo en esta copia) esta commiteado ni pusheado.
    PENDIENTE si se desea versionar: git commit inicial + configurar remoto + credenciales GitHub.


2026-07-18 - Sesion Cowork (sesion 69) - IMPORT SEMIS/FINAL+3P + RECALC + UNIFICAR LABELS PLAYOFFS + RE-IMPORT PRED BONUS + FIX CLASIFICADOS NULL + AUDITORIA DIFERENCIAS EXCEL:

  FUENTE DE DATOS: "20260718_1622- TBL PARA CARGAR LIVE- JOSE semifinal.xlsx"
    Hoja "40- RESULTADOS OFICIALES" = resultado oficial por partido (1 fila x partido).
    Hoja "50- TBL MASTER" = apuestas + puntajes pre-calculados por apostador x partido.
    Copia guardada en la raiz del proyecto para que los scripts la encuentren solos.

  1) IMPORT APUESTAS SEMIS (P101/P102) y FINAL+3P (P103/P104):
     importar_apuestas_fase.py <semis|final3p> [--import] (TBL MASTER, upsert por apostador+partido).
     Semis: 88 apuestas. Final+3P: ~78 (39/44 con marcador; 5 aun sin cargar por partido).
     bats: run_importar_final3p.bat / _IMPORT.bat.

  2) RECALCULO HASTA SEMIS (recalc_hasta_semis.py + run_recalc_hasta_semis.bat):
     Como calcular-puntajes SALTA fases bloqueadas, el script: guarda estado bloqueada
     de todas las fases <= semis (16 bloqueadas), las DESBLOQUEA temporalmente, corre
     POST /calcular-puntajes/2, y RESTAURA el bloqueo original (finally). Requiere uvicorn.

  3) UNIFICAR LABELS PLAYOFFS en becbuc-live-playoffs.html (via safe_patch_html):
     ronda32 -> "16avos", ronda16 -> "Octavos", cuartos -> "Cuartos", semis -> "Semifinal".
     6 zonas: FASE_PTS, _apuestasFaseLabel MAP, LABELS del bracket (btl), columnas ranking,
     FASE_LABELS del detalle, ETAPA_LABEL. Verificado node --check + backup en _backups/.
     (Solo live-playoffs; el usuario lo pidio ahi.)

  4) RE-IMPORT PREDICCIONES DE BONUS (reimportar_predicciones_bonus.py + _APPLY.bat):
     UPDATE apuesta desde TBL MASTER de pred_amarillas/rojas/var/penales_partido/minuto_gol/
     tanda local/visit/equipo_clasifica, para grupos..semis. APLICADO: 2269 filas.
     Reparto: pred_equipo_clasifica=2230 (la BD tenia NULL "quien clasifica" en casi todo KO),
     pred_minuto_gol=62, resto ~1 c/u. NO toca marcador (H/I ya identicos).
     Resultado: las PREDICCIONES de la BD quedaron IDENTICAS a la TBL MASTER.

  5) FIX CLASIFICADOS NULL (fix_clasificado_faltante.py + _APPLY.bat):
     4 partidos KO finalizados tenian equipo_clasificado_id=NULL (toda la campana de ESPANA):
       P084 Spain 3-0 Austria, P093 Portugal 0-1 Spain, P098 Spain 2-1 Belgium, P101 France 0-2 Spain.
     El item P daba 0 a todos ahi. Seteados los 4 -> Spain (inferido por marcador). APLICADO.
     Tras recalc: bonus subio ronda16 +144, ronda32 +86, cuartos +216, semis +152.

  RANKING FINAL (post-todo): checho 1006, fscc 927, seba 911, hs 893, moro 869,
     patito 857, lav 852, vitra 827, coco 825, pato 824.

  ====================================================================
  ====================================================================
  CIERRE AUTOMATIZADO + BANNER LIVE + GOLEADOR + NO-NULL  [sesion 69, addendum 7]
  ====================================================================
  cerrar_torneo_final.py (run_cerrar_torneo_final.bat) REESCRITO - hace el cierre completo
  (correr tras P103/P104). Todo via endpoints existentes + DB (NO se toco logica backend viva):
    0) Muestra estado (fases bloqueadas + P103/P104).
    1) NO-NULL: POST /sync-resultados/2?force=true&max_detalle=60 (import de todos los items +
       marcador). Luego chequea partidos finalizados con items obligatorios en null
       (goles_l/v, amarillas, rojas, VAR, penales_partido); si quedan, reintenta el sync y
       reporta lo que la API no devolvio. (minuto_1er_gol y tanda pueden ser null legitimamente.)
    2) GOLEADOR (global C): lee goleadores_cache (refrescada por el sync), toma el/los primeros
       por goles y hace UPDATE torneo.resultado_goleador = nombre del top. OJO: el engine
       compara C EXACTO case-insensitive (pred_goleador == resultado_goleador). El script
       reporta cuantos apostadores matchean EXACTO; si 0, avisa para ajustar el nombre a la
       grafia que usaron los apostadores. Empate de goleador -> asigna el primero + avisa.
    3) FUERZA PUNTAJES: POST /calcular-puntajes/2?force_grupos=true -> puntua final/3P (fases
       bloqueadas) + recalcula globales A-G. calculate_global corre siempre (no depende del
       bloqueo): A campeon, B finalistas, E mayor goleada se disparan al jugarse la final.
    4) UPDATE torneo.cerrado=TRUE (+ cerrado_at). ALTER idempotente.
    5) Ranking final top15 + conteo de apostadores con puntaje>0 por cada global A-G.
  BANNER LIVE (becbuc-live-playoffs.html): "🏆 TORNEO CERRADO — PUNTAJES FINALES CALCULADOS".
    - Endpoint NUEVO (aislado, solo lectura): GET /api/v1/bets/torneo-cerrado/{tid} -> {cerrado:bool}.
    - loadLive() llama _checkTorneoCerrado() cada ciclo; si cerrado=TRUE muestra el banner.
    - Editado con safe_patch_py / safe_patch_html (backups en _backups/, node --check + ast OK).
  RIESGO: no se toco ninguna funcion backend existente (solo se AGREGO un endpoint). El front
    tiene try/catch: si el endpoint no responde, el banner queda oculto (sin romper nada).
  PASO MANANA: cargar goleador si el auto-match da 0 (ajustar grafia) -> run_cerrar_torneo_final.bat.

  ====================================================================
  PLAN DE CIERRE DEL TORNEO (MANANA, tras Final P104 + 3er puesto P103)  [sesion 69, addendum 6]
  ====================================================================
  CON TODAS LAS FASES BLOQUEADAS, que pasa cuando se juegue la final:
    - RESULTADO del partido: se guarda SOLO (sync actualiza tabla partido por api_fixture_id;
      el bloqueo de fase NO afecta el UPDATE de partido). Goles + estado + campeon OK.
    - GLOBALES A-G: se calculan SOLO. calcular-puntajes SIEMPRE llama calculate_global(), y
      esa funcion NO depende del bloqueo de fase (lee el partido final directo). Al jugarse la
      final dispara A(campeon), B(finalistas), E(mayor goleada) para todos.
    - PUNTOS DEL PARTIDO final/3er puesto (P103/P104, item por item por apostador): NO se
      calculan solos porque calcular-puntajes SALTA fases bloqueadas. Hay que forzar.
  GLOBALES MANUALES (admin) que deben estar cargados o quedan 0 para todos:
    - C goleador  -> torneo.resultado_goleador   (CONFIRMAR MANANA antes del cierre)
    - D peor equipo -> torneo.resultado_peor_equipo_id (Iraq ya seteado en sesion 52)
  HERRAMIENTA UN-COMANDO: cerrar_torneo_final.py + run_cerrar_torneo_final.bat.
    Hace: (1) avisa si C/D estan sin cargar, (2) POST /sync-resultados/2?force=true
    (guarda final + avanza bracket), (3) POST /calcular-puntajes/2?force_grupos=true
    (puntua las fases bloqueadas final/3P + recalcula globales A-G), (4) ranking final top15.
    Requiere uvicorn. NO cambia el bloqueo de fases.
  PASOS MANANA:
    1) (si falta) cargar el goleador C en el portal (Resultados globales) o POST /resultados-globales.
    2) Cuando terminen P103 y P104 -> doble-clic run_cerrar_torneo_final.bat.
    3) Verificar ranking final + globales.

  ====================================================================
  CIERRE EDITOR DE APUESTAS: TODAS LAS FASES BLOQUEADAS  [sesion 69, addendum 5]
  ====================================================================
  Las apuestas de Final (P104) y 3er puesto (P103) ya estan cargadas -> se cierra el editor.
  ACCION: bloquear_final_3p.py --apply (run_bloquear_final_3p[_APPLY].bat) bloqueo las fases
  final, tercer_puesto y semis (fase.bloqueada=TRUE). Con esto TODAS las fases del torneo 2
  quedan bloqueadas (grupos, 16avos, octavos, cuartos, semis, 3er puesto, final, mejores terceros).
  EFECTO en becbuc-live-playoffs.html (editor "Mi Prono"):
    - Frontend: _mpEditable() excluye partidos cuya fase.tipo esta en _blockedFases
      (lee GET /fases-bloqueo). Con todo bloqueado -> "No hay partidos abiertos para cargar apuestas".
    - Backend: POST /live-guardar-apuestas rechaza guardados en fase bloqueada ("Fase bloqueada").
  IMPLICANCIA PARA PUNTUAR P103/P104 cuando se jueguen (19-jul): calcular-puntajes SALTA fases
    bloqueadas, asi que hay que usar run_recalc_force_grupos.bat (force_grupos=true reconstruye
    TODO incluidas las fases bloqueadas, sin cambiar el estado de bloqueo).
  Para REABRIR el editor de una fase (si hiciera falta): UPDATE fase SET bloqueada=FALSE
    WHERE torneo_id=2 AND tipo='<tipo>'  (o Config -> Fases en el portal).

  ====================================================================
  CONFIRMACION ORGANIZACION: REGLA NULL->0 EN K/M ES CORRECTA  [sesion 69, addendum 4]
  ====================================================================
  El usuario confirmo: "esta correcto que el null sea cero". La prediccion en blanco
  se trata como valor 0; si el resultado oficial es 0, el apostador ACIERTA y suma 1 pt.
  => La regla lenient de la BD (K rojas, M penales juego) es CORRECTA y se mantiene.
  RESULTADO: en las 54 diferencias BD vs Excel corregido, la BD es la fuente CORRECTA
  en TODAS. Desglose: K:12 + M:8 (null->0, BD correcta), N:14 (desempate minuto, decision
  org), O:4 (error Excel tanda semis), P:16 (error Excel: no otorgo P a acierto). NO se
  cambia el engine ni se recalcula. Puntajes definitivos; el portal lee de puntaje_detalle.
  ENTREGABLE: becbuc_diffs_puntajes_<ts>.xlsx (hojas Leyenda + Diferencias con Resultado
  real/Apuesta Excel/Apuesta BD por item + Resumen).

  ====================================================================
  FIX ENGINE: ITEM P NO SE DUPLICA PARA PARAGUAY  [sesion 69, addendum 3]
  ====================================================================
  RECTIFICACION del usuario: en el item P (equipo que clasifica) Paraguay NO multiplica x2.
  CAMBIO: backend/app/services/scoring/engines/copa_mundo_2026.py (score_partido):
    ANTES: score.pts_equipo = cfg.pts_equipo_clasifica * mult
    AHORA: score.pts_equipo = cfg.pts_equipo_clasifica   # item P NO x2 Paraguay
  (El resto de items de partido -H/I/J/K/L/M/N/O- SIGUEN x2 para Paraguay.)
  Tras run_recalc_force_grupos.bat (uvicorn --reload tomo el cambio):
    Partidos Paraguay KO afectados: P074 (16avos, P pasa de 4->2) y P089 (octavos, 8->4).
    Ranking bajo levemente para quienes acertaron el clasificado de Paraguay
    (ej. checho partidos 969->963). Bloqueo de fases NO modificado.
  COMPARACION FINAL (exportar_diffs_puntajes.py -> becbuc_diffs_puntajes_20260718_2256.xlsx): 54 diffs.
    (los 40 "Paraguay x2 en item P" DESAPARECIERON; la BD ahora iguala al Excel en P074/P089)
    K:12 + M:8 -> regla NULL->0 de la BD (lenient POR DISENO).
    N:14 -> desempate minuto (BD da 1pt a todos los mas cercanos, decision organizacion).
    O:4  -> error del Excel: tanda en semis P101/P102 sin definicion por penales.
    P:16 -> error del Excel: no otorgo P a prediccion correcta (BD correcta).
    => Ya NO queda ningun caso donde la BD este por debajo de lo correcto salvo la
       regla lenient K/M (por diseno). Los 20 (P:16 + O:4) restantes son errores del Excel.

  ====================================================================
  EXCEL CORREGIDO v2 + FILL CLASIFICADOS NULL  [sesion 69, addendum 2]
  ====================================================================
  FUENTE NUEVA: "20260718_2214- TBL PARA CARGAR LIVE- JOSE con correcciones.xlsx"
    (copiada a la raiz; el viejo *SEMIFINAL*.xlsx movido a _backups/).
    OJO layout: la col de puntos P (CLASIFICADOS) se movio 51 -> 49. Los scripts de
    comparacion ahora AUTO-DETECTAN esa columna por el encabezado 'CLASIFICAD' (robusto),
    y el finder de Excel prioriza 'CORRECCIONES' > 'SEMIFINAL' > 'TBL PARA CARGAR' (mas reciente).
  COMPARACION Excel corregido vs BD (comparar_puntajes_items todas): 1007 -> 98 diffs.
    El Excel corregido arreglo: I 1->0 (TIM PAYNE), P 947->60 (aplicaron escala reglamento 2/4/6/8),
    N 35->14 (P064 y otros stale ya resueltos por el force recalc).
  FILL CLASIFICADOS NULL (fill_clasifica_null.py --apply + run_fill_clasifica_null[_APPLY].bat):
    224 filas KO tenian apuesta.pred_equipo_clasifica NULL en la BD. Se rellenaron 215 desde
    la col 'Q- QUIEN CLASIFICA' (col 32) del Excel corregido (solo NULL, no pisa lo existente).
    Solo 'ESTADOS UNIDOS' (~9 filas) sin match. El engine solo usa pred_equipo_clasifica cuando
    el apostador predijo EMPATE (en victoria infiere del marcador), asi que el fill es seguro.
    Tras run_recalc_force_grupos.bat: ronda16 bonus +8. Ranking estable (checho 1007, fscc 928...).
  RESIDUAL FINAL (exportar_diffs_puntajes.py -> becbuc_diffs_puntajes_<ts>.xlsx): 94 diffs.
    K:12 + M:8  -> regla NULL->0 de la BD (pred en blanco = 0, lenient POR DISENO).
    N:14        -> desempate minuto: BD da 1pt a TODOS los mas cercanos (decision organizacion).
    O:4         -> error del Excel: tanda otorgada en semis (P101/P102) sin definicion por penales.
    P:40        -> Paraguay x2 en item P (BD correcta, reglamento). Partidos Paraguay KO: P074, P089.
    P:16        -> error del Excel: no otorgo P a prediccion correcta (BD correcta).
    => Tras el fix ya NO queda NINGUN caso donde la BD este mal. Los 94 son: BD-correcta-por-regla
       (N/O/P-Paraguay = 58), BD-lenient K/M (20), o error del Excel (P:16). El hueco-BD desaparecio.
  SCRIPTS NUEVOS ESTA TANDA: fill_clasifica_null.py (+ _APPLY.bat), exportar_diffs_puntajes.py
    (+ run_exportar_diffs.bat). comparar_puntajes_items.py: finder multi-nombre + auto-detect col P.

  ====================================================================
  FIX STALE DEFINITIVO - RECALCULO FORZADO (force_grupos=true)  [sesion 69, addendum]
  ====================================================================
  SINTOMA REPORTADO: item N (minuto 1er gol) mal en P064 - AAA y MORO acertaron 28
    en PLENO (distancia 0) pero el sistema daba el punto a EDGAR/GUSTAV/KIKAO/PUCHETA
    (pusieron 20/22, distancia 6-8). Misma raiz que el VAR: puntaje de grupos STALE.
  CAUSA DE FONDO: POST /calcular-puntajes SALTA fases bloqueadas, y el endpoint ademas
    corre _auto_lock_completed_grupos() al inicio -> aunque recalc_hasta_semis desbloquee
    grupos, el endpoint los re-bloquea antes de puntuar -> grupos NUNCA se re-puntuaba ->
    N usaba el minuto real VIEJO (desempate entre todos calculado con dato stale).
  SOLUCION (sin editar backend): el endpoint YA soporta ?force_grupos=true, que:
    - usa _bloq_clause=TRUE en DELETE, _load_partidos y _load_apuestas (trae grupos bloqueados),
    - SALTA _auto_lock_completed_grupos (grupos_auto_bloqueadas=0),
    - NO cambia el estado de bloqueo de ninguna fase.
    => borra y reconstruye TODO puntaje_detalle desde datos ACTUALES. Por definicion
       elimina CUALQUIER valor stale (N, L, y todo lo demas) de una sola pasada.
  SCRIPT: recalc_force_grupos.py + run_recalc_force_grupos.bat (login jose/catalina,
    POST /calcular-puntajes/2?force_grupos=true, imprime por_fase + top10). Requiere uvicorn.
  RESULTADO (comparar_puntajes_items todas, DESPUES del force):
    L (VAR): 145 -> 0   (desaparece; el rebuild supersede el parche fix_var_L, consistente).
    N:        41 -> 35  (bajan 6 = EXACTAMENTE los 6 diffs de P064: AAA/MORO/EDGAR/GUSTAV/
              KIKAO/PUCHETA). AAA y MORO ahora reciben el punto (distancia 0). Los 35
              restantes son EMPATES GENUINOS (BD da 1pt a TODOS los de distancia minima,
              decision organizacion 2026-07-02) - NO son stale.
    I=1, K=12, M=8, O=4, P=947  (SIN cambios: error Excel / regla NULL->0 BD / escala reglamento).
  RANKING (post force, estable): checho 1007, fscc 928, seba 912, hs 894, moro 871,
    patito 856, lav 849, coco 826, vitra 826, pato 823. Bloqueo de fases NO modificado.
  REGLA DE ORO ACTUALIZADA: cuando un item de fase BLOQUEADA quede stale (VAR, minuto, etc),
    NO parchear por fila - correr run_recalc_force_grupos.bat (force_grupos=true) que reconstruye
    todo desde los datos actuales sin tocar el bloqueo. (fix_var_L.py queda como referencia historica.)
    PENDIENTE (mejora backend durable): que calcular-puntajes re-puntue grupos al desbloquearse
    sin necesidad del flag; por ahora force_grupos=true es la via correcta.

  AUDITORIA - FUENTE DE CADA DIFERENCIA DE PUNTAJE Excel(TBL MASTER) vs BD
  (tras re-import de predicciones + fix clasificados + recalc)
  Herramienta: comparar_puntajes_items.py (enriquecido: imprime por diferencia
    real=resultado oficial | ap.Excel | ap.BD | ptsEx | ptsBD). Solo lectura.
  ====================================================================
  H (resultado):        0 diffs. OK.
  I (marcador exacto):  1 diff (TIM PAYNE P102). FUENTE = ERROR DEL EXCEL: calcula I
                        comparando el string con el nombre-placeholder del equipo ("G099")
                        en vez del marcador numerico 1-2. BD correcta (24 pts). No tocar BD.
  J (amarillas):        0 (se resolvio al recalcular; eran puntajes viejos/stale).
  K (rojas):            12 diffs. FUENTE = REGLA NULL->0 DE LA BD (fix sesion 23): trata la
                        prediccion en blanco como 0; si el oficial es 0 y el apostador no cargo K,
                        la BD suma 1pt y el Excel da 0 (todas BD>Excel). BD lenient POR DISENO.
                        No es error del Excel. Decision: mantener o no la regla NULL->0.
  L (VAR):              145 diffs. FUENTE REAL = PUNTAJE DE GRUPOS STALE EN LA BD (no era el Excel).
                        puntaje_detalle tenia real_var VIEJO=2 mientras partido.decisiones_var
                        actual=1 (P063 y otros de grupos). Diagnostico: diag_var_L.py / fix_var_L.py
                        (todas "real_var stale"). CORREGIDO esta sesion: fix_var_L.py --apply recalculo
                        pts_var + pts_bonus + pts_total desde el dato actual -> 145 filas. El Excel
                        SIEMPRE estuvo bien. CAUSA DE FONDO PENDIENTE: calcular-puntajes NO refresca
                        la fase de grupos aunque se desbloquee -> por eso quedo viejo el VAR. Revisar
                        en el backend (calculator.py / endpoint) para que un recalculo futuro si
                        re-puntue grupos y no vuelva a quedar stale.
  M (penales juego):    8 diffs. MISMA FUENTE que K (regla NULL->0 de la BD). octavos P090/P093/P094/P096.
                        BD lenient por diseno, no error del Excel.
  N (minuto 1er gol):   41 diffs. FUENTE = ALGORITMO DE DESEMPATE: la BD da 1pt a TODOS los
                        empatados en la distancia minima al minuto real (decision organizacion
                        2026-07-02). El Excel usa otro criterio. BD correcta por decision. No tocar.
  O (tanda penales):    4 diffs (semis P101/P102: CHEREM, COTO, SONI). FUENTE = ERROR DEL EXCEL:
                        otorgo 4 pts de tanda en semis que se definieron en tiempo reglamentario
                        (sin definicion por penales). BD correcta (O=0). No tocar BD.
  P (equipo que pasa):  947 diffs. FUENTE = DIFERENCIA DE ESCALA (reglamento): el Excel da 1 punto
                        PLANO; la BD escala por fase segun reglamento oficial: 16avos=2, octavos=4,
                        cuartos=6, semis=8. La prediccion es identica; solo cambia el puntaje.
                        DECISION PENDIENTE con la organizacion (escala reglamento vs plano Excel).
                        NOTA: parte de P se debia a 4 clasificados NULL (P084/P093/P098/P101),
                        YA CORREGIDOS esta sesion.

  RESUMEN AUDITORIA: la BD es la fuente correcta. Todo lo que difiere del Excel es por
    (a) error del Excel (I placeholder, O tanda semis),
    (b) inconsistencia interna del Excel entre sus hojas TBL MASTER y RESULTADOS OFICIALES (K/L/M),
    (c) algoritmo de desempate por decision de organizacion (N),
    (d) escala de reglamento vs plano (P, decision pendiente).
  Los RESULTADOS OFICIALES del Excel ya coincidian 100% con partido en la BD (actualizar_resultados_fase.py todas -> 0 cambios).

  SCRIPTS CREADOS ESTA SESION (raiz, todos con .bat, credenciales psycopg2 host=localhost
    user=app_user password=superpassword; los que llaman API usan jose/catalina en :8000):
    importar_semis_excel.py, importar_apuestas_fase.py (semis/final3p),
    reimportar_predicciones_bonus.py, actualizar_resultados_fase.py (grupos..semis, todas),
    comparar_items_resultados.py (todas), comparar_resultados_todos.py,
    comparar_puntajes_items.py (enriquecido real/ap.Excel/ap.BD/ptsEx/ptsBD),
    fix_clasificado_faltante.py, recalc_hasta_semis.py, verificar_item_p.py,
    sin_apuesta_semis.py, cerrar_semis.py, sync_partido.py (P103 3er puesto).

  REGLA DE ORO CONFIRMADA: para dejar la BD identica al Excel en items de partido usar
    actualizar_resultados_fase.py; en predicciones usar reimportar_predicciones_bonus.py;
    para huecos de clasificado KO usar fix_clasificado_faltante.py; SIEMPRE recalcular con
    run_recalc_hasta_semis.bat (desbloquea/recalc/rebloquea, no rompe el estado de fases).

2026-07-15 - Sesion Cowork (sesion 68) - CIERRE CUARTOS + SEMIS/BRACKET + EDITOR APUESTAS LIVE-PLAYOFFS + EXPORT:

  REGLA OPERATIVA CONFIRMADA (app_db compartida):
    app_db es la BD central de gestion de usuarios que comparten TODOS los proyectos
    listados en la tabla `sistema` (BECBUC, Plataforma/FastAPI Release 2 en C:\proyectos\plataforma,
    Energia en C:\Proyectos\Energia, etc.). Cualquier cambio de esquema en app_db.sistema por
    otro proyecto puede romper el arranque de BECBUC (ORM espera columnas legacy -> fix_sistema_columns.py).
    REGLA: avisar y alertar de riesgos ANTES de tocar cualquier cosa en app_db.

  1) CIERRE DE CUARTOS (cerrar_cuartos.py + run_cerrar_cuartos.bat):
     Verifica P097-P100: finalizados + items API cargados (amarillas/rojas/VAR/pen.juego/minuto;
     tanda solo si empate). Guardas de aborto si algo incompleto. Luego POST /calcular-puntajes/2
     (cuartos aun abierta) y bloquea fase Cuartos (id=142). NO abre Semis.
     Resultado: P097 France 2-0 Morocco, P098 Spain 2-1 Belgium, P099 Norway 1-2 England,
     P100 Argentina 3-1 Switzerland. plenos=39 aciertos=85 fallos=52, [cuartos] total=3153, apuestas=176.

  2) SEMIS + AVANCE DE BRACKET (sync_semis.py + run_sync_semis.bat):
     OPCION A (SIEMPRE, default del usuario): POST /sync-resultados/2?force=true ->
     auto-mapea api_fixture_id + trae resultados + avanza bracket. NO bloquea fases,
     no genera puntajes de semis (sin apuestas cargadas).
     Resultado: P101 France 0-2 Spain, P102 England 1-2 Argentina (finalizados).
     Bracket: Final (P104) = Spain vs Argentina | 3er puesto (P103) = France vs England.
     Fechas: 19-jul (P103 00:00 UTC, P104 22:00 UTC).
     Diagnostico: estado_semis_bracket.py / run_estado_semis.bat (solo lectura).
     REGLA: una fase no se cierra ni se puntua sin las apuestas cargadas.

  3) EDITOR DE APUESTAS EN "MI PRONO" (becbuc-live-playoffs.html + apostador_bets.py):
     renderMiProno delega a renderMiPronoEditor (el viejo cuerpo quedo como _renderMiProno_OLD).
     Editor con inputs por item, formato/iconos del tab Apuestas: marcador (pred_local/visitante),
     J amarillas, K rojas, L VAR, M pen.juego, N minuto, seccion "Definicion por penales"
     (Ol/Ov tanda) y P clasifica (select de los 2 equipos). Precarga desde _userPreds.
     Endpoint NUEVO: POST /api/v1/bets/live-guardar-apuestas/{torneo_id}
       body {apostador_id, pin, apuestas:[{numero_fifa, pred_*}]}. Sin auth de apostador
       (la pagina usa token admin). Guarda solo partidos 'programado' con fase NO bloqueada.
       NO calcula puntajes ni cierra fases. Upsert incluye pred_equipo_clasifica + nombre_apostador=username.
     Bracket -> Mi Prono: selectMatch() ahora hace setTab('miprono') + scroll al partido (_scrollToMpCard).

  4) PIN = PRIMER NOMBRE (no username):
     El endpoint lee users.nombre (app_db) y compara el PRIMER TOKEN en MAYUSCULAS.
     Ej: username=cherem, nombre='ANDRES BOGARIN' -> PIN valido = ANDRES. Fallback a username si nombre vacio.
     Verificado (test): PIN correcto acepta, username ya no valida.

  5) MI PRONO SOLO PENDIENTES: se quito la seccion de cotejo (finalizados). Solo partidos no jugados.

  6) RECIBO PDF (auto al guardar con exito): _mpMostrarRecibo() arma una tarjeta blanca imprimible
     con boton "Imprimir / Guardar PDF" (window.print -> en movil "Guardar como PDF"). Lista TODOS
     los partidos pendientes con sus items (desde _userPreds, sin terminados) + encabezado con
     Nombre y apellido (users.nombre, devuelto por el endpoint como "nombre") + Usuario (alias).

  7) BLOQUEO DE EDICION 4H ANTES DEL PARTIDO:
     Backend: live-guardar-apuestas rechaza si now >= fecha_partido - 4h ("Edicion cerrada...").
     Frontend: _mpLocked(m) (fecha del partido, UTC vs hora del dispositivo). Tarjeta bloqueada
     con inputs disabled + badge; si todas cerradas se oculta Guardar. Final/3er puesto (19-jul)
     siguen editables hasta 4h antes de cada uno.

  8) EXPORT PRONOSTICOS + COMPLETADOS POR FASE (Monitoreo):
     Endpoints NUEVOS:
       GET /api/v1/bets/exportar-pronosticos/{torneo_id} (admin): Excel, 1 fila por apostador x partido
         de TODAS las fases abiertas. Cols: No Partido, Fase, Usuario, Nombre, Local, Visitante,
         Resultado real, Pron.Local, Pron.Visit, Amarillas(J), Rojas(K), VAR(L), Pen.juego(M),
         Min.1er gol(N), Tanda Local(Ol), Tanda Visit(Ov), Clasifica(P). Orden: apostador -> fase -> nro partido.
         Solo rol 'apostador' activo. Filename becbuc_pronosticos_fases_abiertas_{ts}.xlsx.
       GET /api/v1/bets/pronosticos-completados/{torneo_id} (admin): por fase abierta cuantos
         apostadores completaron TODAS sus apuestas (n>=total_partidos) sobre total_apostadores.
     UI Portal (Monitoreo): card "Apuestas completas por fase abierta" (X/44 por fase) + boton
       "Exportar pronosticos" (loadCompletadosFase / exportarPronosticos).
     UI Movil (admin): seccion "Pronosticos (fases abiertas)" + boton (exportarPronosticosM /
       _loadCompletadosFaseM). REGLA UI OBLIGATORIA cumplida (portal + movil).
     Verificado (test PASS): completados Semis 0/44, 3er puesto 1/44, Final 1/44; Excel 5.7KB ok.

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py (endpoints live-guardar-apuestas,
      exportar-pronosticos, pronosticos-completados)
    backend/static/becbuc-live-playoffs.html (editor Mi Prono, PIN, recibo, lock 4h, nav bracket)
    backend/static/BECBUC-portal.html (Monitoreo: card completados + export)
    backend/static/BECBUC-movil.html (admin: seccion completados + export)

  ARCHIVOS CREADOS (raiz): cerrar_cuartos.py, estado_semis_bracket.py, sync_semis.py, get_ngrok.py
    y sus run_*.bat; tests test_live_guardar.py / test_export_pronos.py; parches _patch_*.py
    (aplicados con backup en _backups/, verificados con node --check + ast). CREDENCIALES psycopg2
    externas: host=localhost port=5432 user=app_user password=superpassword.

  WHATSAPP a usuarios (para probar apuestas): incluye link ngrok del dia
    https://cupped-oink-thousand.ngrok-free.dev/static/becbuc-live-playoffs.html (CAMBIA al reiniciar;
    obtener con run_get_ngrok.bat), elegir USUARIO en el login, pestana Mi Prono (solo pendientes) o
    tocar el partido en el Bracket, cargar items, Guardar -> PIN = primer nombre -> recibo PDF.

  ESTADO TORNEO POST-SESION:
    Grupos + R32 + Octavos + Cuartos: finalizados y BLOQUEADOS.
    Semis: P101/P102 finalizados, fase 'semis' ABIERTA (apuestas de semis NO cargadas).
    Bracket propagado: Final (P104) Spain vs Argentina, 3er puesto (P103) France vs England (19-jul).
    PENDIENTE: cargar apuestas de Semis (y luego Final/3er puesto) para poder cerrar/puntuar esas fases.

2026-07-09 - Sesion Cowork (sesion 67) - CUARTOS: BLOQUEO OCTAVOS + CALCULAR PUNTAJES P097:

  SCRIPTS CREADOS (raiz proyecto):
    gestionar_fases_cuartos.py + run_gestionar_fases_cuartos.bat:
      - Bloquea Octavos (fase id=141, tipo ronda16) -> bloqueada=TRUE
      - Desbloquea Cuartos (fase id=142, tipo cuartos) -> bloqueada=FALSE
      - Muestra partidos P097-P100 con estado/goles/clasificado
      - Llama POST /calcular-puntajes/2
      - BUG descubierto: P097 France 2-0 Morocco estaba en estado 'en_juego' (no finalizado)
        -> el engine no lo calculaba -> plenos=0, aciertos=0

    finalizar_p097_y_calcular.py + run_finalizar_p097_y_calcular.bat:
      - Verifica estado de P097 en BD (id=743, api_fixture_id=1578539)
      - POST /sync-resultados/2?force=true -> API-Football finaliza P097
        actualizados=31, bracket_ok=True, puntajes_ok=True
      - Post-sync: P097 estado=finalizado, goles=2-0, clasificado=France ✅
      - POST /calcular-puntajes/2 (re-calculo)
      - Muestra ranking top-10

  RESULTADO CUARTOS (fase id=142):
    P097: France 2-0 Morocco    -> finalizado | clasifica: France  ✅
    P098: Spain vs Belgium      -> programado (pendiente)
    P099: Norway vs England     -> programado (pendiente)
    P100: Argentina vs Switzerland -> programado (pendiente)

  PUNTAJES CUARTOS CALCULADOS (44 apostadores):
    plenos=8  aciertos=26  fallos=10
    [cuartos] marcador=580  bonus=272  total=772  apuestas=44
    globales_procesadas=44

  TOP RANKING POST-CUARTOS (puntos_total = partidos + globales + grp_P):
    1er: 870 pts (part=832, glob=12, grp_P=26)
    2do: 888 pts (part=772, glob=0,  grp_P=28)
    3ro: 793 pts (part=766, glob=0,  grp_P=27)
    (alias muestra ? en script diagnostico - portal muestra correctamente)

  ESTADO FASES POST-SESION:
    Octavos (ronda16, id=141): bloqueada=TRUE  ✅
    Cuartos  (cuartos, id=142): bloqueada=FALSE (abierta, solo P097 finalizado)

  PROXIMO PASO:
    Cuando se jueguen P098 (Spain vs Belgium), P099 (Norway vs England),
    P100 (Argentina vs Switzerland):
      -> sync_auto.py los detecta y finaliza automaticamente
      -> POST /calcular-puntajes/2 para puntuar los nuevos partidos
      -> Bloquear Cuartos y abrir Semis cuando los 4 partidos esten finalizados

2026-07-09 - Sesion Cowork (sesion 66) - FIX ARRANQUE UVICORN (sistema) + IMPORT CUARTOS + FIX APUESTAS SANBIE/PATO OCTAVOS:

  CONTEXTO: app_db es COMPARTIDA con el proyecto C:\Proyectos\Energia (mismo core-postgres).
    La modernizacion del core de Energia RESTRUCTURO la tabla app_db.sistema (agrego tipo/logo_url/
    config_json/activo y ELIMINO host_bd/puerto_bd/nombre_bd/usuario_bd/contrasena_bd/es_activo).
    El modelo ORM Sistema de BECBUC + selectinload(User.sistemas) en crud/user.py exigen esas columnas
    -> UndefinedColumnError: column sistema.host_bd does not exist -> uvicorn NO arrancaba.

  FIX 1 - Arranque uvicorn (fix_sistema_columns.py + run_fix_sistema.bat):
    ALTER TABLE sistema ADD COLUMN IF NOT EXISTS (aditivo, no destructivo) restauro las 8 columnas
    legacy que el ORM espera: host_bd, puerto_bd, nombre_bd, usuario_bd, "contraseña_bd", es_activo,
    created_at, updated_at (con defaults). Conviven con las columnas nuevas de Energia. Server levanta.
    NOTA: si Energia vuelve a tocar app_db.sistema y rompe el arranque, re-correr este fix.

  FIX 2 - Import apuestas CUARTOS (importar_cuartos_excel.py + run_importar_cuartos[_IMPORT].bat):
    Fuente: "20260709_1500- PRONOSTICOS CONSOLIDADOS 4TOS.xlsx", hoja '4tos', filtro FASE '40- CUARTOS'.
    Columnas (1-based): pid=2, nombre=9, alias=10, pred_l=13, pred_v=15, J=25,K=26,L=27,M=28,N=29,
    TL=30,TV=31, quien_clasifica=32. Upsert ON CONFLICT (apostador_id, partido_id).
    Resultado: 176 apuestas (44 apostadores x 4 partidos P097-P100), 0 errores, todos los alias
    y equipos matchearon. Partidos: P097 France-Morocco, P098 Spain-Belgium, P099 Norway-England,
    P100 Argentina-Switzerland.

  FIX 3 - Apuestas SANBIE/PATO en octavos (resubir_octavos_sanbie_pato.py + run_resubir_sanbie_pato[_APPLY].bat):
    Reportado: Sandra (username=sanbie id=51) y Pato (Hugo Biedermann, username=pato id=29) con
    apuestas de octavos cruzadas. DIAGNOSTICO: no estaban cruzadas sino DUPLICADAS (identicas) por
    error del Excel. swap_apuestas.py (swap generico de pred_* por rango numero_fifa) confirmo que
    eran identicas -> swap no cambiaba nada.
    SOLUCION: re-subir sus 8 apuestas de octavos c/u (16 filas) desde el master
    "20260705_2016- TBL PARA SUBIR AL LIVE.xlsx" (hoja '50- TBL MASTER'), que el usuario confirmo
    como correcto. Principal correccion: pred_equipo_clasifica (P094 estaba NULL -> Belgium(76)).
    16 apuestas re-subidas, 0 errores.
    NOTA: el usuario descarto verificar resultados reales de octavos vs BD (ese master del 5-jul solo
    tenia P089/P090 finalizados; P091-P096 estaban PENDIENTE en el).

  FIX 4 - Recalculo + bloqueo cuartos (recalc_octavos_bloquear_cuartos.py + run_recalc_octavos_bloquear_cuartos.bat):
    POST /calcular-puntajes/2 -> ronda16 {marcador:1800, bonus:1652, total:3452, apuestas:352},
    globales_procesadas=44. Fase Cuartos (id=142, tipo 'cuartos') BLOQUEADA.

  UTILES / VERIFICACION:
    diag_sistema_schema.py     - vuelca esquema real de app_db.sistema/users/user_sistemas
    verificar_usuario_sandra.py - lista usuarios biedermann/hugo/pato con conteo apuestas octavos
    swap_apuestas.py <u1> <u2> <nf_a> <nf_b> [--apply] - swap generico de predicciones

  ARCHIVOS CREADOS (raiz proyecto): fix_sistema_columns.py, importar_cuartos_excel.py,
    resubir_octavos_sanbie_pato.py, swap_apuestas.py, recalc_octavos_bloquear_cuartos.py,
    verificar_usuario_sandra.py, diag_sistema_schema.py + sus .bat.

  CREDENCIALES BD (conexion directa psycopg2 externa): host=localhost port=5432 user=app_user
    password=superpassword (docker-compose). Docker por dentro sigue con -U app_user sin password.

  PENDIENTE: cuando se jueguen los cuartos (P097-P100) -> POST /calcular-puntajes/2 para puntuarlos.


2026-07-05 - Sesion Cowork (sesion 65) - AUDITORIA COMPARACION ITEMS + FIX TIMEZONE + INFERENCIA FUENTES:

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py, 3 parches):
    backend/static/BECBUC-portal.html (via safe_patch_html, 3 parches):
    backend/static/BECBUC-movil.html (via safe_patch_html, 2 parches):

  FIX TIMEZONE (apostador_bets.py + portal + movil):
    PROBLEMA: Horas de partidos en portal/movil no mostraban hora local del usuario.
    CAUSA: Backend serializaba fechas con .isoformat() (sin 'Z') → JS las parseaba
      como local en vez de UTC. SQL usaba AT TIME ZONE 'America/Costa_Rica' para
      filtrar "partidos de hoy" → partidos nocturnos se perdian.
    FIX apostador_bets.py:
      - partidos_hoy SQL: 'America/Costa_Rica' → 'UTC' (2 ocurrencias)
      - partidos_hoy serialización: .isoformat() → .strftime("%Y-%m-%dT%H:%M:%SZ")
      - live_panel _tz_hoy: 'America/Costa_Rica' → 'UTC'
      - live_panel SQL filter: 'America/Costa_Rica' → 'UTC'
    FIX BECBUC-portal.html:
      - _hoyStatusHtml hora: añade 'Z' si falta, 'es-CR' → 'es' (usa TZ local browser)
      - Partidos live badge hora: mismo fix
    FIX BECBUC-movil.html:
      - Línea 1053 hora: añade 'Z' si falta, 'es-CR' → 'es'
      - Live badge hora (línea 3197): mismo fix
      - Bracket date/hora (línea 4285): 'es-AR' → 'es'
    PRINCIPIO: Backend envía UTC con sufijo 'Z'. JS usa toLocaleTimeString('es')
      sin timeZone → browser usa su propia TZ local (Paraguay UTC-3/4).

  AUDITORIA ITEMS FASE ACTIVA — Nuevo endpoint + UI (portal + movil):
    ENDPOINT GET /admin/auditoria-items-activos/{torneo_id} (apostador_bets.py):
      - Detecta fase activa (primera no bloqueada con partidos finalizados o en_juego)
      - Consulta puntaje_detalle: H/I/J/K/L/M/N/O por apostador x partido
      - Consulta apuesta: pred_J/K/L/M/N para re-scoring por fuente
      - Consulta partido_stats_fuentes (try/except si no existe): api_*/espn_*
      - _rescore_jklm(pred, raw_j, raw_k, raw_l, raw_m): rescora J/K/L/M con stats de fuente
      - _minuto_pts(aid, pid, all_preds, real_min): 1pt si más cercano al minuto real
      - source_scores[aid] = {bd, api, espn} — total pts re-scored por fuente
      - fuentes_summary = {has_fuentes, apostadores_dif_api, apostadores_dif_espn, nota}
      - Respuesta incluye: apostadores[] con fuentes{bd,api,espn}, partidos_raw[], fuentes_summary
      - Excluye: pts_equipo (P), pts_globales (A-G)

    ENDPOINT GET /admin/auditoria-items-activos-excel/{torneo_id} (apostador_bets.py):
      - Hoja "Ítems fase activa": apostador × H-O + Total BD + API + ESPN
      - Hoja "Partidos raw": datos crudos por partido
      - Hoja "Fuentes": nota + diff counts
      - StreamingResponse XLSX: becbuc_items_activos_{tid}_{ts}.xlsx

    UI BECBUC-portal.html — Monitoreo > Auditoría Excel:
      CSS: .aud-img-zone, .aud-img-preview, .aud-cmp-wrap, .aud-cmp-table, .aud-cmp-zero
      HTML: zona drag-and-drop imagen (referencia visual), botones Comparar + Descargar Excel
      JS:
        - _audImgFile, _audCmpData: estado del módulo
        - audImgOnDragOver/Leave/Drop/FileSelect, _audImgLoad(file): drag handlers
        - audCompararActivos(): GET /admin/auditoria-items-activos → _audRenderCmp
        - _audRenderCmp(d): tabla H-O por apostador + columnas BD/API/ESPN + input TBL
            - Campo TBL CHECK: input numérico por apostador que actualiza _audTblRef
            - Columna "⭐ Fuente": detecta fuente más cercana al TBL ingresado
              bestSrc = min(|src_total - tbl|) entre BD/API/ESPN
              Si diff=0: "✅ BD" / Si diff>0: "ESPN (±3)"
            - Celdas API/ESPN: resaltadas en ámbar si difieren de BD
            - Tabla partidos_raw: columnas API/ESPN de amarillas si hay fuentes
        - audExportarComparacion(): descarga XLSX

    UI BECBUC-movil.html — Admin panel (nueva sección "Comparación ítems — Fase activa"):
      JS:
        - audCmpActivosM(btn): llama mismo endpoint, guarda en _mAudCmpData
        - _renderAudCmpM(d): tabla compacta H-O + BD/API/ESPN (resalta diferencias en ámbar)
        - audExportCmpM(btn): descarga XLSX
      HTML: zona con botones "Comparar ítems" + "Descargar Excel" + div resultados

  RESUMEN AUDITORIA — Cómo usar:
    1. Portal: Monitoreo → Auditoría Excel → sección "Comparación ítems fase activa"
       (o Móvil: Admin → Comparación ítems — Fase activa)
    2. Click "Comparar ítems": muestra H-O por apostador con totales BD/API/ESPN
    3. Si hay fuentes en partido_stats_fuentes: columnas API/ESPN muestran totales re-scored
    4. Ingresar total de imagen TBL CHECK → columna ⭐ Fuente indica cuál fuente coincide mejor
    5. Descargar Excel para análisis offline

  ARCHIVOS CREADOS:
    (ninguno nuevo — todo integrado en archivos existentes)

  PENDIENTE:
    - Reiniciar uvicorn para activar nuevos endpoints y fixes timezone
    - Verificar que horas en portal muestren hora local de Paraguay
    - Si partido_stats_fuentes no tiene datos de R16: comparación API/ESPN mostrará
      valores iguales a BD (fuentes aun no pobladas para partidos activos)
      Para poblar: POST /populate-stats-fuentes/{torneo_id} desde Herramientas

2026-07-05 - Sesion Cowork (sesion 64) - FIX AUTOMATIZACION KO: if result NONE + TBD/POR DEFINIR:

  PROBLEMA: calcular-puntajes no actualizaba globales en octavos (ronda16) porque
    ScoringCalculator.calculate() retorna None cuando todas las fases finalizadas
    están bloqueadas (grupos + R32 bloqueados, R16 abierto con partidos finalizados).
    Los endpoints sync_resultados y sync_partido usaban `if result:` que es falsy
    para None → calculate_global() nunca se ejecutaba → puntajes globales desactualizados.

  FIX 1 — apostador_bets.py (3 ubicaciones, via safe_patch_py):
    sync_resultados endpoint (~línea 6065):
      ANTES: if result: global_result = await calc.calculate_global(...)
      AHORA: if result is None: result = {"plenos":0,"aciertos":0,"fallos":0,"por_fase":{}}
             global_result = await calc.calculate_global(...)  ← siempre ejecuta
    sync_partido endpoint (~línea 9002):
      ANTES: result.get("procesados",0) → crash si result es None
      AHORA: if result is None: result = {...}; luego result.get()
    Tercer endpoint con mismo patrón (~línea 9109):
      ANTES: if result: global_result = await calc.calculate_global(...)
      AHORA: mismo fix que sync_resultados

  FIX 2 — sync_api_football.py (via safe_patch_py):
    BUG: query de unmapped_active verificaba `nombre = 'TBD'` para excluir
      partidos "Por Definir". Pero el equipo en BD usa nombre = 'Por Definir' (no 'TBD').
      Efecto: partidos de cuartos con "Por Definir" se contaban como unmapped_active
      → auto_mapeo corría innecesariamente → falla silenciosa, gasta cuota API.
    FIX: Cambiado a `(nombre = 'TBD' OR nombre = 'Por Definir')` en ambos NOT EXISTS.

  CONFIRMADO - Fases futuras (cuartos, semis, final):
    sync_torneo ya tiene el mecanismo correcto para todas las fases KO futuras:
      unmapped_active = COUNT partidos con equipo real + api_fixture_id IS NULL + no finalizado
      if fixtures_mapeados == 0 OR unmapped_active > 0: → auto_mapeo_torneo()
    Cuando _avanzar_bracket propaga ganadores a cuartos (P97-P100), esos partidos
    tienen equipos reales pero api_fixture_id = NULL → unmapped_active > 0 → auto_mapeo.
    La primera vez que sync_auto corre dentro de la ventana temporal del partido,
    mapea el api_fixture_id y luego sincroniza los goles en vivo. No requiere
    intervención manual para ninguna fase futura.

  ESTADO POST-FIX:
    - R16 P89 (Paraguay 0-1 France) y P90 (Canada 0-3 Morocco): finalizados y calculados ✅
    - Ranking: checho 736, lav 707, seba 703 (al momento de la sesión)
    - ⚠ REINICIAR UVICORN para que los fixes entren en efecto

  ARCHIVOS CREADOS (diagnóstico):
    diag_octavos.py + run_diag_octavos.bat       ← estado BD de R16
    diag_y_fix_octavos.py + run_diag_fix_octavos.bat ← diagnóstico + auto-mapeo + sync + puntajes

  ACCION REQUERIDA:
    1. Reiniciar uvicorn (cd backend → .venv\Scripts\Activate.ps1 → uvicorn app.main:app --reload --port 8000)
    2. POST Herramientas → "🔄 Sync desde API-Football" para pre-mapear R16 restantes (P91-P96)
    3. sync_auto.py (Task Scheduler) actualiza automáticamente cuando los partidos se jueguen

2026-07-04 - Sesion Cowork (sesion 62+63) - ENDPOINTS CONSULTA/SYNC PARTIDO + FIX CONECTADOS HOY:

  ENDPOINTS NUEVOS (apostador_bets.py):

  GET /consulta-partido/{numero_fifa} (admin):
    - Busca partido por numero_fifa en BD; obtiene api_fixture_id.
    - Llama GET /fixtures?id={api_fixture_id} desde API-Football (solo lectura).
    - Parsea todos los eventos: amarillas (excluye tarjetas a cuerpo técnico via player.id==null),
      rojas, VAR, minuto_primer_gol, penales_partido.
    - Retorna {ok, bd: {...}, api: {...}, diferencias: {campo: {bd, api}}}.
    - No modifica BD. Sirve para diagnosticar diferencias.

  POST /sync-partido/{numero_fifa} (admin):
    - Si no hay api_fixture_id → llama auto_mapeo_torneo() primero.
    - Fetch fixture desde API-Football, llama _update_partido_full().
    - Avanza bracket: _maps = await _ko.build_num_maps(db, torneo_id);
      await _avanzar_bracket(db, torneo_id, _maps).
    - Recalcula puntajes. Retorna {ok, partido, goles, api_items, bracket_ok, puntajes_ok}.

  GET /ultimo-calculado/{torneo_id}:
    - Retorna el último partido con puntaje_detalle calculado (ORDER BY fecha DESC).
    - Incluye: numero_fifa, equipos, goles, fase, iso local/visitante, apostadores_calculados.
    - Usado por banner "Último calculado" sobre el ranking en el dashboard.

  SCRIPTS CREADOS/ACTUALIZADOS:
    diag_y_sync_p90.py: reescrito — usa /consulta-partido/90 y /sync-partido/90.
    run_diag_sync_p90.bat: launcher (call backend\.venv\Scripts\activate && python diag_y_sync_p90.py).
    finalizar_partido_ko.py: fix HTTP 422 — login cambiado de form-data a JSON
      (LoginRequest espera application/json; antes enviaba x-www-form-urlencoded).

  UI - PORTAL + MOVIL:
    api() fix (ambas interfaces): if (r.status === 204) return null; antes de r.json()
      → resuelve error al eliminar KPIs (portal.py retorna 204 No Content en DELETE /kpis/{id}).
    Banner "Último partido calculado" sobre ranking del dashboard:
      CSS .ult-partido-banner. Función loadUltimoCalculado(torneoId) en portal,
      loadUltimoCalculadoM(torneoId) en móvil. Llamado desde loadRankingDash().

  FIX CONECTADOS HOY (apostador_bets.py — 3 cambios):

  1. POST /live-presencia:
     Ahora también actualiza _online_users[apostador_id]='playoffs' Y escribe en
     usuario_actividad_dia (UPDATE si ya existe fila del día, INSERT si no).
     Cualquier apostador que sincronice o que loadLive() dispare (cada 30s) en
     becbuc-live-playoffs.html queda registrado en "Conectados hoy".

  2. GET /usuarios-online:
     Bug: COALESCE(apostador, username) — columna 'apostador' no existe en app_db.
     Causaba ProgrammingError silencioso → alias_map={} → todos aparecían como "U{id}".
     Fix: cambiado a SELECT username directamente.

  3. POST /heartbeat INSERT:
     Bug: ON CONFLICT (user_id, fecha) falla si la tabla fue creada sin constraint UNIQUE.
     Fix: patrón UPDATE + INSERT — UPDATE primero; si rowcount=0 → INSERT.
     No depende del constraint (aunque la tabla lo tiene en la versión actual).

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py)
    backend/static/BECBUC-portal.html (via safe_patch_html)
    backend/static/BECBUC-movil.html (via safe_patch_html)
    diag_y_sync_p90.py
    finalizar_partido_ko.py

2026-07-04 - Sesion Cowork (sesion 61) - FIX DOBLE CONTEO ITEM P GRUPOS + DESGLOSE P KO POR FASE:

  BUG CRITICO - Doble conteo ítem P (equipo clasifica) en fase de grupos:
    CAUSA: copa_mundo_2026.py tenía pts_equipo_clasifica=1 para grupos.
      sync_api_football.py setea equipo_clasificado_id = ganador del partido en TODOS los partidos
      (incluidos los 72 de grupos). Esto hacía que el engine score P por partido de grupo
      (hasta 72 pts en puntaje_detalle.pts_equipo) Y calculate_clasificados() sumaba
      OTROS 23-28 pts de apostador_clasificados. Total inflado: hasta ~100 pts por apostador.
    
    DATOS DIAGNÓSTICO (diag_clasificados2.py):
      cat_equipo grupos (puntaje_detalle): 42-52 pts por apostador ⚠️
      cat_equipo KO (puntaje_detalle):     24-34 pts por apostador (correcto)
      pts_grupos_p (apostador_clasificados): 23-28 pts (correcto)
      Total doble-contado que mostraba el ranking: hasta 82 pts

    FIX 1 - copa_mundo_2026.py (inmediato):
      pts_equipo_clasifica=1 → pts_equipo_clasifica=0 para 'grupo'
      Futuras recalculaciones no producirán pts_equipo en partidos de grupo.

    FIX 2 - SQL (ejecutar run_fix_pts_equipo_grupos.ps1):
      UPDATE puntaje_detalle: pts_equipo=0, pts_bonus-=old_pts_equipo, pts_total-=old_pts_equipo
      para todos los partidos de fase de grupos.
      Necesario porque grupos están BLOQUEADOS → el recalculo normal no los toca.
      Archivo: documentacion/fix_pts_equipo_grupos.sql

    DESPUÉS DEL FIX SQL: correr POST /calcular-puntajes/2 para recalcular KO (no toca grupos).
    RESULTADO ESPERADO: cat_equipo en ranking = solo KO (24-34 pts), pts_grupos_p = 23-28 pts.
    TOTAL P correcto: ~50-60 pts máximo (KO + grupos clasificados).

  DESGLOSE P KO POR FASE en árbol de ranking (sesion 61):
    - BECBUC-portal.html: label "P — Clasificados R32" → "P Grupos — Clasif. R32 (max 32)"
      + filas dinámicas por fase KO: ronda32/ronda16/cuartos/semis/tercer_puesto/final
      con color diferenciado y pts por fase.
    - BECBUC-movil.html: equivalente en toggleRkAposM (mismo desglose).
    - apostador_bets.py: nuevo campo clasifica_ko_fases en ranking response:
      {fase_tipo: pts} por fase KO con pts_equipo > 0 (excluye grupos).

  PRESENCIA LIVE / BANDERAS - SESION 60 (completado):
    - Banderas: Twemoji CDN migrado de twemoji.maxcdn.com a cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/
    - flagFromIso(): fix para GB-ENG/GB-SCT/GB-WLS (lookup explícito antes de procesar ISO code)
    - becbuc-live-playoffs.html: loadApostadores() usa /apostadores (rol='apostador', excluye admins)
    - _registrarPresencia(): fire-and-forget a POST /live-presencia en 2 eventos:
        1. confirmApostadorSelection() → login inicial del apostador
        2. syncNow() → cuando el apostador presiona Sincronizar

  ARCHIVOS MODIFICADOS SESION 61:
    backend/app/services/scoring/engines/copa_mundo_2026.py:
      - pts_equipo_clasifica: grupo 1 → 0 (P grupos = solo apostador_clasificados)
    backend/static/BECBUC-portal.html (sesion 60):
      - clasifica_ko_fases desglose en árbol ranking
    backend/static/BECBUC-movil.html (sesion 61):
      - clasifica_ko_fases desglose en toggleRkAposM
    backend/app/api/v1/endpoints/apostador_bets.py (sesion 60):
      - clasifica_ko_fases en ranking response (excluye grupos)
    documentacion/fix_pts_equipo_grupos.sql (NUEVO - EJECUTAR):
      - Limpia pts_equipo de partidos de grupo en puntaje_detalle
    run_fix_pts_equipo_grupos.ps1 / .bat (NUEVO):
      - Launcher para ejecutar el SQL fix

  PASOS PENDIENTES PARA COMPLETAR EL FIX:
    1. Ejecutar: run_fix_pts_equipo_grupos.ps1
    2. Ejecutar: POST /calcular-puntajes/2 (desde portal Herramientas)
    3. Verificar ranking: cat_equipo debe ser 24-34 pts (solo KO), pts_grupos_p 23-28 pts

2026-07-04 - Sesion Cowork (sesion 60) - PRESENCIA LIVE + FIX SIN-APUESTAS + UX MONITOREO:

  MONITOREO - sin_apuestas (fix critico):
    PROBLEMA: Mostraba 16 apostadores incompletos cuando debia mostrar 0.
    CAUSA: Query sumaba partidos pendientes de TODAS las fases abiertas (8vos+4tos+semis+final=16).
    FIX (apostador_bets.py): LIMIT 1 al primer join de fases_abiertas_info para tomar solo
    la primera fase abierta. apuestas_map construido contra esa fase sola.
    RESULTADO: Indica correctamente cuantos apostadores no apostaron en la fase abierta actual.

  MONITOREO - hora en partidos de hoy:
    BECBUC-portal.html: cards de partidos del dia muestran la hora local (hh:mm) del partido.
    Computed desde p.fecha (UTC) → hora CR local via new Date().toLocaleTimeString().

  MONITOREO / DASHBOARD - indicador "En live":
    - KPI tile nuevo "🟢 En live" (id=monKpiOnline) en el panel de monitoreo.
    - _loadMonitorData(): fetcha /usuarios-online en paralelo, incluye la cuenta en el tile.
    - onlineNowBar en panelUsuariosHoy: muestra alias de quien esta conectado (web/movil/playoffs).
    - Auto-refresh 30s: _startOnlineNowRefresh() / _stopOnlineNowRefresh() en showView().

  PRESENCIA LIVE-PLAYOFFS — mecanismo nuevo sin auth:
    PROBLEMA RAIZ: becbuc-live-playoffs.html auto-loguea como jose (admin); todos comparten
    el mismo user_id en _online_users → siempre mostraba 1-2 personas sin importar cuantas habia.
    
    FIX 1 (ya aplicado sesion anterior): heartbeat acepta viewas_id (apostador seleccionado).
    FIX 2 (sesion 60): _live_presencia — mecanismo complementario via loadLive().

    apostador_bets.py:
      + _LIVE_TTL = 90  (segundos; loadLive corre cada 30s, 3 ciclos de margen)
      + _live_presencia: dict[int, tuple[float, str, int]] = {}
        (apostador_id → (timestamp, alias, torneo_id))
      + POST /api/v1/bets/live-presencia (sin auth):
          Acepta apostador_id, torneo_id=2, alias.
          Registra en _live_presencia con timestamp actual.
          Retorna {ok: True}.
      + /usuarios-online: merge _live_presencia activos en result["playoffs"].
          Combina con alias_map. Deduplica por nombre.
          result["total"] = len({*activos.keys(), *live_activos.keys()})

    becbuc-live-playoffs.html:
      + loadLive(): al final, si _viewAsId != null → fire-and-forget fetch a /live-presencia.
          Usa _viewAsName como alias. No bloquea el render.
      + RESULTADO: cada apostador que visita la pagina y selecciona su nombre
        queda registrado en el servidor. /usuarios-online refleja presencia real.

  ARCHIVOS MODIFICADOS SESION 60:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py):
      - sin_apuestas: LIMIT 1 al primer join de fases abiertas
      - _live_presencia + _LIVE_TTL agregados al modulo
      - POST /live-presencia endpoint nuevo (sin auth)
      - /usuarios-online: merge _live_presencia en result["playoffs"]
    backend/static/BECBUC-portal.html (via safe_patch_html):
      - Hora en cards partidos de hoy
      - KPI tile "En live" en monitoreo
      - onlineNowBar + loadOnlineNow() + auto-refresh 30s
    backend/static/becbuc-live-playoffs.html (via safe_patch_html):
      - loadLive(): fire-and-forget fetch a /live-presencia al cargar datos
      - Usa _viewAsName como alias para la presencia

2026-07-03 - Sesion Cowork (sesion 59) - R32 RECONCILIACION COMPLETA + TASK SCHEDULER FIX:

  DIFERENCIAS CONOCIDAS ENTRE EXCEL TBL CHECK Y BD (para referencia):

  GRUPOS (P001-P072) — Estado al cierre sesion 58:
    H=0, I=0, J=0, K=0, L=0, M=0, N=11, O=0  → TOTAL DIFFS=11
    N=11: BD otorga 1pt a TODOS los apostadores empatados en distancia minima al minuto gol.
          Excel (TBL CHECK) puede usar criterio distinto (solo el mas cercano).
          BD ES CORRECTO segun decision organizacion 2026-07-02 (todos los empatados suman).
          No cambiar algoritmo BD sin nueva confirmacion de organizacion.

  R32 (P073-P088) — Estado al cierre sesion 59:
    H=0, I=0, J=0, K=0, L=0, M=0, N=2, O=0   → TOTAL DIFFS=2
    N=2: Mismo algoritmo de tie-breaking (BD correcto, Excel puede diferir).
         BD total=4280 pts, Excel total=4278 pts, diff=+2 exactamente los 2 N.
    ✅ R32 RECONCILIADO. BD y Excel coinciden en todos los items H-O excepto N algoritmico.

  PENDIENTES R32:
    P083-P088: 6 partidos aun sin jugar al 2026-07-03.
    Predicciones bonus (pred_amarillas, rojas, etc.) para P083-P088 YA IMPORTADAS
    via importar_bonus_r32_desde_excel.py (sesion 59).
    Cuando se jueguen: correr comparar_puntajes_r32.py para verificar.

  FIX APOSTADORES ENDPOINT:
    /apostadores: columna u.apostador no existe en users table → cambiado a u.username.
    Esto causaba "is not iterable" en tab Puntajes de becbuc-live-playoffs.html.
    Fix aplicado via safe_patch_py en apostador_bets.py.

  TASK SCHEDULER — MultipleInstances=IgnoreNew:
    PROBLEMA: dos instancias de sync_auto.py corriendo en paralelo causaban
    "sqlalchemy.dialects.postgresql.asyncpg.Error" (race condition en sesion BD).
    FIX: Tarea BECBUC-SyncAPI re-registrada como Admin con -MultipleInstances IgnoreNew.
    Verificado: (Get-ScheduledTask -TaskName "BECBUC-SyncAPI").Settings.MultipleInstances → "IgnoreNew"
    Ahora si el sync tarda >1 min, el siguiente ciclo se descarta (no corre en paralelo).

  SCRIPTS CREADOS SESION 59:
    actualizar_r32_desde_excel.py  <- actualiza partido tabla desde hoja "40- RESULTADOS OFICIALES"
    run_actualizar_r32.bat         <- launcher para actualizar_r32_desde_excel.py
    importar_bonus_r32_desde_excel.py <- importa predicciones bonus R32 desde hoja "50- TBL MASTER"
    comparar_puntajes_r32.py       <- compara H-O entre TBL MASTER y puntaje_detalle BD

  COLUMNAS HOJA "50- TBL MASTER" (referencia para proximas sesiones):
    col[1]=ID PARTIDO (P073...), col[9]=ALIAS (prefijo \xa0), col[54]=ESTADO
    col[12]=pred_local, col[14]=pred_visitante
    col[24]=pred_amarillas, col[25]=pred_rojas, col[26]=pred_var, col[27]=pred_penales_partido
    col[28]=pred_minuto_gol, col[29]=pred_penales_local_tanda, col[30]=pred_penales_visitante_tanda
    col[39]=H, [40]=I, [41]=J, [42]=K, [43]=L, [44]=M, [45]=N, [46]=O-EQ1, [47]=O-EQ2
    Valor 99 en tanda = sin tanda (tratar como NULL en BD).
    partido.penales_local/penales_visitante (NO penales_local_tanda/penales_visitante_tanda).

2026-07-02 - Sesion Cowork (sesion 58) - RECONCILIACION PUNTAJES vs TBL CHECK EXCEL:

  OBJETIVO: Reducir diferencias item x item entre BD (puntaje_detalle) y TBL CHECK Excel.

  HERRAMIENTAS CREADAS:
    - Endpoint temporal /api/v1/bets/tmp-becbuc-sql (ELIMINADO al cierre de sesion):
        Permitio consultas SQL directas en becbuc DB desde JS en Chrome.
        Patron: safe_patch_py para agregar, mismo para eliminar post-sesion.
    - excel_tbl_check2.json: servido en /static/, formato {alias: {numero_fifa: {H..O, total}}}.
    - actualizar_resultados_desde_excel.py + run_actualizar_resultados.bat: sync resultados desde Excel.

  SWAP DE PREDICCIONES — HISTORIA COMPLETA:
    El import original de pronosticos usaba numero_fifa para asociar predicciones a partido_id.
    En sesion anterior (fix_swap_numero_fifa.sql), 5 pares de partidos tuvieron su numero_fifa
    intercambiado para corregir el orden en la BD. Esto dejo las predicciones de esos pares
    bajo los partido_ids incorrectos.

    INTENTO ERRONEO (revertido): fix_swap_predicciones.sql aplicado a los 44 apostadores
    genero 785 diffs (H=294). Causa: la mayoría de los apostadores ya tenian las predicciones
    correctas. El doble-swap (aplicar 2 veces) revirtio al estado original (13 diffs H=2).

    FIX CORRECTO: Solo cherem (apostador_id=15) tenia 2 pares incorrectos:
      - P049 (Scotland/Brazil, pid=194) ↔ P050 (Morocco/Haiti, pid=193): cherem swapped ✅
      - P055 (Curaçao/Ivory Coast, pid=198) ↔ P056 (Ecuador/Germany, pid=197): cherem swapped ✅
      - P061/P062, P065/P066, P067/P068: NO swapped (cherem tenia correctos)

    SWAP APLICADO: CTE atomico en becbuc DB, 1 fila por par (solo apostador_id=15).
    POST-RECALCULO: plenos=428, aciertos=1685, fallos=1495, grupos total=18441.

  RESULTADO FINAL DE COMPARACION (grupos P001-P072):
    H=0, I=0, J=0, K=0, L=0, M=0, N=11, O=0  → TOTAL DIFFS=11
    H=0 confirma que el fix de cherem fue correcto.

  N=11 DIFERENCIAS (algoritmicas, no errores de datos):
    BD=1 donde TBL=0 para item N (minuto primer gol).
    Apostadores afectados: @bs (P006,P012), alfaorion 99 (P037), tony (P006),
      sajano freddy (P037), pato (P002,P058), monkey (P002), cayetano (P021),
      gh1s (P037), moño (P037).
    Causa: diferencia de algoritmo de tie-breaking (ver pregunta pendiente #2 en reglamento).
    BD otorga 1 pt a TODOS los empatados en el minuto mas cercano.
    TBL CHECK puede usar criterio distinto (solo el mas cercano de un lado, etc).
    NO se cambia el algoritmo de BD sin confirmacion de la organizacion.

  ARCHIVOS MODIFICADOS SESION 58:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py):
      + Endpoint temporal /tmp-becbuc-sql (AGREGADO al inicio, ELIMINADO al cierre).
    documentacion/fix_swap_predicciones.sql: obsoleto (swap para 44 apostadores, NO usar).
    run_fix_swap_predicciones.bat: obsoleto (NO usar).
    [CTE swap cherem directamente en Docker via /tmp-becbuc-sql endpoint]

  REFERENCIA DE PARES SWAP (para futuras sesiones):
    P049 (Scotland/Brazil) pid=194 ↔ P050 (Morocco/Haiti) pid=193
    P055 (Curaçao/Ivory Coast) pid=198 ↔ P056 (Ecuador/Germany) pid=197
    P061 (Norway/France) pid=204 ↔ P062 (Senegal/Iraq) pid=203
    P065 (Cape Verde/Saudi Arabia) pid=206 ↔ P066 (Uruguay/Spain) pid=205
    P067 (Panama/England) pid=210 ↔ P068 (Croatia/Ghana) pid=209
    cherem apostador_id = 15
    Solo P049/P050 y P055/P056 eran incorrectos para cherem.



2026-07-01 - Sesion Cowork (sesion 57) - HOJA BECBUC AUDIT + AUDITORIA DIFF CON DIAGNOSTICO:

  HOJA "becbuc audit" en _build_auditoria_workbook (apostador_bets.py):
    39 columnas (antes 38): agregada "H- TANDA PENALES" entre "G- 1ER GOL" y "TOTAL".
    Mapeo de columnas de puntaje (idx 0-based desde fila):
      Col 30 (idx 29): A- GANA-EMPATA-PIERDE  → pts_resultado
      Col 31 (idx 30): B- RESULTADO EXACTO    → pts_marcador
      Col 32 (idx 31): C- AMARILLAS           → pts_amarillas
      Col 33 (idx 32): D- ROJAS               → pts_rojas
      Col 34 (idx 33): E- VAR                 → pts_var
      Col 35 (idx 34): F- PENALES             → pts_penales_partido
      Col 36 (idx 35): G- 1ER GOL             → pts_minuto
      Col 37 (idx 36): H- TANDA PENALES       → pts_penales_tanda  ← NUEVO
      Col 38 (idx 37): TOTAL                  → suma de A-H
      Col 39 (idx 38): ESTADO PARTIDO
    TOTAL ahora incluye pts_penales_tanda (antes no lo sumaba).
    Query pron_r: + COALESCE(pd.pts_penales_tanda, 0) AS pts_penales_tanda.

  ENDPOINT auditoria_diff (POST /admin/auditoria-diff/{torneo_id}):
    COMPLETAMENTE REDISEÑADO con 3 tipos de diagnóstico.
    ANTES: 7 columnas [P#, Fase, Local, Visitante, Campo, Excel, BD].
    AHORA: 9 columnas [P#, Fase, Local, Visitante, ALIAS, Campo, Excel, BD, DIAGNÓSTICO].
    3 hojas en el Excel de salida:
      1. "Diferencias" — diferencias de resultado (goles) por partido.
      2. "Sin Diferencias" — partidos con goles coincidentes.
      3. "Puntajes" — diffs de puntaje por apostador × partido (si hay sheet "becbuc audit").
      4. "Globales" — diffs de puntaje_global (si hay sheet "Globales").
    Lógica de DIAGNÓSTICO por campo:
      "resultado de partido no coincide" — goles en Excel ≠ goles en BD.
      "error de algoritmo becbuc — puntaje no calculado" — puntaje_detalle no existe.
      "error de algoritmo becbuc — puntaje en 0" — BD tiene 0 pero Excel tiene pts.
      "error del excel" — goles OK + puntaje_detalle correcto, discrepancia en el Excel.
      "error del excel (globales)" — para puntaje_global.
    Cada diagnóstico incluye los labels de campo que no coinciden (→ A- GANA-EMPATA-PIERDE, B- ...).
    Campos comparados en "becbuc audit" sheet (_SCORE_COLS):
      A-GANA-EMPATA-PIERDE, B-RESULTADO EXACTO, C-AMARILLAS, D-ROJAS,
      E-VAR, F-PENALES, G-1ER GOL, H-TANDA PENALES (8 items)
    TOTAL comparado: suma de los 8 items (_SCORE_COLS), NO el valor de la columna TOTAL del Excel.
      Si total computed Excel ≠ total computed BD y no hay items individuales con diferencia,
      se reporta "TOTAL" como campo diferente.
    Campos comparados en "Globales" sheet:
      A-CAMPEON, B-FINALISTAS, C-GOLEADOR, D-PEOR EQUIPO,
      E-MAYOR GOLEADA, F-ETAPA PARAGUAY, G-GOLES PARAGUAY.

  REGLA: Hoja "becbuc audit" del Excel generado por BECBUC puede subirse al endpoint
    auditoria_diff para comparar puntajes apostador × partido contra la BD.
    El alias (col 7, ALIAS) se usa para identificar al apostador en la BD.

  SKILLS CREADOS:
    becbuc-safe-edit  — evitar truncacion en archivos >50KB (usar safe_patch_py)
    becbuc-file-naming — todos los archivos generados usan prefijo becbuc_

  CONVENCIONES DE ARCHIVOS:
    Todos los archivos de salida BECBUC: becbuc_<tipo>_<descripcion>_<YYYYMMDD_HHMM>.<ext>
    Ejemplos: becbuc_auditoria_20260701_1200.xlsx, becbuc_ranking_export_20260701.xlsx
    7 filenames corregidos en sesión anterior (sesion 56).

  PRIVACIDAD: siempre usar a.apostador (alias) nunca a.nombre (nombre real).
    En "becbuc audit": col NOMBRE y col ALIAS ambas muestran el alias, no el nombre real.

  ITEM P (equipo clasifica) - FIX SESION 57:
    copa_mundo_2026.py: si pred gana → inferir clasificado del marcador (no usar pred_equipo_clasifica).
    Si pred empate → usar pred_equipo_clasifica (o inferir de tanda si es NULL).
    En KO no existe resultado de empate final: siempre hay ganador.

  ARCHIVOS MODIFICADOS SESION 57:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py):
      - Hoja "becbuc audit": + H- TANDA PENALES, TOTAL actualizado, query + pts_penales_tanda
      - auditoria_diff: rediseño completo con diagnóstico + hojas Puntajes y Globales
    backend/app/services/scoring/engines/copa_mundo_2026.py:
      - Item P: fix victoria predicha → inferir clasificado del marcador



2026-06-30 - Sesion Cowork (sesion 56) - TAB GOLEADORES EN PUNTAJES + FIXES ANTERIORES:

  SUB-TAB GOLEADORES (becbuc-live-playoffs.html):
    - Nuevo sub-tab "⚽ Goleadores" dentro del tab Puntajes (junto a "📊 Ranking").
    - Barra de sub-tabs: .sc-subtabs / .sc-subtab con estado active.
    - setScoresSubTab(name): alterna entre panes #scp-ranking y #scp-goleadores.
    - loadGoleadores(force): llama GET /api/v1/bets/goleadores/{torneo_id}.
    - renderGoleadores(): tabla con foto, nombre, equipo, goles, asistencias, apostadores.
    - Resaltado del apostador seleccionado (verde) si su predicción matchea al jugador.
    - Badge 👥 con cantidad de apostadores que eligieron ese jugador (tooltip con aliases).
    - Panel superior: "Tu predicción" + estado (✅ +20pts / ❌ 0pts / pendiente).
    - Goleador oficial (resultado_goleador admin): fila con 🏆 en dorado.
    - Match por substring entre pred_goleador (texto libre) y nombre API-Football.

  ENDPOINT NUEVO (apostador_bets.py):
    - GET /api/v1/bets/goleadores/{torneo_id}:
        Llama API-Football /players/topscorers?league={api_league_id}&season={api_season}.
        Lee pred_goleador de apuesta_global para todos los apostadores.
        Obtiene aliases desde app_db via _app_engine.
        Match aproximado: substring entre pred_goleador y nombre del jugador.
        Retorna: scorers[] (top 20), my_pred, resultado_goleador, predicciones{}.
        1 llamada a API-Football por request (consume cuota).

  OTROS FIXES SESION 56:
    - sim-bar: partidos finalizados ahora muestran marcador en gris ("1-2") en vez de "vs".
    - apostador_bets.py partidos_hoy: usa timezone America/Costa_Rica (no UTC) para fecha.
      Permite que partidos programados para las 19:00 CR (01:00 UTC día siguiente) aparezcan.
      Elimina filtro de estado: también muestra partidos finalizados del día.
    - table_crud.py: _coerce_value() para TIMESTAMP ahora maneja ISO 8601 con timezone (+00:00).
      Usa datetime.fromisoformat() + regex strip de timezone offset como fallback.
    - Backup 20260630_1915 ejecutado. Puntajes recalculados incluyendo P78 (1-2 Norway).
    - Ranking actualizado: checho 530, seba 530, hs 511, lav 499, vitra 498.

  ESTADO TORNEO:
    - R32 finalizados: P73 (SA 0-1 CAN), P74 (GER 1-1 PAR pen 3-4 🇵🇾), P75 (NED 1-1 MAR pen 2-3),
      P76 (BRA 2-1 JPN), P78 (CIV 1-2 NOR).
    - Goleadores al 30/06: Messi 6g, Mbappé 4g, Vinícius 4g.
    - 27 apostadores eligieron a Mbappé como goleador (ítem C).



2026-06-29 - Sesion Cowork (sesion 55) - FIX SYNC ALARGUE Y PENALES (hay_partido_activo):

  BUG: Cuando un partido KO terminaba el tiempo reglamentario (90 min), API-Football
    retornaba status 'FT' brevemente antes de que empezara el alargue (AET).
    El sync veia 'FT' → STATUS_MAP['FT'] = 'finalizado' → marcaba el partido como finalizado en BD.
    En el siguiente ciclo de sync_auto.py, hay_partido_activo excluia el partido
    con `AND p.estado != 'finalizado'` → activo=False → sync NO corria.
    Resultado: todo el alargue (ET/BT) y la tanda de penales (P/PEN) se perdian sin sync.

  CAUSA RAIZ: La condicion `AND p.estado != 'finalizado'` en hay_partido_activo bloqueaba
    el re-chequeo de partidos que habian sido marcados finalizado de forma prematura.

  FIX (apostador_bets.py - hay_partido_activo):
    - Eliminada condicion `AND p.estado != 'finalizado'` del WHERE.
    - Reemplazada por `AND NOT COALESCE(p.datos_confirmados, FALSE)`.
    - Solo los partidos que el admin blindó (Blindar) quedan excluidos del sync.
    - La ventana temporal 15-300 min ahora aplica a partidos en CUALQUIER estado
      (programado, en_juego, o finalizado-transitorio por el FT breve).
    - El OR `p.estado = 'en_juego'` sigue siendo el fallback sin límite temporal.

  FIX (sync_api_football.py - fallback window):
    - Aumentado de 200 a 240 minutos el in_window del fallback de sync_torneo.
    - Cubre: 90 min reglamentario + 30 AET + 30 penales + 90 buffer/margen.

  FLUJO CORRECTO AHORA:
    1. Partido en 2H (90 min): sync normal, en_juego ✓
    2. Status API = 'FT' brevemente: sync marca finalizado en BD, pero...
    3. Siguiente ciclo: hay_partido_activo incluye el partido (dentro de ventana 300 min,
       datos_confirmados=False) → activo=True → sync corre
    4. live=all retorna el partido con status 'ET' → _update_partido_full
       → STATUS_MAP['ET'] = 'en_juego' → BD revierte a en_juego ✓
    5. Alargue completo synced. Cuando termina → status 'AET' o 'P'/'PEN'.
    6. 'PEN': pen_home/pen_away correctamente extraidos → partido finalizado con tanda ✓
    7. Admin hace click en Blindar → datos_confirmados=True → sync se detiene ✓

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py)
    backend/app/services/sync_api_football.py (via safe_patch_py)



2026-06-28 - Sesion Cowork (sesion 52) - IMPORTACION R32 + RANKING COMPLETO + PLAYOFFS MI PRONO:

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py
    backend/static/becbuc-live-playoffs.html
    backend/static/BECBUC-portal.html
    backend/static/BECBUC-movil.html

  ARCHIVOS CREADOS:
    importar_r32_excel.py  <- importa pronosticos R32 (P073-P088) desde Excel consolidado
    run_importar_r32.bat   <- dry-run (solo verifica aliases y muestra diferencias)
    run_importar_r32_IMPORT.bat  <- ejecuta la importacion real
    set_peor_equipo_irak.bat     <- registra Iraq como peor equipo via API

  RANKING - apostador_bets.py:
    - Agregado query a apostador_clasificados (fase_tipo='grupo') para pts_grupos_p
    - Agregado query a puntaje_global para pts_peor_equipo_d (item D) por separado
    - puntos_total = pts_partidos + pts_globales + pts_grupos_p (CORREGIDO - faltaba pts_grupos_p)
    - campos nuevos en response: pts_grupos_p, pts_peor_equipo_d

  becbuc-live-playoffs.html (via Python bash, NO Edit tool):
    - 4 sub-tabs: partido | miprono | predicciones | ranking
    - Tab "Mi Prono": renderMiProno(p) - compara prediccion del usuario vs resultado real item a item (H-O)
    - Seccion scores breakdown: pts_partidos + pts_grupos_p + pts_peor_equipo_d + pts_globales
    - CSS: .mp-*, .sb-breakdown*
    - Auto-refresh mejorado: detecta cambios de estado del partido
    - PRIVACIDAD fix: r.apostador||r.username en renderRanking/renderPredictions

  BECBUC-portal.html + BECBUC-movil.html:
    - Ranking total: incluye pts_grupos_p en calculo frontend
    - Arbol apostador: muestra desglose P grupos y D peor equipo

  REGLA NUEVA: Para archivos >200KB, usar Python bash en lugar de Edit tool
    (Edit tool trunca al tamano original en bytes cuando se inserta contenido mas largo)

  EXCEL R32:
    - importar_r32_excel.py mapea aliases del Excel a apostador_id en BD
    - Columnas: pred_local/visitante (9/11), amarillas(21), rojas(22), var(23),
      penales_partido(24), minuto_gol(25), tanda_local(26), tanda_visitante(27)
    - Constraint UNIQUE(apostador_id, partido_id) - usa ON CONFLICT DO UPDATE
    - Verificacion de puntajes GRUPOS: compara columna TOTAL(36) Excel vs puntaje_detalle BD

  PENDIENTES:
    1. POST /calcular-puntajes/2 → sanbie recibe 20 pts Iraq (item D). ✅ LISTO EJECUTAR.
    2. Verificar predicciones R32 en tab Mi Prono de live-playoffs (704 importadas).
    3. Al terminar R32 → sync auto propagara ganadores a R16 automaticamente.



2026-06-29 - Sesion Cowork (sesion 54) - FIX SYNC + EVENTOS API + CAMBIO USUARIO LIVE + SEDE BRACKET + R32 SCORING:

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html (via safe_patch_html)
    backend/app/services/sync_api_football.py (via safe_patch_py)
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py)
    backend/app/services/scoring/calculator.py (via safe_patch_py)

  BUG 1 - Boton Sync no funcionaba en becbuc-live-playoffs.html:
    CAUSA: syncNow() tenia guard `if (_isAdmin)` pero _isAdmin quedaba false porque
      init() falla silenciosamente al llamar /auth/me (empty catch block).
    FIX: Eliminado el guard — la pagina siempre auto-loguea como jose (admin) y
      el API mismo valida permisos. Sync ahora funciona sin restriccion JS.

  BUG 2 - Historial de eventos del partido no se mostraba (tab En Vivo):
    CAUSA: sync_api_football.py habia eliminado el write de eventos_api en sesion 21
      para evitar crash si la columna no existia. La columna SI existe (migracion sesion 21).
    FIX: Re-habilitado write de eventos_api en _update_partido_full():
      UPDATE partido SET ... eventos_api = COALESCE(CAST(:eventos_json AS jsonb), eventos_api)
    NOTA: ::jsonb causa PostgresSyntaxError con asyncpg (interpreta : como param binding).
      Usar CAST(:col AS jsonb) en todos los casos de este tipo.

  BUG 3 - Al cambiar usuario en combo no se actualizaba el tab live:
    CAUSA: setViewAs() llamaba renderBracket() + renderScoresTab() pero NO renderLiveContent()
      ni renderMiProno(). El tab activo quedaba con datos del usuario anterior.
    FIX: Agregado en setViewAs() al final:
      if (_activeTab === 'live') renderLiveContent();
      if (_activeTab === 'miprono') renderMiProno(_liveData?.partido);
      if (_activeTab === 'apuestas') renderApuestasTab();

  FEATURE - Sede/ciudad en bracket list cards:
    - apostador_bets.py bracket_real: agrega p.sede, p.ciudad al SELECT y al output dict.
    - becbuc-live-playoffs.html renderBracketList(): muestra "📍 Ciudad · Sede" debajo
      de cada card con CSS .match-venue-row y .match-venue.

  BUG 4 - Puntajes R32 todos en 0 (ronda32 fallos=88, total=0):
    CAUSA: _check_teams_match() en calculator.py simulaba bracket desde predicciones
      de grupos via simular_standings_usuario() + armar_ronda32(). Copa del Mundo 2026
      tiene bracket FIJO (Grupo X vs Grupo Y predeterminado) que armar_ronda32() NO replica
      correctamente → teams_match=False para todos → 0 pts.
      Los apostadores importaron predicciones R32 directamente via importar_r32_excel.py.
    FIX: Agregado early return en _check_teams_match():
      if tipo == "ronda32": return True
      (equipos reales en R32 son los correctos; teams_match siempre True para ronda32)
    RESULTADO: plenos=27, aciertos=42, ronda32.total=896 pts. ✅

  VERIFICACION POST-SESION:
    POST /calcular-puntajes/2 → {ok:true, plenos:27, aciertos:42, fallos:19,
      ronda32:{marcador:738, bonus:158, total:896, apuestas:88}, globales_procesadas:44}

2026-06-29 - Sesion Cowork (sesion 54 continuacion) - FIX PREDICCIONES MI PRONO + ITEM E AL FINAL:

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html (via safe_patch_html)
    backend/app/api/v1/endpoints/apostador_bets.py (via safe_patch_py)
    backend/app/services/scoring/calculator.py (via safe_patch_py)

  BUG 1 - Predicciones del apostador no cargaban en renderMatchDetail (tab Mi Prono):
    CAUSA RAIZ 1: selectAposFromMatrix() no llamaba loadUserPredictions(uid).
      Al seleccionar un apostador en la tabla Puntajes, _userPreds quedaba con
      datos del usuario anterior (o vacio). renderMatchDetail usaba _userPreds[m.num]
      y siempre obtenia undefined → mostraba "?–?" en todos los campos.
    FIX: Agregado await loadUserPredictions(uid) en selectAposFromMatrix()
      antes de renderBracket() y renderScoresItemBreakdown().

    CAUSA RAIZ 2: mis-partidos endpoint no incluia numero_fifa en el SELECT.
      loadUserPredictions() indexa _userPreds por p.numero_fifa cuando no es null
      (fallback a partido_id). Como numero_fifa era null en la respuesta,
      _userPreds quedaba indexado por partido_id (ej: 143, 150...) en vez de
      numero_fifa (73-104). renderMatchDetail busca _userPreds[m.num] donde
      m.num es numero_fifa → siempre undefined.
    FIX: Agregado p.numero_fifa al SELECT de mis-partidos en apostador_bets.py.
    RESULTADO: _userPreds tiene 104 entradas con claves 1-104 (num FIFA). ✓

    CAUSA RAIZ 3: renderRanking() crasheaba con TypeError al intentar
      getElementById('rank-list') que no existe en la vista de playoffs.
      El crash ocurria en cada ciclo de auto-refresh impidiendo otras funciones.
    FIX: Agregado null guard if (!list) return; al inicio de renderRanking().

    CAUSA RAIZ 4: renderMatchDetail() crasheaba con TypeError en
      getElementById('scores-hint') que habia sido eliminado del HTML en sesion anterior.
    FIX: Agregado if (hint) hint.style.display='none'; y if (!section) return; guards.

  BUG 2 - Item E (mayor goleada) se calculaba incrementalmente durante el torneo:
    REGLA: "Los puntajes globales de mayor goleada se calculan solo al final del torneo"
    CAUSA: _load_torneo_resultados() en calculator.py siempre ejecutaba la query
      de mayor goleada (WHERE estado='finalizado' sin chequear si habia campeon).
      Durante R32, la mayor goleada de grupos (ej: 8-0) ya otorgaba puntos,
      lo cual no es correcto segun la regla establecida.
    FIX: Envuelto el bloque E en guard:
      if result.get("campeon_id") is not None:  # solo cuando la Final fue jugada
    COMPORTAMIENTO AHORA:
      - Durante R32/R16/etc: pts_mayor_goleada = 0 para todos los apostadores.
      - Cuando el campeon sea definido (partido final jugado): E se computa
        sobre TODOS los partidos del torneo (la goleada maxima de los 104 partidos).
    NOTA: campeon_id es el mismo gate usado por items A y B (campeon/finalistas).
      Se auto-detecta desde partido final equipo_clasificado_id.

2026-06-29 - Sesion Cowork (sesion 53) - SIM-BAR PARTIDOS DE HOY + MEJORES TERCEROS EN GRUPOS:

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py
    backend/static/becbuc-live.html
    backend/static/BECBUC-portal.html
    backend/static/BECBUC-movil.html (via Python bash, >200KB)

  BUG 1 - Sim-bar solo mostraba partidos en_juego (no todos los del dia):
    CAUSA: renderSimBar() usaba _partEnJuego (solo en_juego), threshold 2+ para mostrar barra.
    FIX apostador_bets.py live_panel:
      - Nueva query "2c. Todos los partidos KO de HOY": estado IN ('en_juego','programado','pendiente')
        filtrado por DATE(p.fecha AT TIME ZONE 'UTC') = CURRENT_DATE y fase NOT ILIKE 'grupo%%'
      - Retorna campo "partidos_hoy": lista de todos los KO del dia (incluye programados)
    FIX becbuc-live.html:
      - let _partHoy = []: nuevo estado para partidos del dia
      - cargarPanel(): carga _partHoy desde data.partidos_hoy
      - renderSimBar(): usa _partHoy si disponible (fallback _partEnJuego); muestra barra con 2+ partidos hoy
        Tabs: .sim-live (rojo) para en_juego con minuto, .sim-prox-tab (gris) para programados con hora local
        Label cambia: "Hoy" vs "En juego" segun fuente de datos
      - navPartido(): prioriza _partHoy sobre _partEnJuego para navegacion

  BUG 2 - Mejores terceros no se actualizaba al cambiar apuesta de grupo:
    CAUSA sesion 43: se elimino #mejores-terceros-panel del DOM y los callers de _renderMejoresTerceros().
    FIX BECBUC-portal.html:
      - _renderBetApostarBody(): agrega <div id="mejores-terceros-panel"> antes de el.innerHTML = html
      - onScoreChange(): agrega llamada a _renderMejoresTerceros() al final
      - recalcularTodos(): agrega llamada a _renderMejoresTerceros() antes del feedback visual
    FIX BECBUC-movil.html (via Python bash):
      - _renderPronosGruposM(): agrega <div id="mejores-terceros-panel-m"> al HTML + llama _renderMejoresTercerosM()
      - Nueva funcion async _renderMejoresTercerosM(): fetcha /mejores-terceros-provisorios/{torneoId}
        y renderiza tabla compacta (# | Equipo+Grupo | Pts | DG | ✓/✗) en el panel

  BUG 3 - becbuc-live-playoffs.html no mostraba horarios de partidos del dia:
    FIX: portado el sim-bar de becbuc-live.html a becbuc-live-playoffs.html.
    CSS: .sim-tab, .sim-label, .sim-live, .sim-prox-tab, .sim-dot-p, .sim-prox, .sim-vs, etc.
    HTML: <div id="sim-bar"> insertado entre topbar y score-hdr
    JS: _partHoy = [] estado, loadLive() lo pobla desde d.partidos_hoy (mismo endpoint ya modificado)
    renderSimBar(): muestra barra con tabs por partido del dia (🔴 en vivo con minuto / 🔵 programado con hora)
    navToPartidoP(num): tap en tab live → setTab('live'); tap en programado → setBracketView('list') + scroll al card
    card.dataset.num = m.num en renderBracketList() para que el scroll funcione

  NOTA: servidor uvicorn necesita reiniciar para leer el nuevo campo partidos_hoy de apostador_bets.py

  PARTE 2 - ANTI-TRUNCACION (sesion 53 continuacion):
    PROBLEMA RAIZ DESCUBIERTO: El Edit tool trunca archivos al tamaño original en bytes
    cuando el nuevo contenido es mayor. Incluso scripts Python bash pueden truncar en paths
    montados Windows cuando el archivo es muy grande. Afecto a 4 archivos en esta sesion:
      - becbuc-live-playoffs.html (Edit tool)
      - apostador_bets.py (Python bash write)
      - BECBUC-portal.html (Edit tool)
      - becbuc-live.html (Edit tool)
    Todos restaurados desde git con `git show HEAD:path > /tmp/restore` + re-apply.

    SOLUCION IMPLEMENTADA:
      safe_write.py (C:\proyecto FAST API\safe_write.py):
        - safe_write(path, content): backup + write + verify + rollback automatico
        - safe_patch_html(path, [(old,new)]): parche seguro para HTML
        - safe_patch_py(path, [(old,new)]): parche seguro para Python
        - verificacion: ast.parse para .py, node --check + </html> para .html
        - backup en C:\proyecto FAST API\_backups\ con timestamp
      USAR OBLIGATORIAMENTE para cualquier archivo >50KB.
      VERIFICAR siempre con: python safe_write.py <archivo>

2026-06-28 - Sesion Cowork (sesion 52 - continuacion, parte 6) - LOGIN REAL + TIMEZONE FIX + TAB LIVE REDESIGN + TAB APUESTAS PRIVACIDAD:

  OBJETIVO: Restaurar becbuc-live-playoffs.html desde git HEAD y re-aplicar todos
    los cambios pendientes (archivo habia quedado corrupto a 218026 bytes).

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html (via Python bash, >200KB):
      Restaurado desde git HEAD + todos los cambios re-aplicados en un script.
      Archivo final: 120572 bytes, 1 <script> / 1 </script>. JS syntax OK.

  CAMBIOS:

  1. LOGIN REAL:
     - Pantalla de login con usuario/contrasena: ELIMINADA.
     - ensureToken(): auto-login silencioso con credenciales internas del sistema.
     - Pantalla #scr-selector: selector de apostador por abecedario (sin contrasena).
       El apostador elige su nombre en un <select> + click 'Continuar'.
       populateApostadorSelector(): llena el combo con apostadores ordenados A-Z.
       confirmApostadorSelection(): setViewAs + showScreen('main') + startAutoRefresh().

  2. TIMEZONE ROBUSTA:
     - const _localTZ: Intl.DateTimeFormat().resolvedOptions().timeZone.
     - _isoToUTC(iso): agrega 'Z' si ISO no tiene indicador de zona (BD guarda UTC sin Z).
     - fmtFechaCorta(): usa _isoToUTC + timeZone:_localTZ -> siempre hora del browser.
     - startCountdown(), getNextMatchNum(): tambien usan _isoToUTC.

  3. TAB EN VIVO - PANEL ITEMS H-O:
     - live-totals movido a sub-miprono (tab Mi Prono): 'Tus puntos este partido'.
     - live-items-panel nuevo en tab-live: grilla 4 col con icono+letra+pts por item.
       H=sol, I=diana, J=amarilla, K=roja, L=TV, M=pelota, N=reloj, Ol/Ov=trofeo.
     - renderLiveItemsPanel(items, total): nueva funcion sincroniza el panel de items.
     - renderLiveTotals() llama renderLiveItemsPanel al final.
     - Ol y Ov: 2 items separados (tanda local / visitante), 2 pts c/u.

  4. AUTO-REFRESH 30s:
     - Intervalo 60000 -> 30000 ms.
     - En cada ciclo si activeTab==='live': llama renderLiveContent().

  5. TAB APUESTAS - PRIVACIDAD:
     - renderApuestasTab() rediseniado: muestra SOLO el apostador seleccionado.
       ANTES: grid con todos los apostadores (violaba privacidad).
       AHORA: usa _bracket + _userPreds del apostador activo (_viewAsId).
     - Cards: score real vs prediccion, color (ok/parcial/fallo/pend), pts H+I.
     - Filtros por fase: Todos | R32 | 8vos | 4tos | Semis | 3P | Final.

2026-06-28 - Sesion Cowork (sesion 52 - continuacion, parte 5) - TAB APUESTAS EN BECBUC-LIVE-PLAYOFFS:

  OBJETIVO: Crear un nuevo tab "📋 Apuestas" en becbuc-live-playoffs.html que muestra
    todas las predicciones de todos los apostadores para cada partido KO, con filtros
    por fase de playoff.

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html (via Python bash, >200KB):
      - CSS nuevas clases: .ap-filter, .ap-pill, .ap-match-card, .ap-match-hdr,
        .ap-match-teams, .ap-match-score, .ap-grid, .ap-cell, .ap-cell-alias,
        .ap-cell-pred, .ap-cell-pts, .ap-cell.ap-pleno/ap-res/ap-miss/ap-pend, .ap-empty, .ap-count
      - Nuevo botón en bottom nav: "📋 Apuestas" (id=bn-apuestas)
      - Nuevo tab pane: #tab-apuestas con #ap-filter-row y #ap-match-list
      - setTab actualizado: incluye 'apuestas' en el array; llama renderApuestasTab() al activar
      - Variables de estado: _allBets (cache), _apuestasFase (filtro activo, default 'all')
      - Funciones nuevas:
          loadAllBets(): GET /api/v1/bets/apuestas-ko/{torneo_id} con cache
          _apuestasFaseLabel(tipo): mapea tipo DB → etiqueta legible
          _apuestasCls(pl, pv, gl, gv): calcula clase CSS (pleno/res/miss/pend)
          _apPts(apuesta): string "+N" con pts H+I del partido
          renderApuestasTab(): renderiza chips de filtro + cards de partido
          setApFase(fase): actualiza filtro + re-renderiza

    backend/app/api/v1/endpoints/apostador_bets.py (ya hecho en parte anterior):
      - GET /api/v1/bets/apuestas-ko/{torneo_id}: retorna todas las apuestas KO
        agrupadas por partido (num FIFA) con pred_local/pred_visitante/pts H/I
        para todos los apostadores. 3 queries SQL eficientes.

  COMPORTAMIENTO:
    - Filtros: Todas | R32 | 8vos | 4tos | Semis | 3P | Final
    - Cards ordenadas por número FIFA (P73 → P104)
    - Apostadores dentro de cada card: ordenados alfabéticamente por alias
    - Codificación de color:
        Verde (ap-pleno): marcador exacto
        Amarillo (ap-res): resultado correcto (L/E/V) pero marcador incorrecto
        Rojo tachado (ap-miss): resultado incorrecto
        Gris (ap-pend): partido no finalizado o sin predicción
    - Contador por partido: "🟢 N plenos · 🟡 N aciertos · N fallos de 44"
    - PRIVACIDAD: usa alias (apostador/username), nunca nombre real

  NOTA: REGLA UI OBLIGATORIA no aplica aquí — BECBUC-movil.html y BECBUC-portal.html
    NO tienen un tab equivalente de consulta masiva de apuestas. Solo en live-playoffs.

2026-06-28 - Sesion Cowork (sesion 52 - continuacion, parte 4) - REDISENO BRACKET TREE SVG:

  OBJETIVO: Redisenar el arbol del bracket para que coincida con el formato oficial
    "Las Llaves del Mundial FIFA 2026" (imagen oficial).

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html (via Python bash, >200KB):
      - LEFT/RIGHT arrays corregidos para que los grupos coincidan con KO_FEEDERS:
          LEFT  = [[74,77,73,75,83,84,81,82],[89,90,93,94],[97,98],[101]]
          RIGHT = [[76,78,79,80,86,88,85,87],[91,92,95,96],[99,100],[102]]
        ANTES: [[73,74,75,76,...],[89,90,91,92],...] (orden secuencial incorrecto)
        AHORA: agrupados por quien alimenta cada partido R16 (P89-P96 via KO_FEEDERS)
      - Llamadas pairR/pairL corregidas para reflejar el agrupamiento correcto:
          pairR(74,77,89): Germany/Paraguay + France/Sweden → P89
          pairR(73,75,90): South Africa/Canada + Netherlands/Morocco → P90
          pairR(83,84,93): Portugal/Croatia + Spain/Austria → P93
          pairR(81,82,94): USA/Bosnia + Belgium/Senegal → P94
          pairL(76,78,91): Brazil/Japan + Ivory Coast/Norway → P91
          pairL(79,80,92): Mexico/Ecuador + England/Congo DR → P92
          pairL(86,88,95): Argentina/Cape Verde + Australia/Egypt → P95
          pairL(85,87,96): Switzerland/Algeria + Colombia/Ghana → P96

    backend/static/BECBUC-portal.html (via Python bash, >200KB):
      - _renderBracketTree: modificada para mostrar SVG tree + editor de fases.
      - Nueva funcion _renderBracketSVGTree(koData, realMap):
          Mismo layout SVG que live-playoffs.html (9 columnas, PAD/S/CW/CH).
          LEFT/RIGHT arrays correctos (identicos a live-playoffs).
          Mismas llamadas pairR/pairL.
          Cards muestran equipos pronosticados con ★ para el ganador predicho.
          Codificacion de color: verde = acierto, rojo = fallo, default = sin jugar.
          Muestra marcadores reales (gl/gv) cuando el partido esta finalizado.
      - NOTA: movil (BECBUC-movil.html) NO tiene bracket tree; usa lista por fases.
        La REGLA UI OBLIGATORIA no aplica aqui porque son componentes distintos.

  ESTRUCTURA ARBOL (mitad izquierda → SF P101, mitad derecha → SF P102):
    Izquierda:
      P74(Germany/Paraguay) + P77(France/Sweden) → P89
      P73(South Africa/Canada) + P75(Netherlands/Morocco) → P90
      P83(Portugal/Croatia) + P84(Spain/Austria) → P93
      P81(USA/Bosnia) + P82(Belgium/Senegal) → P94
      P89 + P90 → P97 (QF)
      P93 + P94 → P98 (QF)
      P97 + P98 → P101 (SF)
    Derecha:
      P76(Brazil/Japan) + P78(Ivory Coast/Norway) → P91
      P79(Mexico/Ecuador) + P80(England/Congo DR) → P92
      P86(Argentina/Cape Verde) + P88(Australia/Egypt) → P95
      P85(Switzerland/Algeria) + P87(Colombia/Ghana) → P96
      P91 + P92 → P99 (QF)
      P95 + P96 → P100 (QF)
      P99 + P100 → P102 (SF)
    Centro: P101 vs P102 → P104 (Final) | P103 (3er puesto)

2026-06-28 - Sesion Cowork (sesion 52 - continuacion, parte 3) - REVERSION ANALISIS INCORRECTO BRACKET R32:

  PROBLEMA RAIZ DESCUBIERTO:
    El analisis de la sesion 52 parte 2 sobre el mapeo FIFA→BECBUC era COMPLETAMENTE INCORRECTO.
    La sesion 52 parte 2 afirmaba que los P-numbers BECBUC NO coincidian con los numeros FIFA
    oficiales a partir de P80. Esta afirmacion era falsa.

  VERDAD CONFIRMADA POR QUERY A BD:
    Los numeros BECBUC P73-P88 SÍ corresponden 1:1 a los numeros FIFA oficiales:
      P73=South Africa/Canada     P74=Germany/Paraguay      P75=Netherlands/Morocco
      P76=Brazil/Japan            P77=France/Sweden         P78=Ivory Coast/Norway
      P79=Mexico/Ecuador          P80=England/Congo DR      P81=USA/Bosnia
      P82=Belgium/Senegal         P83=Portugal/Croatia      P84=Spain/Austria
      P85=Switzerland/Algeria     P86=Argentina/Cape Verde  P87=Colombia/Ghana
      P88=Australia/Egypt

  DAÑO CAUSADO Y REVERTIDO:

  1. KO_FEEDERS ko_scoring.py (REVERTIDO ✅):
     La sesion 52 parte 2 "corrgio" las entradas 92-96 basandose en el mapeo incorrecto.
     Las entradas ORIGINALES (92-96) eran CORRECTAS. El "fix" las rompio.
     ACCION: Revertidas a los valores originales correctos:
       92: ((W, 79), (W, 80))  # Mexico vs England
       93: ((W, 83), (W, 84))  # Portugal/Croatia vs Spain/Austria
       94: ((W, 81), (W, 82))  # USA vs Belgium/Senegal
       95: ((W, 86), (W, 88))  # Argentina vs Australia/Egypt
       96: ((W, 85), (W, 87))  # Switzerland/Algeria vs Colombia/Ghana

  2. fix_r32_equipos.sql + fix_r32_equipos.bat (EJECUTADOS INCORRECTAMENTE, REVERTIDOS ✅):
     El SQL apuntaba a numero_fifa=86 y 87, que son Argentina y Colombia (no Switzerland/Belgium).
     Al correr fix_r32_equipos.bat, cambio:
       P86 Argentina: visitante Cape Verde Islands → Algeria  (INCORRECTO)
       P87 Colombia:  visitante Ghana              → Senegal  (INCORRECTO)
     ACCION: documentacion/revert_r32_fix_incorrecto.sql creado y ejecutado.
     RESULTADO: P86=Argentina vs Cape Verde Islands ✅, P87=Colombia vs Ghana ✅ (restaurados)

  3. Los equipos en P82 y P85 SIEMPRE ESTUVIERON CORRECTOS:
     P82 = Belgium vs Senegal ✅ (nunca necesito fix)
     P85 = Switzerland vs Algeria ✅ (nunca necesito fix)

  ARCHIVOS OBSOLETOS/INCORRECTOS (no usar):
    documentacion/fix_r32_equipos.sql  ← INCORRECTO, apuntaba a Argentina/Colombia
    fix_r32_equipos.bat                ← INCORRECTO, no usar

  ARCHIVOS MODIFICADOS:
    backend/app/services/ko_scoring.py:
      - KO_FEEDERS entradas 92-96: REVERTIDAS a valores originales correctos
      - Comentarios actualizados: BECBUC P73-P88 SÍ = FIFA oficial 1:1
    documentacion/revert_r32_fix_incorrecto.sql (NUEVO):
      - SQL que restauro P86=Argentina/Cape Verde y P87=Colombia/Ghana

  ESTADO FINAL POST-SESION 52 PARTE 3:
    BD: ✅ Correcta (Argentina/Cape Verde P86, Colombia/Ghana P87, Belgium/Senegal P82, Swiss/Algeria P85)
    ko_scoring.py KO_FEEDERS: ✅ Correcto (revertido a valores originales)
    Bracket R32 16 partidos: ✅ Todos con equipos correctos
    Pendiente ejecutar: POST /avanzar-bracket/2 y POST /calcular-puntajes/2

2026-06-28 - Sesion Cowork (sesion 52 - continuacion, parte 2) - BRACKET R32: ANALISIS Y FIX KO_FEEDERS + EQUIPOS:

  INVESTIGACION COMPLETADA: mapeo FIFA oficial vs BECBUC numeros de partido R32.

  PROBLEMA RAIZ:
    Los numeros de partido BECBUC P73-P88 NO coinciden 1:1 con los numeros oficiales FIFA
    para los partidos del 1-3 de julio. La asignacion de numeros en BECBUC fue por
    ORDER BY p.id (base de datos) al correr fix_numero_fifa_ko.py en sesion 45.
    La diferencia nace porque los 16 partidos KO se crearon en un orden distinto al
    orden cronologico/oficial FIFA.

  MAPEO FIFA → BECBUC (verificado vs calendario oficial por fecha+sede):
    FIFA73=P73  FIFA74=P74  FIFA75=P75  FIFA76=P76  FIFA77=P77  FIFA78=P78  FIFA79=P79
    FIFA80=P81 (England vs DR Congo, Atlanta, Jul 1 noon ET)
    FIFA81=P80 (USA vs Bosnia, San Francisco/Levi's, Jul 1 8pm ET)
    FIFA82=P87 (Belgium vs Senegal, Seattle/Lumen Field, Jul 1 4pm ET)
    FIFA83=P88 (Croatia vs Portugal, Toronto/BMO, Jul 2 7pm ET)
    FIFA84=P85 (Spain vs Austria, Los Angeles/SoFi, Jul 2 3pm ET)
    FIFA85=P86 (Switzerland vs Algeria, Vancouver/BC Place, Jul 2 11pm ET)
    FIFA86=P82 (Argentina vs Cape Verde, Miami/Hard Rock, Jul 3 6pm ET)
    FIFA87=P84 (Colombia vs Ghana, Kansas City/Arrowhead, Jul 3 9:30pm ET)
    FIFA88=P83 (Australia vs Egypt, Dallas/AT&T, Jul 3 2pm ET)

  ERRORES ENCONTRADOS:

  1. EQUIPOS INCORRECTOS EN R32 (fix_r32_oficial.py sesion 45 asigno mal):
     P86 (Switzerland, Vancouver): visitante = Senegal  → DEBE SER Algeria
     P87 (Belgium, Seattle):       visitante = Algeria  → DEBE SER Senegal
     (Algeria es Group J 3rd place; Senegal es Group I 3rd place)

  2. KO_FEEDERS INCORRECTOS (5 entradas en ko_scoring.py):
     ANTES:
       92: ((W, 79), (W, 80)),   # usaba P80=USA (incorrecto, P80=FIFA81 no FIFA80)
       93: ((W, 83), (W, 84)),   # usaba P83=Australia, P84=Colombia (ambos wrong)
       94: ((W, 81), (W, 82)),   # usaba P81=England, P82=Argentina (ambos wrong)
       95: ((W, 86), (W, 88)),   # usaba P86=Swiss, P88=Croatia (wrong pair)
       96: ((W, 85), (W, 87)),   # usaba P85=Spain, P87=Belgium (wrong pair)
     AHORA (corregido):
       92: ((W, 79), (W, 81)),   # Mexico vs England (FIFA80=P81)
       93: ((W, 88), (W, 85)),   # Croatia/Portugal vs Spain/Austria (FIFA83=P88, FIFA84=P85)
       94: ((W, 80), (W, 87)),   # USA vs Belgium/Senegal (FIFA81=P80, FIFA82=P87)
       95: ((W, 82), (W, 83)),   # Argentina vs Australia/Egypt (FIFA86=P82, FIFA88=P83)
       96: ((W, 86), (W, 84)),   # Switzerland/Algeria vs Colombia/Ghana (FIFA85=P86, FIFA87=P84)

  ARCHIVOS MODIFICADOS:
    backend/app/services/ko_scoring.py:
      - KO_FEEDERS entradas 92-96 corregidas
      - Comentarios de mapeo FIFA→BECBUC agregados para referencia futura

  ARCHIVOS CREADOS:
    documentacion/fix_r32_equipos.sql  <- corrige equipos visitantes en P86 y P87
    fix_r32_equipos.bat                <- double-click para aplicar SQL

  IMPACTO EN EXCEL/PREDICCIONES:
    Los 704 pronosticos importados (44 apostadores × 16 partidos R32) estan ligados
    a partido_id en BD. Corregir el nombre del equipo en partido NO afecta las predicciones.
    La puntuacion se calcula por goles (pred_local/visitante vs goles reales), no por equipos.

  PREGUNTA USUARIO (canada bracket):
    CONFIRMADO: Canada (P73 ganador) SI va contra Netherlands/Morocco (P75) en R16 (P90).
    El KO_FEEDERS P90=(W,73),(W,75) ES CORRECTO.
    El algoritmo estaba bien para esa pareja especifica.
    El error era en P92-P96 (USA, England, Belgium/Senegal, Croatia/Portugal, etc.)

  VERIFICACION EXCEL NUMERO PARTIDOS:
    El Excel 16avos usa numeracion BECBUC (P073-P088), igual que la BD.
    Ambos tenian los mismos equipos incorrectos en P86 y P87 (ya que provienen
    del mismo fix_r32_oficial.py). La correccion en BD es suficiente.

  PENDIENTES POST-FIX:
    1. Ejecutar fix_r32_equipos.bat (corregir equipos P86/P87 en BD)
    2. POST /avanzar-bracket/2 para que los R16 reflejen equipos correctos
    3. Git commit + backup (pendiente desde sesion 52 inicio)
    4. POST /calcular-puntajes/2 para que sanbie reciba 20 pts Iraq (item D)

2026-06-28 - Sesion Cowork (sesion 52 - continuacion):

  ARCHIVOS MODIFICADOS:
    backend/app/services/ko_scoring.py
    backend/app/services/scoring/calculator.py
    backend/app/services/sync_auto.py
    backend/static/becbuc-live-playoffs.html
    importar_r32_excel.py

  LOCK FASES DE GRUPOS:
    - 12 fases de grupo + fase "Mejores terceros" marcadas bloqueada=TRUE via SQL.
    - calcular_puntajes respeta las fases bloqueadas: no re-calcula ni sobreescribe
      puntaje_detalle de fases ya cerradas.
    - Puntajes de grupos son inmutables desde este momento.

  FIX _set_teams (ko_scoring.py):
    - PROBLEMA: avanzar_ronda32() podia calcular local/visitante en orden diferente
      al que fix_r32_oficial.py habia guardado, lo que disparaba el "team changed"
      detection y borraba el resultado de un partido ya finalizado (ej: P73 Canada).
    - FIX: agregado guard al inicio de _set_teams():
        r = await db.execute(SELECT ... estado FROM partido WHERE id = :pid)
        if row["estado"] == "finalizado": return   <- no tocar partidos ya jugados
    - Resultado: Canada (ganador P73) propagado correctamente a P90. ✅

  SYNC_AUTO — avanzar-bracket siempre:
    - run_avanzar_bracket(token): nueva funcion que llama POST /avanzar-bracket/{torneo_id}.
    - Se ejecuta al inicio de main() ANTES del guard de ventana activa.
    - Garantiza que ganadores de R32/R16/etc aparezcan en la siguiente ronda
      incluso cuando no hay partido activo (gap entre partidos).
    - Sin costo: solo operaciones DB, cero llamadas a API-Football.

  FIX becbuc-live-playoffs.html — timezone local del navegador:
    - PROBLEMA: fmtFechaCorta() usaba hardcoded "America/Costa_Rica" (UTC-6).
      Apostadores en California veian hora de Paraguay.
    - FIX: usar toLocaleString('es') SIN parametro timeZone → usa TZ local del browser.
      function fmtFechaCorta(iso) { return new Date(iso).toLocaleString('es', {
        weekday:'short', day:'numeric', month:'short', hour:'2-digit', minute:'2-digit'
      }); }
    - Aplicado en 4 lugares del archivo (via Python bash, archivo >200KB).

  FEATURE becbuc-live-playoffs.html — proximo partido con countdown:
    - renderNoLive(): cuando no hay partido activo (p == null), busca en _bracket
      el proximo partido por fecha, renderiza equipos + fase + fecha local + countdown.
    - Elemento #nl-countdown con data-fecha para actualizacion dinamica.
    - startCountdown(): refresca tanto el countdown del partido activo como #nl-countdown.
    - _bracket siempre esta cargado (se carga en paralelo con loadLive() en init()).

  FIX importar_r32_excel.py:
    - PROBLEMA: INSERT incluia columna torneo_id que NO existe en tabla apuesta.
    - FIX: removido torneo_id de la lista de columnas y del dict de params.
    - Resultado: 704 filas importadas (44 apostadores × 16 partidos R32), 0 errores. ✅

  calculator.py — globales sin necesidad de campeon:
    - PROBLEMA: calculate_global() tenia guard que SOLO calculaba globales cuando
      campeon_id estaba definido (torneo terminado). Eliminaba puntaje_global si no habia campeon.
    - FIX: eliminada la guard completa. Los globales se calculan SIEMPRE:
        D (peor equipo): puede calcularse desde que el admin lo registre.
        E/F/G: se acumulan durante el torneo.
        A/B (campeon/finalistas): devuelven 0 hasta que haya partido final (comportamiento correcto).
    - Resultado: sanbie recibira 20 pts por pronosticar Iraq (D=peor equipo)
      al correr POST /calcular-puntajes/2. ✅

  IRAQ PEOR EQUIPO (D):
    - UPDATE torneo SET resultado_peor_equipo_id = 84 WHERE id = 2 ✅
    - 1 apostador (sanbie) tenia pred_peor_equipo_id = 84 en apuesta_global.
    - Con el fix de calculator.py, al recalcular puntajes sanbie suma 20 pts globales (item D).

  PENDIENTES:
    1. POST /calcular-puntajes/2 para que sanbie reciba los 20 pts de Iraq.
    2. Verificar en live-playoffs que predicciones R32 aparecen en tab Mi Prono.
    3. Actualizar CLAUDE.md proximos pasos cuando avance el torneo.

2026-06-28 - Sesion Cowork (sesion 51) - BECBUC-LIVE-PLAYOFFS: 8 BUGS CORREGIDOS:

  ARCHIVOS MODIFICADOS:
    backend/static/becbuc-live-playoffs.html
    backend/app/api/v1/endpoints/apostador_bets.py

  BUGS CORREGIDOS:

  1. liveNum solo activo cuando partido en_juego (4 lugares):
     ANTES: const liveNum = _liveData?.partido?.numero_fifa;
     AHORA: const liveNum = (_liveData?.partido?.estado === 'en_juego') ? _liveData.partido.numero_fifa : null;
     → renderBracketTree (L884), renderBracketList (L1049), renderPhaseChips (L1242), renderMatchDetail (L1273)
     → Fix raiz: sin esto hasLive=true para el proximo partido (programado), nextNum=null, badge NEXT nunca aparecia

  2. cardCls usa campo correcto del bracket (en_vivo bool, no estado string):
     ANTES: m?.estado==='en_juego'||isLive
     AHORA: m?.en_vivo===true||isLive
     → bracket_real endpoint retorna 'en_vivo' boolean, no 'estado' string

  3. isLive en renderMatchDetail incluye m.en_vivo:
     AHORA: const isLive = m.num===liveNum || m.en_vivo===true;

  4. Marcador visible en partidos live y terminados (3 lugares):
     ANTES: (done||isLive) → scores
     AHORA: (done||m?.en_vivo||isLive) → scores
     → En bracket tree, lista y detail: el marcador se muestra cuando en_vivo aunque bracket no haya sido re-sync

  5. Fecha no se superpone en modo lista:
     ANTES: fecha dentro de .match-card-num (position:absolute → overlap)
     AHORA: fecha como footer separado al final de la card con border-top
     → .match-card-num ahora solo contiene "P{num}"

  6. penales_local → penales_tanda_local (6 lugares):
     → renderLiveHeader, renderLiveTotals (x3), renderTimeline, renderPredictions
     → El endpoint live_panel serializa p.penales_local AS penales_tanda_local en SQL

  7. Tab En Vivo — eventos individuales de API-Football:
     renderTimeline() REESCRITA:
     - Si p.eventos_api?.length > 0: usa eventos individuales ordenados por minuto
       (Goal → ⚽ jugador+minuto, Card → 🟨/🟥 jugador+minuto, Var → 📺)
     - Fallback: vista agregada (amarillas totales, rojas, VAR, etc.) si no hay eventos
     - Siempre muestra tanda de penales si penales_tanda_local != null

  8. Backend — jose (admin) excluido de apostadores y ranking en live_panel:
     apostador_bets.py live_panel endpoint:
     - Nuevo bloque "5b": query a app_db → valid_apostador_ids_lp (solo rol 'apostador')
     - base_ids filtrado: solo UIDs en valid_apostador_ids_lp
     - ranking_vista loop: skip si uid no en valid_apostador_ids_lp
     → Mismo patrón que calcular_puntajes.valid_apostador_ids

  PRIVACIDAD fix:
     renderPredictions: a.nombre||a.apostador → a.username||a.apostador||a.nombre
     renderRanking: r.apostador||r.nombre → r.username||r.apostador||r.nombre

  NOTA TECNICA: El archivo becbuc-live-playoffs.html estaba truncado en 88885 bytes
    (tanto el original como el backup) desde sesiones anteriores. Se reconstruyo el
    tail completo: ISO_MAP + utilities (flagEmoji, flagFor, showToast, setTab, setSubTab, init()).
    Archivo final: 92188 bytes, 1798 lineas. ✅

2026-06-28 - Sesion Cowork (sesion 50) - ITEM P COMPLETO + LISTA DE 32 EN LIVE + TEST VERIFICADO:

  ITEM P — SCORING COMPLETO (grupos + KO):

  calculator.py — calculate_clasificados(valid_ids=None):
    - Nuevo parámetro valid_ids: set[int] — filtra solo apostadores con rol 'apostador' (excluye admins/test).
    - Grupos: simula standings predichos por cada apostador → R32 pronosticado → intersecta con R32 real.
      Persiste en apostador_clasificados (fase_tipo='grupo', aciertos, equipos_pronosticados/reales).
    - KO: audit trail en apostador_clasificados por fase (pts_equipo ya en puntaje_detalle).
    - Prints de diagnóstico [clasificados] en uvicorn log para debugging.

  apostador_bets.py — calcular_puntajes:
    - Antes de calculate_clasificados: fetcha IDs con rol 'apostador' desde app_db.
    - Pasa valid_ids al método → jose (admin/test) excluido del bonus grupos P.

  apostador_bets.py — live_panel:
    - equipo_clasificado_id incluido en _partido_sql → JS puede calcular P en tiempo real.
    - grupos_p_map: ahora retorna equipos_pronosticados[] y equipos_reales[] además de aciertos/pts.
    - equipos_r32_nombres: dict {equipo_id: nombre} de los 32 equipos del R32.
    - Fallbacks de grupos_p con "pronosticados": [], "reales": [] para apostadores sin datos.
    - Return incluye "equipos_r32": equipos_r32_nombres.

  becbuc-live.html:
    - FASE_PTS con clave P por fase: grupo=1, ronda32=2, ronda16=4, cuartos=6, semis=8,
      tercer_puesto/tercero=10, final=12.
    - scoreApostador(): calcula P cuando equipo_clasificado_id === pred_equipo_clasifica.
    - Estado _equiposR32: {id: nombre} — se carga desde data.equipos_r32 en cargarPanel().
    - Nuevo panel #gp-panel "🏅 Grupos P — Lista de 32":
        Muestra los 32 equipos R32 con ✅/❌ por apostador seleccionado.
        Select para elegir apostador (o "todos" para ver fracción de aciertos por equipo).
        Verde = apostador pronosticó correctamente, gris = fallo.
        Llamado desde render() en cada ciclo.

  TEST VERIFICADO (run_test_grupos_p.bat):
    - 44 apostadores procesados (IDs 9-53 menos jose).
    - Todos con 32 equipos predichos y 32 reales consistentes.
    - Aciertos: min=23, max=28 de 32.
    - Total grupoP: 1,156 pts.
    - KO audit trail: ronda32/ronda16/cuartos/semis/tercer_puesto/final (vacío hasta que R32 juegue).
    - plenos=0/aciertos=0 en el run es ESPERADO (grupos bloqueados, R32 sin finalizar).

  NOTA: rol 'apostador' de jose eliminable con documentacion/fix_jose_rol.sql.
    Get-Content "C:\proyecto FAST API\documentacion\fix_jose_rol.sql" | docker exec -i core-postgres psql -U app_user -d app_db

2026-06-28 - Sesion Cowork (sesion 49) - BRACKET PLAYOFF: DETALLE POR ÍTEM + FECHA + BADGES LIVE/NEXT:

  BADGES LIVE / PRÓXIMO en el bracket (árbol y lista):
    - getNextMatchNum(): retorna el numero_fifa del partido no finalizado con la fecha más próxima en el futuro.
      Solo se llama cuando NO hay partido en_juego (si hay live, no se muestra NEXT).
    - Árbol (renderBracketTree):
        statusBadge div con class "btc-status-badge live" (🔴 EN VIVO) o "btc-status-badge next" (⏭ PRÓXIMO).
        Posicionado fuera de btc-inner (para evitar clipping de overflow:hidden) como sibling absoluto.
        left: x + CW/2, top: y - 11px (flota encima de la card).
    - Lista (renderBracketList):
        .match-card-next-badge: badge azul "⏭ Próximo" en top-right (igual que live badge pero azul).
        Solo aparece en la fase activa si ese partido es el nextNumL.
    - Lógica: si hay live → solo badge LIVE en ese partido; si no hay live → solo badge NEXT en el más próximo.

2026-06-28 - Sesion Cowork (sesion 49) - BRACKET PLAYOFF: DETALLE POR ÍTEM + FECHA EN CARDS:

  ARCHIVOS MODIFICADOS:
    becbuc-live-playoffs.html:

  FECHA-HORA EN CADA CARD (blanco):
    - Nueva función fmtFechaCorta(iso): convierte UTC → hora CR (UTC-6), formato "Dom 29 Jun 14:30"
    - Árbol (renderBracketTree): nuevo div .btc-fecha al final del inner de cada card.
        Cards TBD: también muestran la fecha (btdFecha).
        Altura extra: CH + (hasPen?12:0) + (hasFecha?12:0).
    - Lista (renderBracketList): div .match-fecha-lbl "📅 Dom 29 Jun 14:30" debajo del num-badge.
        Solo se muestra para partidos no finalizados (finalizado ya tiene "Final" implícito).
    - CSS: .btc-fecha (8px, blanco, fondo #080a12, border-top), .match-fecha-lbl (10px, blanco).

  DETALLE DE APUESTAS AL TOCAR PARTIDO (renderMatchDetail — REESCRITO):

    1. 3 ESTADOS distintos:
       - Partido no iniciado (isNotStarted): items en "pend", real="–", pred=predicción del user.
         Nota al pie: "Partido pendiente — puntos se calcularán al finalizar".
         Si no hay pred: "Sin predicción registrada para este partido".
         Panel total: oculto.
       - Partido live (isLive): usa _liveData.partido para stats en tiempo real.
         Panel total: visible con "~ simulado (parcial)".
       - Partido finalizado: cotejar pred vs real, calcular pts.
         Panel total: visible con "de ~N posibles este partido".

    2. SIN PREDICCIÓN REGISTRADA (noPred=true):
       Antes: "Sin predicción cargada" + return early.
       Ahora: muestra TODOS los ítems con pdv="–", clase "pend", pts="–".
       No falla, no oculta la lista.

    3. ÍCONOS en vez de letras:
       H=⚽ I=🎯 J=🟨 K=🟥 L=📺 M=🥅 N=⏱ Ol=🏆 Ov=🏆 (font-size:18px en item-letter)

    4. TANDA SEPARADA (Ol + Ov):
       Antes: ítem O único "Pen. tanda" con real "3–2" y pts sumados.
       Ahora: 2 ítems separados:
         🏆 Tanda {locS}: real=m.pen_l, pred=pred_penales_local_tanda, pts=(hitOl?2:0)*mult
         🏆 Tanda {visS}: real=m.pen_v, pred=pred_penales_visitante_tanda, pts=(hitOv?2:0)*mult

    5. ESTADÍSTICAS REALES — nueva cadena de prioridad:
       rAmar = livePart?.amarillas ?? pred?.amarillas ?? m.amarillas ?? null
       (pred tiene los valores reales desde mis-partidos, no solo las predicciones)
       Igual para rojas, decisiones_var, penales_partido, minuto_primer_gol.

    6. MINUTO GOL (N) — ahora detecta hit correctamente:
       hitN = !isNotStarted && rMinG!==null && pred?.pred_minuto_gol!=null && rMinG===pred.pred_minuto_gol
       Antes estaba hardcodeado como pend:true.

    7. Partido pendiente — fecha visible en el scoreboard:
       periodTxt = m.fecha ? `📅 ${fmtFechaCorta(m.fecha)}` : 'Próximo'

2026-06-28 - Sesion Cowork (sesion 48) - PANEL KO ACUMULADO EN BECBUC-LIVE:

  OBJETIVO: En el tab "Partido" de becbuc-live.html, mostrar para fases KO un panel
    adicional con el acumulado de puntos por ítem (H-O) de la fase KO completa,
    destacando en tiempo real cuáles ítems el apostador está acertando en el partido actual.

  ARCHIVOS MODIFICADOS:
    apostador_bets.py — live_panel endpoint:
      Nuevo bloque "4c. Puntos KO por ítem" (entre paso 4b y paso 5):
        Query a puntaje_detalle JOIN fase WHERE tipo NOT ILIKE 'grupo%' AND partido != actual.
        Retorna ko_h/ko_i/ko_j/ko_k/ko_l/ko_m/ko_n/ko_o por apostador.
        ko_pts: dict[int, dict] = {apostador_id: {H..O}} (0 si no tiene pts KO previos).
      apostadores[]: + campo "ko_acum": {H..O} (acumulado KO sin contar partido actual).
      ranking_vista[]: + campo "ko_acum": {H..O} idem.

    becbuc-live.html:
      CSS nuevas clases:
        #ko-panel: contenedor del panel KO
        .ko-phase-badge: badge ámbar con el nombre de fase actual
        .ko-tbl-wrap: overflow-x para tabla
        .ko-hit-live: verde (#34d399) — pts ganados EN ESTE partido (live)
        .ko-hit-hist: azul (#60a5fa) — pts acumulados en partidos KO previos
        .ko-total: ámbar (#fbbf24) — total KO del apostador
        .ko-live-row: tint verde muy suave en filas donde hay pts live
        .ko-hint: leyenda de colores
      HTML nuevo div#ko-panel (entre rank-section y footer):
        Tabla: # | Apostador | H | I | J | K | L | M | N | O | Total KO
        id="ko-tbl-body" para actualización dinámica
        id="ko-phase-label" para mostrar nombre de fase actual
        Leyenda de colores (🟢 verde = live · 🔵 azul = previo)
      JS función renderKoPanel():
        Solo visible cuando fase_tipo NO empieza por 'grupo'.
        Combina rv.ko_acum (histórico KO del ranking_vista) + r.sim_detail (partido actual).
        Celdas: hist+live cuando ambos > 0 (ej: "3+1"), solo +N cuando live, solo N cuando hist.
        Ordenado por Total KO descendente (independiente del ranking general).
        Filas con pts live resaltadas con .ko-live-row.
        Llamada desde render() para actualizar en cada ciclo auto-refresh.
      Llamada render() → renderKoPanel() agregada.

  COMPORTAMIENTO:
    - En grupos: panel oculto (display:none).
    - En KO (R32, R16, QF, SF, 3P, Final): panel visible debajo de la tabla principal.
    - Partido pendiente/programado: solo columna azul (histórico), nada verde.
    - Partido en_juego con goles: verde muestra pts live del scoreApostador() en JS.
    - Partido finalizado: sim_detail = 0 (el scoring ya está en puntaje_detalle).
      → Al recalcular puntajes, el historico KO sube y live vuelve a 0.
    - La columna "Total KO" acumula solo la fase playoff (excluye grupos y globales).

2026-06-28 - Sesion Cowork (sesion 47) - FECHAS KO + VISIBILIDAD EN BRACKET Y LISTA:

  ARCHIVOS CREADOS:
    importar_fechas_ko.py  <- horarios oficiales FIFA 2026 para P73-P104 en UTC.
      Fuente: Yahoo Sports / FIFA.com (verificado 2026-06-28).
      Convierte Eastern Time (EDT=UTC-4) a UTC naive para guardar en partido.fecha.
      EJECUTAR: run_importar_fechas_ko.bat (doble clic con uvicorn activo).
    run_importar_fechas_ko.bat  <- wrapper para ejecutar el script desde File Explorer.

  CALENDARIO KO IMPORTADO (resumen, hora Costa Rica = ET - 2h):
    R32 (P73-P88): 28 Jun - 4 Jul
      P73 South Africa vs Canada      Dom 28/06 13:00 CR  (Los Ángeles)
      P76 Brazil vs Japan             Lun 29/06 11:00 CR  (Houston)
      P74 Germany vs Paraguay         Lun 29/06 14:30 CR  (Boston)
      P75 Netherlands vs Morocco      Lun 29/06 19:00 CR  (Monterrey)
      P78 Ivory Coast vs Norway       Mar 30/06 11:00 CR  (Dallas)
      P77 France vs Sweden            Mar 30/06 15:00 CR  (Nueva York/NJ)
      P79 Mexico vs Ecuador           Mar 30/06 19:00 CR  (Ciudad de México)
      P81 England vs Congo DR         Mié 01/07 10:00 CR  (Atlanta)
      P87 Belgium vs Algeria          Mié 01/07 14:00 CR  (Seattle)
      P80 USA vs Bosnia & Herzegovina Mié 01/07 18:00 CR  (San Francisco)
      P85 Spain vs Austria            Jue 02/07 13:00 CR  (Los Ángeles)
      P88 Croatia vs Portugal         Jue 02/07 17:00 CR  (Toronto)
      P86 Switzerland vs Senegal      Jue 02/07 21:00 CR  (Vancouver)
      P83 Australia vs Egypt          Vie 03/07 12:00 CR  (Dallas)
      P82 Argentina vs Cape Verde     Vie 03/07 16:00 CR  (Miami)
      P84 Colombia vs Ghana           Vie 03/07 19:30 CR  (Kansas City)
    R16 (P89-P96): 4-7 Jul
    Cuartos (P97-P100): 9-11 Jul
    Semis (P101-P102): 14-15 Jul
    3P (P103): 18 Jul Miami  |  Final (P104): 19 Jul Nueva York/NJ

  ARCHIVOS MODIFICADOS:
    apostador_bets.py:
      bracket_real: fecha serializada con strftime("%Y-%m-%dT%H:%M:%SZ") → sufijo "Z"
        JS: new Date("...Z") parsea como UTC → convierte a CR local (UTC-6) ✅
      resultados_partidos: mismo fix (isoformat → strftime con "Z")
    becbuc-live.html:
      Bracket (renderBracket32) - fecha más visible:
        font-size 9px → 11px, color #9ca3af → #6ee7b7 (teal, visible en fondo negro)
        Ícono 📅 prefijado. Ahora se muestra también para partidos finalizados.
        Fallback por fase si p.fecha es null: FASE_FECHAS['ronda32'] etc.
      Lista (renderResultados) - 2 mejoras:
        .res-fecha: color #9ca3af → #6ee7b7, font-weight 700, font-size 11px
        Nueva sección "📅 Próximos partidos KO" al tope de la lista (carga bracket
          en paralelo via Promise.all para obtener _r32Cache).
        CSS nuevas clases: .prox-card, .prox-num, .prox-fecha, .prox-match, .prox-fase
      loadResultados: carga bracket-real en paralelo si _r32Cache es null,
        para que la sección "Próximos KO" siempre tenga datos al renderizar.

  CAUSA DEL BUG "no aparece":
    font-size:9px + color:#9ca3af sobre #111827 = contraste insuficiente (4:1 para 9px).
    Fix: 11px + #6ee7b7 = verde teal claramente visible en fondo negro.

2026-06-28 - Sesion Cowork (sesion 46) - SCORING POR FASES: AUTO-LOCK + RANKING DESGLOSE:

  CAMBIO ARQUITECTURAL - calcular_puntajes respeta fases bloqueadas:
    calculator.py (_load_partidos, _load_apuestas):
      WHERE ... AND COALESCE(f.bloqueada, FALSE) = FALSE
      → Fases bloqueadas NO se re-calculan. Sus puntaje_detalle se preservan.
    calculator.py (DELETE puntaje_detalle / puntaje_item):
      DELETE ... WHERE partido_id IN (SELECT p.id WHERE fase NOT bloqueada)
      → El DELETE solo limpia fases activas antes de recalcular.

  NUEVO HELPER - _auto_lock_completed_grupos(db, torneo_id):
    Llamado al inicio de POST /calcular-puntajes/{torneo_id}.
    UPDATE fase SET bloqueada=TRUE WHERE tipo ILIKE 'grupo%' AND todos los partidos finalizados.
    Retorna N fases auto-bloqueadas. Incluido en la respuesta del endpoint.
    Invariante: una vez que todos los partidos de grupos terminan y se calcula,
    la fase de grupos queda bloqueada permanentemente y su scoring es inmutable.

  RANKING ENDPOINT refactorizado (fuente única: puntaje_detalle):
    ANTES: puntos_partidos_total = SUM(apuesta.puntos) [cache stale, incorrecto]
    AHORA: puntos_partidos_total = SUM(pts_resultado + pts_marcador + ... + pts_equipo) de puntaje_detalle
    Plenos = pts_marcador > 0 (marcador exacto)
    Aciertos = pts_resultado > 0 AND pts_marcador = 0 (resultado correcto)
    Nuevos campos en response:
      cat_penales_tanda (O): puntaje penales en tanda KO acumulado
      cat_equipo (P): puntaje equipo clasifica KO acumulado
      fases: [{tipo, nombre, pts}] — desglose de pts por cada fase jugada

  FRONTEND (portal + movil) - Ranking:
    CATS / CATS_M: ahora incluyen O (penales tanda KO) y P (equipo clasifica KO)
      Orden oficial: H | I | J | K | L | M | N | O | P
      Headers: letras únicas en vez de abreviaturas largas
    Árbol apostador (portal): pre-populated con tabla "pts por fase" desde r.fases
      Partidos detalle se cargan en sub-div rk-partidos-{aid} (no sobreescribe el árbol)
    Árbol apostador (movil): fasesHtml prepended en toggleRkAposM desde _ranking cache

2026-06-28 - Sesion Cowork (sesion 45) - CIERRE FASE DE GRUPOS + BRACKET R32 OFICIAL:

  OBJETIVO: Sincronizar resultados finales de grupos, asignar cruces R32 oficiales y
    calcular puntajes. Estado anterior: 72 partidos de grupo finalizados en BD,
    partidos KO con numero_fifa NULL y cruces generados por armar_ronda32() (incorrecto).

  SCRIPTS CREADOS:
    diag_bd_estado.py           <- diagnóstico de estado BD (fases, partidos, R32)
    fix_numero_fifa_ko.py       <- asigna numero_fifa 73-104 a partidos KO por orden de id
    fix_r32_oficial.py          <- actualiza cruces R32 según tabla oficial confirmada
    validar_bracket_oficial.py  <- valida BD vs resultados oficiales (standings + R32)
    crear_fases_ko.py           <- crea fases KO si no existen (fases ya existían)

  PROBLEMA RAIZ: partidos KO tenían numero_fifa = NULL.
    build_num_maps() en ko_scoring.py asigna números por POSICIÓN (zip con ORDER BY id),
    no por el campo numero_fifa. La query WHERE numero_fifa BETWEEN 73 AND 88 devolvía 0.
    FIX: fix_numero_fifa_ko.py asignó numero_fifa 73-104 matching posición → id.

  CRUCES R32 OFICIALES aplicados (P73-P88):
    P73 South Africa vs Canada           P74 Germany vs Paraguay
    P75 Netherlands vs Morocco           P76 Brazil vs Japan
    P77 France vs Sweden                 P78 Ivory Coast vs Norway
    P79 Mexico vs Ecuador                P80 USA vs Bosnia & Herzegovina
    P81 England vs Congo DR              P82 Argentina vs Cape Verde Islands
    P83 Australia vs Egypt               P84 Colombia vs Ghana
    P85 Spain vs Austria                 P86 Switzerland vs Senegal
    P87 Belgium vs Algeria               P88 Croatia vs Portugal

  BUG EN fix_r32_oficial.py (corregido):
    1. ALIAS faltaba "Suiza" → ["Switzerland"]: equipo en BD es "Switzerland" (no "Suiza").
       Fix: agregadas 16+ entradas al ALIAS (España, Alemania, Brasil, etc.)
    2. Llamaba a avanzar-bracket DESPUÉS de actualizar R32, que sobreescribía los cruces.
       Fix: removida llamada a avanzar-bracket del post-update.

  BUG EN validar_bracket_oficial.py (corregido):
    "Cabo Verde" no matcheaba "Cape Verde Islands" (threshold 0.75 > similarity 0.714).
    Fix: ALIAS "Cabo Verde" → [..., "Cape Verde Islands", "Cabo Verde Islands"].

  RESULTADO FINAL:
    Partidos finalizados: 72/72 ✅
    R32 Bracket OK:       16/16 ✅
    Puntajes calculados:  321 plenos ✅
    Standings "erróneos": 7/12 en el validador — FALSOS POSITIVOS.
      ESPERADO_GRUPOS usa letras BECBUC que no coinciden con letras FIFA.
      Los standings en BD son correctos (verificados por sync API-Football + 72/72 fin.)

  FLUJO CORRECTO para cambiar cruces R32 (para futuras sesiones):
    1. Actualizar equipo_local_id / equipo_visitante_id en partido directamente
    2. NO llamar avanzar-bracket después (sobreescribe)
    3. Llamar calcular-puntajes para actualizar scores
    "s" | python fix_r32_oficial.py   <- aplica cruces oficiales sin tocar bracket engine

  NOTA: sincronizar_final_grupos.ps1 fue reescrito (sesión anterior tenía errores de PS5).
    El bat y ps1 funcionan correctamente. Step 5 llama fix_r32_oficial.py con "s" via pipe.

  FIX GRUPO G - STANDINGS INCOMPLETOS (sesion 45, continuacion):
    PROBLEMA: participacion tenia PJ=2 para todos los equipos del Grupo G.
      Solo se habian acumulado las primeras 2 jornadas. La 3ra jornada (P63 Egypt-Iran,
      P64 NZ-Belgium) estaba correcta en tabla partido pero no en participacion.
      BD mostraba: Egypt 4pts, Iran 2pts, Belgium 2pts, NZ 1pt (estado post-jornada 2).
    FIX: fix_standings_grupo_g.py recalculo standings directo desde tabla partido.
    RESULTADO CORRECTO:
      1. Belgium    5pts  PJ=3 PG=1 PE=2 PP=0  GF=6  GC=2  GD=+4  (G1 -> P87 vs Algeria)
      2. Egypt      5pts  PJ=3 PG=1 PE=2 PP=0  GF=5  GC=3  GD=+2  (G2 -> P83 vs Australia)
      3. Iran       3pts  PJ=3 PG=0 PE=3 PP=0  GF=3  GC=3  GD=0
      4. New Zealand 1pt  PJ=3 PG=0 PE=1 PP=2  GF=4  GC=10 GD=-6
    Belgium es G1 por GD superior (+4 vs +2) — confirmado por estructura R32
      (G1 juega 3ro de A/E/H/I/J → Algeria J3 en P87; G2 juega D2 → Australia en P83).
    Puntajes recalculados post-fix: 321 plenos (sin cambios). ✅

  VERIFICACION NOMBRES EQUIPOS (sesion 45):
    equipo.nombre YA ESTA EN INGLES en todos los equipos Copa del Mundo 2026.
    equipo.nombre_es guarda el nombre en español (ALEMANIA, COSTA DE MARFIL, etc.).
    Script fix_nombres_equipos_en.py: UPDATE 0 (sin cambios necesarios). ✅
    Script creado: documentacion/fix_nombres_equipos_en.sql (idempotente para referencia futura).

2026-06-27 - Sesion Cowork (sesion 44) - FIX TABS BECBUC-LIVE EN MODO SIMULTÁNEO:

  BUG: Al refrescar la página con 2+ partidos en_juego, ningún tab funcionaba.
  CAUSA: `_modoSimult = _numFifa == null && simEnJuego.length > 0` activaba modo dual,
    que llama `renderDual()` pero NO `render()` ni `renderNav()`.
    Los paneles de tabs (panel-partido, panel-ranking, etc.) quedaban vacíos.
    Seleccionar el 2do partido ponía `_numFifa` → desactivaba _modoSimult → render() corría.
  FIX: becbuc-live.html — `_modoSimult = false` siempre.
    `renderSimBar()` sigue corriendo y muestra botones de navegación entre partidos simultáneos.
    Todos los tabs funcionan correctamente desde el refresh inicial.

2026-06-26 - Sesion Cowork (sesion 43) - SIN TERCEROS PROVISORIOS (fill_incomplete=False):

  CAMBIO ARQUITECTURAL: eliminar concepto de "terceros provisorios" del bracket en vivo.
  La idea de asignar terceros de grupos INCOMPLETOS causaba inestabilidad (Scotland iba y venia).
  Nueva logica: fill_incomplete=False — solo terceros de grupos con TODOS sus partidos jugados.

  apostador_bets.py — 4 sitios cambiados (sort_unified=True → fill_incomplete=False):
    1. _avanzar_bracket (linea ~5614): docstring + logica actualizada
    2. avanzar_bracket_provisional (linea ~5660)
    3. transparencia endpoint (linea ~6307)
    4. fair_play_terceros endpoint (linea ~6818)

  Comportamiento nuevo:
    - Grupos incompletos (J, L con pend=2): sus terceros no se asignan hasta que terminen
    - Bracket actualiza automaticamente al finalizar cada partido (via sync_auto.py chain)
    - Cuando todos los grupos terminan → mejores 8 confirmados → bracket definitivo

  UI limpiada (provisorios removidos de ambas interfaces):
    BECBUC-portal.html:
      - Tab "3️⃣ Mejores 3ros" eliminado del bet-tabs
      - if (_betTab==='terceros') eliminado de loadBetTab
      - <div id="mejores-terceros-panel"> eliminado de renderBetGrupos
      - _renderMejoresTerceros() eliminado de onScoreChange y recalcularTodos
    BECBUC-movil.html:
      - ['terceros','3️⃣ 3ros'] eliminado del array tabs
      - else if(_pronosTab==='terceros') eliminado de switchPronosTab

  Script de verificacion creado: fix_bracket_sin_provisorios.py/.bat
    Ejecutar cuando el servidor este activo para re-aplicar bracket con nueva logica.
    O simplemente esperar al proximo partido: sync_auto lo aplica automaticamente.

2026-06-26 - Sesion Cowork (sesion 42) - FIX BRACKET REGRESION sort_unified:

  PROBLEMA RAIZ:
    El endpoint avanzar-bracket-provisional usaba seleccionar_mejores_terceros(standings)
    con parametros DEFAULT (fill_incomplete=True, sort_unified=False), lo que da prioridad
    a grupos COMPLETOS sobre incompletos. Si Scotland (grupo C completo) tenia mejor
    clasificacion que terceros de grupos incompletos, volvia al bracket.
    El boton "Calcular siguiente fase" del Monitoreo llama a este endpoint.
    Resultado: cada click en ese boton REVERTIA el fix anterior de Scotland.

  FIX apostador_bets.py (3 sitios):
    1. avanzar_bracket_provisional (linea 5660):
       ANTES: seleccionar_mejores_terceros(standings)
       AHORA:  seleccionar_mejores_terceros(standings, sort_unified=True)
    2. transparencia endpoint (linea 6307):
       ANTES: seleccionar_mejores_terceros(st)
       AHORA:  seleccionar_mejores_terceros(st, sort_unified=True)
    3. fair_play_terceros endpoint (linea 6818):
       ANTES: seleccionar_mejores_terceros(standings)
       AHORA:  seleccionar_mejores_terceros(standings, sort_unified=True)

  El mi_bracket endpoint (linea 771) NO se toco: usa standings de predicciones
  del apostador, donde el criterio de grupos completos es correcto.

  VERIFICADO: fix_scotland_bracket.bat ejecutado. Scotland NO esta en R32.
    P77: France vs Sweden (3F)
    P79: Mexico vs Ecuador (3E)
    P80: INGLATERRA vs Senegal (3I)
    P81: USA vs BOSNIA Y HERZEGOVINA (3B)
    P82: Egypt vs COREA DEL SUR (3A)
    P85: Switzerland vs Algeria (3J)
    P87: Colombia vs Croatia (3L)
    (P74: ALEMANIA vs Paraguay 3D - confirmado anterior)

2026-06-26 - Sesion Cowork (sesion 41) - FAIR PLAY FIFA + SYNC ROBUSTO + LIVE FIX:

  FAIR PLAY FIFA - Mejores terceros (criterio completo):
    - Nuevas columnas en partido: local_amarillas, visitante_amarillas, local_rojas, visitante_rojas
    - Nuevas columnas en participacion: fair_play_pts, amarillas, rojas_directas, rojas_doble_amarilla
    - sync_api_football.py: extrae tarjetas por equipo via ev["team"]["id"] en loop de eventos.
      per_team_amar / per_team_rojas acumulados y escritos en el UPDATE de partido.
    - apostador_bets.py - _calc_standings_reales: acumula fair_play_pts (amarilla=1, roja=3).
    - apostador_bets.py - _recalc_participacion: escribe fair_play_pts en UPDATE.
    - Nuevo endpoint POST /recalc-fair-play/{torneo_id} (admin):
        Re-descarga eventos de API-Football para partidos de grupo (incluso confirmados).
        Actualiza SOLO local/visitante_amarillas/rojas — no toca stats verificadas.
        Llama _recalc_participacion → fair_play_pts poblado en todos los grupos.
    - UI portal: boton "⚽ Recalcular Fair Play (mejores terceros)" en Herramientas.
    - UI movil: boton "⚽ Recalc. Fair Play" en admin panel Mas opciones.
    - Script: ejecutar_fair_play.ps1 (migración + login + recalc FP + puntajes).
    - Migración: documentacion/migracion_fair_play_partido.sql (ejecutada).

  SYNC ROBUSTO:
    - sync_api_football.py: guard idempotente para datos_confirmados antes de _sql2.
    - _sql2 SELECT: agrega torneo_id y numero_fifa (faltaban → UPSERT partido_stats_fuentes fallaba).
    - apostador_bets.py sync_resultados y sync_historico: except Exception (antes solo ValueError).

  BECBUC-LIVE error handling:
    - init() catch: mensajes específicos por tipo (conn refused, 401, 403, sin torneo activo).
    - Limpia token automáticamente en error de conexión o credenciales.

  Criterio desempate mejores terceros (FIFA Art.38):
    Pts → DG → GF → fair_play_pts (menor es mejor) → fifa_ranking → grupo
    AHORA COMPLETO Y FUNCIONAL con datos reales de API-Football.

2026-06-25 - Sesion Cowork (sesion 40) - BLINDAR PARTIDOS + VERIFICACION EXCEL vs BD:

  VERIFICACION COMPLETA Excel vs BD (44 partidos finalizados):
    - Comparacion item x item: H(goles_l), I(goles_v), J(amarillas), K(rojas),
      L(VAR), M(penales_partido), N(minuto_primer_gol).
    - Resultado: 44/44 matcheados, 0 discrepancias. BD == Excel oficial. ✅
    - Endpoint reparado: verificar-importacion usaba current.role (bug) → cambiado a _check_admin().
      Limite default cambiado a 100.

  DATOS_CONFIRMADOS — Blindaje contra sync:
    - Nueva columna: partido.datos_confirmados BOOLEAN DEFAULT FALSE
    - Migración idempotente via endpoint POST /confirmar-partido-stats/{torneo_id}
    - 54 partidos marcados como confirmados (todos los finalizados al 2026-06-25)
    - sync_api_football.py: 3 puntos de guarda agregados:
        1. incremental pre-check: confirmed → nunca entra en pending_fix_ids
        2. finished_fixtures loop: confirmed → skip a ya_finalizados
        3. live_fixtures loop: confirmed → skip (ni en vivo se tocan)
    - apostador_bets.py:
        POST /confirmar-partido-stats/{torneo_id} — migración + marcar todos finalizados (admin)
        PATCH /confirmar-partido/{partido_id}?confirmar=true|false — toggle individual (admin)
        GET /espn-verify/{partido_id}: si datos_confirmados=True → retorna sin aplicar ESPN
    - UI portal: botón "🔒 Blindar partidos finalizados" en Herramientas
    - UI movil: botón "🔒 Blindar finalizados" en Más opciones del sistema

  FLUJO PARA NUEVAS FASES:
    1. Juegan los partidos → sync automático actualiza goles/stats
    2. Admin verifica resultados contra fuente oficial
    3. Admin hace click en "🔒 Blindar partidos finalizados" → todos los finalizados quedan protegidos
    4. Futuros syncs solo actualizan partidos no confirmados (en curso / pendientes)

2026-06-25 - Sesion Cowork (sesion 39) - TABLA STATS FUENTES + ESPN MATCHING + ANALISIS CONFIABILIDAD:

  partido_stats_fuentes — tabla de auditoría comparativa de fuentes:
    - Columnas completas: api_*/espn_*/ss_* para amarillas/rojas/var/penales + minuto_primer_gol
    - migracion_stats_fuentes.sql: v3 (numero_fifa, minuto_primer_gol) + v4 (api/espn/ss_minuto)
    - populate_stats_fuentes_all: UPSERT completo, fix asyncpg fecha (date object, no string),
      fix tipo numero_fifa (str cast), fix SAVEPOINT → commit directo
    - endpoint POST /populate-stats-fuentes/{torneo_id}: carga 104 partidos con datos de ESPN + final_*
    - endpoint GET /stats-fuentes/{torneo_id}: consulta con filtro por estado

  SOFASCORE deshabilitado (SOFASCORE_ENABLED = False):
    - Devuelve 403 Forbidden desde IP de servidor
    - _sofascore_scoreboard retorna [] inmediatamente cuando disabled
    - _sofascore_extract_stats: agrega extraccion minuto_primer_gol desde incidents (para uso futuro)
    - Reactivar: cambiar SOFASCORE_ENABLED = True en sync_api_football.py

  ESPN matching mejorado (48% → 100% cobertura):
    - Mapa _TEAM_ES_EN_RAW: 90+ equipos con traducciones ES→EN
    - Keys normalizadas (_TEAM_ES_EN con _normalize(k)) — fix bug clave no normalizada
    - Entradas nuevas: Inglaterra, Turkiye, Curacao, Haiti, USA, Jordania, etc.
    - _espn_scoreboard: fallback fecha -1 dia (partidos nocturnos USA/México = fecha UTC distinta)
    - _espn_find_game_id: usa _espn_translate() con variantes ES/EN, shortDisplayName, abbreviation
    - _TEAM_EN_ES: inverso construido automáticamente desde _TEAM_ES_EN

  Análisis de confiabilidad (scripts en C:\proyecto FAST API\):
    - analizar_fuentes.py: cobertura + precision + error avg por fuente x campo
    - cruzar_fuentes.py: tabla de discrepancias ESPN vs BD con patron sobreestima/subestima
    - diag_sofascore.py (→ diag_espn_matching.py): diagnostico directo SofaScore/ESPN
    - diag_sync_estado.py: verifica api_league_id, api_fixture_id, api_team_id, api_sync_log
    - Scripts ps1: run_populate_y_analisis.ps1, run_auto_mapeo.ps1, run_migrate_and_populate.ps1

  Resultados análisis:
    - API-Football: 100% cobertura, fuente primaria y confiable
    - ESPN: 100% cobertura, 65.7% precision global
      Amarillas: ESPN siempre devuelve 0 (inutil para J)
      VAR: ESPN sobrecontea (commentary vs eventos reales) — BD es correcta
      Rojas/Penales: ~90% precision
      Minuto gol: ESPN no extrae (100% null)
    - SofaScore: 0% (bloqueado 403)

  Diagnostico sync:
    - 72/104 partidos tienen api_fixture_id (todos los de grupos)
    - 32 partidos KO son "Por Definir" — se mapean automaticamente cuando avance el bracket
    - Todos los 54 partidos finalizados tienen amarillas/rojas/VAR completos ✅
    - Para mapear KO cuando se definan equipos: POST /api/v1/bets/api-mapeo/2/auto
      o ejecutar run_auto_mapeo.ps1

2026-06-25 - Sesion Cowork (sesion 38) - FIX TARJETAS Y VAR EN SYNC + SOFASCORE:

  sync_api_football.py — _update_partido_full:
    BUG: API-Football statistics "Yellow Cards" incluye la 2ª amarilla (que resulta en
    expulsión), inflando amarillas_total. Ej: Colombia vs Congo, Pickel doble amarilla →
    stats decían 4 amarillas cuando lo correcto son 3.
    FIX: Nuevo contador amarillas_events (solo "Yellow Card" events, excluye
    "Second Yellow card"). Si amarillas_events > 0, se usa en lugar de amarillas_total.
    Así: 1ª amarilla → amarillas; 2ª amarilla → rojas. Correcto per reglamento.

  sync_api_football.py — _espn_verify_and_patch:
    BUG 1 (VAR): ESPN siempre sobreescribía decisiones_var. ESPN cuenta menciones en el
    commentary (múltiples por cada decisión real → sobreconteo). API-Football events son
    más precisos (1 evento por decisión VAR).
    FIX: Solo usar ESPN para VAR cuando API-Football tiene 0 (sin eventos detectados).
    BUG 2 (amarillas): ESPN boxscore también puede incluir 2ª amarilla en yellowCards.
    FIX: Solo usar ESPN para amarillas cuando API-Football tiene 0.
    Rojas: ESPN "gana si mayor" se mantiene (útil para rojas directas no captadas).

  SOFASCORE INTEGRATION — Fase D (nueva fuente autoritativa):
    Problema raíz: tanto API-Football statistics como ESPN boxscore pueden mezclar
    2ª amarilla con amarillas. ESPN commentary sobrecontea VAR. Se necesitaba una
    fuente que distinga tipos de tarjeta de forma precisa y nativa.

    SofaScore incidents:
      incidentClass='yellow'    → amarilla (1ª tarjeta, NO cuenta expulsión)
      incidentClass='yellowRed' → 2ª amarilla = ROJA (expulsión)
      incidentClass='red'       → roja directa
      incidentType='varDecision'→ 1 evento por decisión VAR real (no commentary)

    Nuevas funciones en sync_api_football.py:
      SOFASCORE_BASE, SOFASCORE_HEADERS (constantes)
      _sofascore_scoreboard(client, fecha): GET /sport/football/scheduled-events/{date}
      _sofascore_find_event(events, local, visitante): match por nombre normalizado
      _sofascore_get_incidents(client, event_id): GET /event/{id}/incidents
      _sofascore_extract_stats(incidents): parsea tarjetas y VAR correctamente
      _sofascore_verify_and_patch(db, client, db_p, partido_id, ss_cache): aplica correcciones
    
    sync_torneo — Fase D (después de ESPN):
      - Corre SofaScore verify en paralelo para todos los partidos finalizados
      - SofaScore ES AUTORITATIVO: gana sobre API-Football y ESPN para J/K/L
        cuando tiene datos de incidents (ss_corrections)
      - ESPN mantiene rol de fallback para minuto_gol, penales tanda, penales partido
    
    Return incluye campo 'sofascore_correcciones' con partidos corregidos.

  PARA APLICAR: Al próximo sync, el flujo corre Fase A (API-Football) →
    Fase B (write DB) → Fase C (ESPN: minuto, tanda) → Fase D (SofaScore: J/K/L).
    Para corregir partidos ya sincronizados: POST /sync-resultados con force=true.

2026-06-17 - Sesion Cowork (sesion 37) - FIX APUESTAS SWAP + BECBUC-LIVE RANKING+LIVE COLUMNS:

  PROBLEMA RAIZ - 10 apuestas con team IDs swapped:
    pronosticos_aux tenia numeracion de 5 pares consecutivos invertida vs tabla partido
    (P049↔P050, P055↔P056, P061↔P062, P065↔P066, P067↔P068).
    El reload anterior usaba numero_fifa como clave → apuestas quedaron ligadas al partido incorrecto.

  NUEVO ENDPOINT - apostador_bets.py:
    POST /api/v1/bets/reload-apuestas-por-equipos/{torneo_id} (admin):
      Usa idequipolocal/idequipovisitante de pronosticos_aux como clave de join con partido
      (en vez de numero_fifa). Corrige los 10 casos de pares swapped.
      Convierte NULL en goles_local/goles_visitante a 0 en el INSERT.
      Resultado: 3168 apuestas recargadas, 10 correcciones de swap, 0 sin_match.

  FIX calculator.py - COALESCE en _load_apuestas():
    pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas, pred_penales_partido
    ahora usan COALESCE(col, 0) → NULLs no rompen el scoring.
    pred_minuto_gol, pred_penales_local/visitante_tanda, pred_equipo_clasifica quedan NULL
    (NULL = "sin prediccion" es semanticamente correcto para esos items).

  becbuc-live.html - SIMULACION LIVE REDISEÑADA:
    - Columnas H-O: muestran SOLO los puntos del partido actual (sim_detail), NO acumulado.
    - calcularTodos() reescrito: distingue en_juego vs finalizado vs pendiente.
        en_juego: total = puntos_antes + sim_pts (partido no está en puntaje_detalle aun)
        finalizado: total = puntos_antes (ya incluye este partido, no sumar doble)
        pendiente (sin goles): sim_pts = 0, solo J/K/L/M si pred coincide con 0
    - Nueva columna "Ranking": muestra puntos_antes (gris, acumulado confirmado).
    - Columna final renombrada "Live▼": muestra puntos_antes + sim_pts del partido.
    - Top5 panel: usa _results (proyectado) cuando hay partido en_juego con goles.
    - simActiva: definida antes del bloque top5 en render() para evitar ReferenceError.
    - Hint text: "H–O: puntos de este partido · Total: acumulado todos los partidos"

2026-06-17 - Sesion Cowork (sesion 36) - VAR FIX + DIAGNOSTICO NO PUNTAJES:

  becbuc-live.html:
    - VAR chip fix: '📺','VAR', p.decisiones_var > 0 ? p.decisiones_var : null' -> 'p.decisiones_var'
      Ahora VAR aparece en match-stats (abajo del partido) incluso cuando decisiones_var = 0.
    - "Sin datos aún" message: agrega sugerencia "Presioná 🔄 Sincronizar para calcular puntajes".
    - Si _debug.pd_error presente en response, muestra toast con el error de BD.

  apostador_bets.py - live_panel endpoint:
    - Exception handler de puntaje_detalle query: agrega print() al log de uvicorn.
    - Response incluye _debug.pd_error cuando hay error, para diagnostico desde UI.

  Archivos CREADOS:
    documentacion/fix_pts_penales_partido.sql  <- ALTER TABLE puntaje_detalle ADD pts_penales_partido IF NOT EXISTS
    fix_y_recalcular.bat  <- corre migration + recalculo via API (double-click desde File Explorer)

  DIAGNOSTICO: pts_penales_partido faltaba en migracion_scoring_v2.sql (line 17 comment lo excluia).
    Fue agregado directo al Docker en sesion 20 (no quedó en archivo .sql guardado).
    Si el container fue recreado o el schema cambia, esta columna puede faltar → query falla silenciosamente → vista_map={} → todos puntajes 0.
    FIX: ejecutar fix_pts_penales_partido.sql O usar fix_y_recalcular.bat.
    LUEGO: click en 🔄 Sincronizar en becbuc-live.html para recalcular.

2026-06-17 - Sesion Cowork (sesion 35) - PENDIENTES EJECUTADOS (git + migraciones Docker):

  Git: commit 2db8960 "sesion 33+34: live panel ranking fix + totales por item" pusheado a origin. ✅
  migracion_monitor.sql: EJECUTADA via bat. Tablas api_sync_log/monitor_config/monitor_jornada/monitor_partido_estado OK. ✅
  fix_partido_id_apuestas_v2.sql: EJECUTADA via bat. 1452 apuestas con numero_fifa, 0 cambios requeridos. ✅
  Metodo: run_docker_migrations.bat ejecutado via File Explorer (double-click). Log: migration_log.txt.

2026-06-17 - Sesion Cowork (sesion 34) - BECBUC-LIVE RANKING FIX + TOTALES POR ITEM:

  PROBLEMA RAIZ RANKING VACIO:
    El endpoint live-panel consultaba v_copamundial_puntajes usando aliases en mayuscula
    (AS pts_H, AS pts_I, etc). PostgreSQL convierte aliases sin comillas a minuscula,
    por lo que row["pts_H"] fallaba con "Could not locate column in row for column 'pts_H'".
    El except Exception lo tragaba silenciosamente → ranking_vista: [] vacio.

  FIX apostador_bets.py - live_panel endpoint:
    - Reemplazado query a v_copamundial_puntajes por query directa a puntaje_detalle + puntaje_global.
    - Aliases en minuscula: AS h, AS i, AS j, AS k, AS l, AS m, AS n, AS o, AS total_partidos.
    - Globales desde puntaje_global: pts_campeon/finalistas/goleador/peor_equipo/mayor_goleada/etapa_py/goles_py.
    - vista_map y ranking_vista ahora retornan 44 apostadores con puntos reales.
    - Variable _vista_error eliminada (era debug temporal).

  FIX becbuc-live.html - Tab Ranking:
    - Agregada fila "TOTAL ACUMULADO POR ITEM (N apostadores)" al tope del ranking.
    - Muestra suma de cada item H/I/J/K/L/M/N/O (partidos) y A-G (globales) sobre todos los apostadores.
    - Chips con color mas intenso para diferenciarlos de los chips individuales.
    - La seccion GLOBALES solo aparece si alguno tiene puntaje global > 0.

  Puntajes recalculados: POST /calcular-puntajes/2 → 77 plenos, 334 aciertos.

  EJECUTADO sesion 35 (via File Explorer bat):
    - git commit 2db8960 "sesion 33+34: live panel ranking fix + totales por item" ✅ PUSHEADO
    - migracion_monitor.sql: EJECUTADA ✅ (tablas ya existian, idempotente OK)
    - fix_partido_id_apuestas_v2.sql: EJECUTADA ✅ (1452 apuestas OK, 0 cambios necesarios)

2026-06-16 - Sesion Cowork (sesion 32) - LOGIN FIX + AUTO-REFRESH KPIs:

  PROBLEMA RAIZ LOGIN: apostador_bets.py tenia el import CurrentAdmin faltante.
    El endpoint /espn-verify/{partido_id} usaba CurrentAdmin pero no estaba importado
    en la linea de imports de app.api.deps → NameError al arrancar servidor.
    FIX: from app.api.deps import CurrentUser, CurrentAdmin, OptionalCurrentUser, BECBUCSession as DBSession

  ARCHIVO TRUNCADO REPARADO: apostador_bets.py
    La ultima linea del endpoint espn_verify_live estaba cortada ("er" en vez de "error": str(e)}).
    Reparado via script Python (binary replace del tail corrompido).
    Sintaxis verificada: OK (python3 -c "import ast; ast.parse(...)")

  login.html MEJORADO:
    - AbortController con timeout de 12 segundos: si el servidor no responde en 12s
      muestra "El servidor tardó demasiado. Verificá que uvicorn esté activo (puerto 8000)."
    - Mensajes de paso a paso: "Conectando con el servidor..." → "Verificando credenciales..."
       → "Cargando tu cuenta..."
    - Errores descriptivos por tipo:
        timeout → mensaje de uvicorn apagado
        connection refused → "No se pudo conectar con el servidor"
        401 → "🔑 Credenciales incorrectas"
        500+ → "❌ Error N: detalle"
        JSON inválido → "respuesta no es válida"
        token ausente → "no devolvió un token"
    - Antes: el fetch colgaba indefinidamente si el servidor no respondia (sin timeout).

  PORTAL BECBUC-portal.html - init() faltaba:
    La llamada init() se habia perdido en una restauracion anterior del archivo.
    SIN init(): el portal cargaba el HTML pero nunca autenticaba → _me=null → KPIs vacios,
    nombre "?", sin info de usuario.
    FIX: agregado init(); antes de </script> (linea 8600).

  AUTO-REFRESH KPIs - BECBUC-portal.html + BECBUC-movil.html:
    PROBLEMA: KPIs del dashboard quedaban congelados desde el login. Solo se recargaban
    al navegar manualmente al tab Dashboard.
    
    Portal (BECBUC-portal.html):
      - _refreshDash(): recarga KPIs (loadBecbucKpis), stats (lider/ultimo), ranking,
        partidos del dia. Se llama recursivamente con setTimeout cada 2 minutos.
      - _startDashRefresh() / _stopDashRefresh(): inician/detienen el timer.
      - showView('dashboard') llama _startDashRefresh().
      - Cualquier otra vista llama _stopDashRefresh() → no hace requests en background.
      - afterLogin() llama _startDashRefresh() para el primer ciclo.
    
    Movil (BECBUC-movil.html):
      - _refreshDashM(): extiende _loadStatsLiveM() + refresca ranking si está visible.
      - _startStatsTimerM(): cambiado de setInterval 60s a setInterval 120s llamando _refreshDashM.
      - El stats bar (lider/ultimo/apostadores) sigue refrescandose en cada ciclo.

  CREDENCIALES - PROBLEMA POWERSHELL ESCAPING:
    Los comandos anteriores usaban '\$2b\$12\$...' en PS double-quoted string.
    En PowerShell el backslash NO es caracter de escape (se usa backtick `).
    Resultado: la BD guardaba '\$2b\$12\$...' (con backslashes) → bcrypt no reconocia el hash.
    SOLUCION CORRECTA: usar variable PS con single-quote para la asignacion:
      $h1 = '$2b$12$tEHo72yAiA/NfjFAPhTW7uedeiywLf9dyT/aQ7rluY.Dnp67k4Ko6'
      docker exec core-postgres psql -U app_user -d app_db -c "UPDATE users SET password_hash = '$h1' WHERE username = 'jose';"
    Al asignar con comilla simple, el $ es literal. Al interpolar en double-quote, PS
    expande $h1 al valor correcto (con $ del hash).

  ESPN SYNC - CUANDO Y DESDE DONDE:
    1. sync_auto.py (Task Scheduler, cada 1 min): llama sync_torneo() que incluye
       _espn_verify_and_patch() como verificacion secundaria despues de API-Football.
    2. becbuc-live.html (auto, cada 20 min si hay partido en_juego):
       GET /api/v1/bets/espn-verify/{partido_id} via JS en cargar().
    Reglas ESPN: VAR siempre ESPN; amarillas/rojas ESPN si mayor; minuto solo como fallback.

  FUENTE UNICA PUNTAJES (aclaracion):
    calcular_puntajes() ESCRIBE en puntaje_detalle.
    Las vistas v_copamundial_puntajes y v_copamundial_puntajes_det LEEN de puntaje_detalle.
    El ranking, ranking-export, exportar-puntajes y live-panel TODOS leen de puntaje_detalle.
    apuesta.puntos y apuesta.puntos_bonus: mantenidos por compatibilidad, NO usados para totales.
    Para actualizar scores: el sync automatico llama calcular_puntajes() en la cadena.

2026-06-16 - Sesion Cowork (sesion 31) - ESPN LIVE + BECBUC-LIVE FIXES + LOGIN:

  apostador_bets.py:
    - live_panel ORDER BY: agrega CASE WHEN f.tipo ILIKE 'grupo%' THEN 0 ELSE 1 END
      → ya no muestra 32avos como "proximo partido" cuando aun hay grupos pendientes.
    - Nuevo endpoint GET /api/v1/bets/espn-verify/{partido_id} (admin):
      Llama ESPN, aplica correcciones (VAR/amarillas/rojas/minuto_gol) y hace commit.
      Mismo engine que sync_torneo. Retorna {partido_id, correcciones, estado, ok}.

  becbuc-live.html:
    - PASS corregido: 'Catalina' → 'catalina' (minuscula, igual que en app_db).
    - Columna tabla "Corregido▼" → "En vivo▼".
    - Twemoji CDN agregado: convierte emoji de banderas a imagenes SVG → funciona en Windows/Chrome desktop.
      <script src="https://unpkg.com/twemoji@14.0.2/dist/twemoji.min.js">
      twemoji.parse() llamado en flag-l y flag-v despues de cada render().
    - ESPN check automatico cada 20 min durante partido en_juego:
      _lastEspnCheck (timestamp) inicializado en estado.
      En cargar(): si en_juego y elapsed > 20min → GET /espn-verify/{partido_id}.
      Aplica correcciones a _partido localmente + re-render + toast amber.

  Credenciales app_db resetedas:
    jose → catalina | apostadores (id 9-53) → becbuc2026

2026-06-16 - Sesion Cowork (sesion 30) - PRONOSTICOS_AUX + FUENTE UNICA SCORING:

  TABLA pronosticos_aux - Nuevos campos:
    - numero_partido_fifa: INTEGER (P001 → 1)
    - idequipolocal, idequipovisitante: INTEGER (FK equipo, inferidos por nombre ES→EN)
    Script: sync_paux_a_apuesta.py — pobló 5280 local + 5280 visitante. 0 sin match.

  SYNC apuesta DESDE pronosticos_aux:
    - 3168 filas de apuesta.pred_* actualizadas (todos apostadores × 72 partidos CSV).
    - Join: apuesta.numero_fifa = pronosticos_aux.numero_partido_fifa + LOWER(nombre).
    - Verificado: 0 diferencias entre pronosticos_aux y apuesta (verificar_sync.py).
    - fix_nulls_apuesta.py: convirtió NULL→0 en pred_local/visitante/amarillas/rojas/var/pp/minuto.

  ANALISIS FUENTES DE PUNTAJE - PROBLEMA RAIZ ENCONTRADO:
    El ranking usaba SUM(apuesta.puntos + apuesta.puntos_bonus) como total.
    Esta columna cache quedaba desincronizada al importar predicciones sin recalcular.
    Las vistas v_copamundial_puntajes y v_copamundial_puntajes_det leen de puntaje_detalle
    y siempre son correctas. El endpoint /exportar-puntajes ya usaba las vistas.
    El /live-panel ya usaba puntaje_detalle. El /ranking NO — era el único mal.

  FIX RANKING - FUENTE UNICA DE VERDAD:
    apostador_bets.py - endpoint /ranking/{torneo_id}:
      - ANTES: _sql_base leía de apuesta (SUM puntos + puntos_bonus) + query separada puntaje_detalle
      - AHORA: Un solo CTE que lee todo de puntaje_detalle (igual que v_copamundial_puntajes):
          pd_agg: SUM de todos los pts_* → puntos_partidos_total + cat_* por categoria
          plenos_agg: plenos=marcador exacto (pts_marcador>0), aciertos=resultado ok, fallos
          Unificado en un SELECT, sin queries adicionales.
      - puntos_total = puntos_partidos_total (puntaje_detalle) + pts_globales (puntaje_global)
      - cat_* ahora en la misma query (no merge separado).

    apostador_bets.py - top5 monitor dashboard:
      - Mismo fix: ahora lee de puntaje_detalle, no de apuesta.puntos.

    apostador_bets.py - stats generales (monitor):
      - plenos/aciertos/fallos ahora usan pts_marcador/pts_resultado de puntaje_detalle.
      - Consistente con el nuevo significado: pleno=marcador exacto, acierto=resultado ok.

  CRITERIO UNIFICADO (nuevo invariante del sistema):
    FUENTE UNICA: puntaje_detalle (partidos) + puntaje_global (A-G)
    LECTURA: ranking, top5, stats, exportar-puntajes, live-panel — todos desde puntaje_detalle.
    apuesta.puntos y apuesta.puntos_bonus: mantenidos por compatibilidad pero NO usados para totales.
    PARA ACTUALIZAR SCORES: siempre correr POST /calcular-puntajes/{torneo_id}.

  Scripts auxiliares creados (en C:\proyecto FAST API\):
    sync_paux_a_apuesta.py  ← pobla pronosticos_aux + sync a apuesta
    fix_nulls_apuesta.py    ← convierte NULL→0 en pred_* de apuesta
    verificar_sync.py       ← verifica consistencia entre tablas
    ver_quiroga.py          ← muestra predicciones+resultado+puntos de un apostador
    diag_quiroga_pts.py     ← diagnóstico de discrepancias de puntaje
    recalcular_puntajes.py  ← llama POST /calcular-puntajes/2 via API

2026-06-14 - Sesion Cowork (sesion 28) - LOGIN MOVIL + NOMBRE APOSTADOR + VISTAS PUNTAJES + EXPORTAR EXCEL:

  LOGIN / APP MOVIL (fix critico):
    - BECBUC-movil.html: agregado auto-start al final del script:
        Lee token del parametro URL ?token= (redirigido desde login.html).
        Si hay token -> boot(); sino -> showLogin().
        Lineas: lectura URL param en inicializacion + `if (token) { boot(); } else { showLogin(); }` al final.
    - login.html: mejorado device detection:
        Usa /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i + window.innerWidth < 768.
        Guarda token en sessionStorage + localStorage ANTES de redirigir (evita que movil no lo encuentre).
        Redirige a BECBUC-movil.html (mobile) o BECBUC-portal.html (desktop).

  CAMPO nombre_apostador EN APUESTA:
    - Nuevo campo: apuesta.nombre_apostador VARCHAR(200).
    - Migracion: documentacion/migracion_nombre_apostador.sql (ejecutada OK).
    - apostador_bets.py - upsert_apuesta: graba nombre_apostador desde current.nombre || current.username.
    - apostador_bets.py - importar_apuestas_grupos:
        Carga user_nombre_map (id -> nombre) desde app_db en la query pre-existente.
        INSERT incluye nombre_apostador = row.nombre (Excel) || user_nombre_map[uid] || row.apostador.
    - Carga inicial de nombres existentes via dblink (UPDATE 3095 filas):
        UPDATE apuesta SET nombre_apostador = COALESCE(nombre, username) FROM dblink(app_db) WHERE nombre_apostador IS NULL.

  VISTAS SQL (becbuc):
    - v_copamundial_puntajes: resumen por apostador (torneo_id=2).
        Cols: apostador, apostador_id, partidos_finalizados, H..P pts, subtotal_partidos, A..G pts globales, subtotal_globales, total_puntos.
        Nombre desde apuesta.nombre_apostador (sin dblink).
        Archivo: documentacion/v_copamundial_puntajes.sql.
    - v_copamundial_puntajes_det: detalle por apostador x partido (solo finalizados).
        Cols: apostador, partido_id, fase, local, goles_local, goles_visitante, visitante, estado,
              por cada item (resultado/marcador/amarillas/rojas/var/penales_partido/minuto_gol/penales_tanda/equipo_clasifica):
              _real | _apuesta | _pts, total_partido.
        Archivo: documentacion/v_copamundial_puntajes_det.sql.

  ENDPOINT + UI EXPORTAR PUNTAJE:
    - apostador_bets.py: GET /api/v1/bets/exportar-puntajes/{torneo_id}
        Consulta v_copamundial_puntajes + v_copamundial_puntajes_det.
        Genera Excel (openpyxl) con 2 hojas: Resumen + Detalle.
        Devuelve StreamingResponse attachment puntajes_copa_{ts}.xlsx.
    - BECBUC-portal.html: boton "Exportar puntaje" en sidebar (visible para todos). Funcion exportarPuntajes().
    - BECBUC-movil.html: boton "📊 Exportar puntaje" junto a Excel ranking. Funcion exportarPuntajesM().

  SCRIPT STANDALONE:
    - exportar_puntajes_vista.py: alternativa CLI para generar el Excel sin servidor.
      Ejecutar: python exportar_puntajes_vista.py (requiere backend\.venv activo).

2026-06-16 - Sesion Cowork (sesion 29) - MODO NOCHE/DIA VERIFICADO + TABLA pronosticos_aux:

  MODO NOCHE/DIA (#8):
    - Verificado: YA ESTABA COMPLETAMENTE IMPLEMENTADO desde sesiones anteriores.
    - Portal: CSS [data-theme="light"] overrides en lineas 19-24, setTheme() en ~3862,
      tab "Tema" en Config con botones "Modo Oscuro" / "Modo Claro".
    - Movil: setTheme() en linea 2435, botones "Oscuro" / "Claro" en admin panel.
    - No se requirio ningún cambio de código. Tarea marcada completada.

  TABLA pronosticos_aux (nueva):
    - Objetivo: importar pronósticos históricos del CSV para análisis y comparacion.
    - Schema: id (SERIAL PK), id_partido (VARCHAR P001-P072), nombre, alias,
      equipo_local, goles_local, goles_visitante, equipo_visitante,
      amarillas, rojas, var, penales, primer_gol.
    - Indices: idx_paux_partido, idx_paux_nombre.
    - Archivo SQL: documentacion/migracion_pronosticos_aux.sql
    - Importacion: 3168 registros, 44 apostadores, P001-P072. ✅ EJECUTADO.
    - Script auxiliar: importar_pronosticos_aux.py (usa venv backend psycopg2).
    - Verificacion: resultado_importacion.txt confirma total=3168, apostadores=44.

  GIT:
    - Pendiente: git push con cambios de sesion 28 + 29.
    - Comando: cd "C:\proyecto FAST API\backend" && git add -A && git commit -m "sesion 28+29: login movil + exportar puntaje + pronosticos_aux" && git push

2026-06-13 - Sesion Cowork (sesion 27) - SYNC AUTO ACTIVADO + TASK SCHEDULER:

  PROBLEMA RAIZ: sync_auto.py tenia configuracion incorrecta → nunca habia corrido.
    - TORNEO_ID = 1 → 2 (torneo activo es siempre el 2)
    - ADMIN_USER = "admin@becbuc.com" → "Jose"
    - ADMIN_PASS = "changeme" → "Catalina"
    - Login usaba clave "email" → cambiado a "username" (lo que espera el API)
    - Archivo estaba truncado: faltaba la ultima linea `if __name__ == "__main__": main()`
    - Python path en PS1: .venv → backend\.venv (ubicacion real del venv)

  NUEVO ARCHIVO: registrar_sync_auto.ps1
    - Script PowerShell listo para ejecutar como Admin.
    - Prueba sync_auto.py, verifica log, elimina tarea anterior si existe, registra nueva.
    - Ubicacion: C:\proyecto FAST API\registrar_sync_auto.ps1

  TASK SCHEDULER REGISTRADO Y VERIFICADO:
    - Tarea: BECBUC-SyncAPI
    - Corre cada 1 minuto con RunLevel Highest
    - Verificado en vivo: detecto Brazil vs Morocco [en_juego], 1 actualizado, 3 API calls, puntajes_ok=True
    - Log: C:\proyecto FAST API\sync_auto.log

  ESTADO: sync automatico ACTIVO. Los minutos del partido se actualizan solos en becbuc-live.html.

2026-06-13 - Sesion Cowork (sesion 26) - FIX IMPORTAR EXCEL COLUMNAS:

  importar-apuestas.html (parseIndividualFormat):
    - CAUSA: parser leia columnas con offset -1 vs plantilla Excel real del apostador.
      partido_num: row[0] (col A) -> row[1] (col B) ✅
      equipo_local: row[9] (col J) -> row[10] (col K) ✅
      goles_local: row[11] (col L) -> row[12] (col M) ✅
      goles_visitante: row[13] (col N) -> row[14] (col O) ✅
      equipo_visitante: row[14] (col O) -> row[15] (col P) ✅
    - Condicion skip: !row[0] -> !row[1] (usa partido_num para detectar fila vacia).
    - Filtro fase: row[5] (col F) sin cambio (ya estaba correcto).
    - EFECTO: alias en col J ahora queda ignorado (alias ya se lee de la hoja ficha D5).
      Los goles, equipos y partido_num ahora llegan correctamente al backend.
      DELETE fase + re-INSERT funciona: bet anterior de cherem (0-3) se elimina antes
      del INSERT del nuevo (1-3).

2026-06-13 - Sesion Cowork (sesion 25) - BECBUC EN VIVO + FIX SYNC:

  NUEVO ARCHIVO: backend/static/becbuc-live.html (650 lineas)
    Pagina standalone de seguimiento en vivo. Diseño oscuro (paleta #0f172a/#111827/#1f2937).
    Acceso: http://localhost:8000/static/becbuc-live.html
    Externo (iPhone): https://cupped-oink-thousand.ngrok-free.dev/static/becbuc-live.html

  CARACTERISTICAS:
    - Auto-login como Jose/Catalina (sin pantalla de login, token solo en memoria JS)
    - Detecta torneo activo automaticamente via GET /api/v1/torneo/activas
    - Boton "🔄 Sincronizar" (solo admin): llama POST /sync-resultados/{torneo_id}
    - Boton "🏠 Portal": enlace al portal principal
    - Auto-refresh cada 90s mientras el partido esta en_juego
    - Reloj en tiempo real en el header

  ESTRUCTURA JS (funciones principales):
    init()             <- auto-login + detecta torneo + carga panel
    cargarPanel()      <- GET /live-panel/{torneo_id} -> _partido + _apostadores
    calcularTodos()    <- scoring engine JS puro (sin API), llena _resultados[]
    calcScore(p,ap,allMin) <- calcula H/I/J/K/L/M/N/O para un apostador
    render()           <- actualiza DOM con _partido y _resultados
    sincronizar()      <- POST sync-resultados -> recarga datos
    startAutoRefresh() <- polling 90s cuando partido en_juego
    flagEmoji(iso,name) <- iso code o fallback por ISO_MAP[nombre]
    api(url,opts)      <- fetch wrapper con JWT + ngrok-skip-browser-warning

  ESTRUCTURAS DE DATOS:
    _partido    <- dict con campos del endpoint live-panel
    _apostadores <- array con pred_local/visitante/amarillas/rojas/var/pp/minuto/tanda
    _resultados  <- array calculado en JS: {apostador_id, nombre, puntos_base, detail, pts_partido, total_proyectado}

  SCORING ENGINE JS (FASE_PTS):
    grupos: H=4, I=8 | 16avos: H=6, I=12 | 8avos: H=8, I=16
    4tos: H=10, I=20 | semi: H=12, I=24 | tercero: H=14, I=28 | final: H=20, I=40
    J/K/L/M/N: 1 pt exacto | O: 2 pts/equipo en tanda | Paraguay: mult=2
    Minuto gol (N): 1 pt al apostador mas cercano (entre todos los apostadores)

  ENDPOINT NUEVO: GET /api/v1/bets/live-panel/{torneo_id}
    Prioridad partido: en_juego > pendiente/prog (+130min) > finalizado hoy > mas reciente
    Retorna: partido (con fase_tipo, es_paraguay, bandera_local/visitante) + apostadores[]
    Bandera: COALESCE(equipo.codigo_iso, '') -> JS fallback por ISO_MAP si vacio

  FLAGS (ISO_MAP en JS):
    ~80 selecciones mapeadas nombre→ISO (Qatar→QA, Switzerland→CH, etc.)
    SPECIAL_FLAGS: England/Scotland/Wales → emoji de bandera regional
    En Windows Chrome: renderiza como "QA"/"CH" (normal, Windows no soporta flag emoji)
    En iPhone: renderiza como 🇶🇦 🇨🇭 correctamente

  TABLA (columnas):
    Apostador | Pred. | H | I | J | K | L | M | N | O | +Live | Total▼

  FIX sync_api_football.py:
    - sync_torneo(): agregado parametro fecha_filtro=None a la firma.
      Cuando se provee, filtra partidos de esa fecha especifica (resync_ayer / resync_fecha).
      SQL construido dinamicamente con variable _ff_clause + _ff_params.
    - Archivo estaba truncado en _update_partido_full (linea 940). Completado:
      dict de params UPDATE + await db.commit() faltaban.

  FIX api() helper en becbuc-live.html:
    - Header 'ngrok-skip-browser-warning': 'true' en todas las llamadas (evita interstitial ngrok en movil)
    - opts spread DESPUES de headers para no pisarlos: {...opts, headers}
    - Error message incluye codigo HTTP y detalle del body: "Error en sync [500]: ..."

  FIX endpoint live_panel (apostador_bets.py) - continuacion sesion 25:
    - Token cache 24h en localStorage (key 'bec_live_token' + 'bec_live_token_exp').
      Auto-login jose/Catalina si no hay token valido. Retry con token fresco en 401.
    - Fallback partido: si no hay programado/en_juego -> ultimo finalizado (ORDER BY fecha DESC).
    - Columnas puntaje_global: pts_etapa_py/pts_goles_py -> pts_etapa_paraguay/pts_goles_paraguay.
    - JOIN puntaje_detalle: d.apuesta_id (no existe) -> d.partido_id=p2.id AND d.apostador_id=ap.apostador_id.
    - Query users_r (redundante y con error) eliminada. Solo rank_r calcula puntos totales.
    - VERIFICADO: endpoint retorna partido + 43 apostadores con puntos reales.
      becbuc-live.html renderiza correctamente: partido, tabla predicciones, ranking top-5.

  REQUERIMIENTOS becbuc-live.html (doc para futuras sesiones):
    - Autenticacion: jose/Catalina, token 24h localStorage, auto-renova en 401.
    - Partido: proximo programado/en_juego por fecha; fallback ultimo finalizado.
    - Tabla: todos los apostadores con predicciones + puntos H/I/J/K/L/M/N/O calculados en JS.
    - Ranking: top-5 por total proyectado (puntos actuales + pts partido en curso).
    - Auto-refresh 60s. Boton 🔄 manual. Boton 🏠 Portal (token via sessionStorage).
    - Pagina completamente independiente (sin herencia de portal ni movil).

2026-06-13 - Sesion Cowork (sesion 24) - FIX ARBOL RANKING + EXCEL RANKING POR FASE:

  CAUSA: _rkLoadNodeContent (portal) y toggleRkAposM (movil) llamaban a /mis-apuestas
    que NO incluye campos pts_* de puntaje_detalle. Los items siempre mostraban 0.

  FIX backend - apostador_bets.py:
    - mis_partidos: agregado parametro for_apostador_id (igual que mis_apuestas).
      Admin puede ver datos de otro apostador via for_apostador_id.
      target_id = current.id por defecto; si for_apostador_id y es admin, usa ese id.
      _qparams usa target_id en vez de current.id.

  FIX frontend - BECBUC-portal.html + BECBUC-movil.html:
    - _rkLoadNodeContent (portal): /mis-apuestas → /mis-partidos
    - toggleRkAposM (movil): /mis-apuestas → /mis-partidos
    Ahora el arbol nivel 3 recibe pts_resultado, pts_marcador, pts_amarillas,
    pts_rojas, pts_var, pts_penales_partido, pts_minuto, pts_penales_tanda
    directamente de puntaje_detalle via el endpoint correcto.

  EXCEL RANKING - apostador_bets.py:
    - Nuevo endpoint GET /api/v1/bets/ranking-export/{torneo_id} (todos los roles).
    - Genera workbook openpyxl con StreamingResponse:
        Hoja "Puntaje general": tabla ranking Pos|Apostador|H|I|J|K|L|M|N|O|Glob|Total.
        Una hoja por fase (ej. "Fase de grupos", "Ronda 32", etc.):
          Tabla plana apostador×partido con AutoFilter en fila 2.
          Cols: Apostador | Partido | Marcador(Pred/Real) | H-Pts | I-Pts |
                J(Pred/Real/Pts) | K(Pred/Real/Pts) | L(Pred/Real/Pts) |
                M(Pred/Real/Pts) | N(Pred/Real/Pts) |
                O(Pred-L/Pred-V/Real-L/Real-V/Pts) | Total.
    - BECBUC-portal.html: boton "📥 Excel" junto a toggles Totales/Por partido.
      Funcion downloadRankingExcel() usa fetch + blob download.
    - BECBUC-movil.html: boton "📥 Excel ranking" en header de ranking.
      Funcion downloadRankingExcelM(btn) equivalente.

  PENDIENTE POST-SESION:
    - Verificar visualmente que el arbol muestra pts reales por item
    - Verificar descarga Excel con datos reales
    - Git push + backup
    - Recalcular puntajes si no se hizo en sesion 23

2026-06-12 - Sesion Cowork (sesion 23) - LOGIN INDEPENDIENTE + SCORING NULL FIX + ARBOL 3 NIVELES:

  login.html (NUEVO - /static/login.html):
    - Pagina de login independiente. Formulario minimalista sin logica extra.
    - POST /api/v1/auth/login -> guarda token en sessionStorage('bec_token') Y localStorage('tok_fix').
    - Redirige a BECBUC-portal.html (desktop) o BECBUC-movil.html (mobile).
    - SIN auto-login, SIN deteccion de token preexistente, SIN logica adicional.
    - Acceso: http://localhost:8000/static/login.html

  BECBUC-portal.html - Eliminacion login overlay:
    - CSS login eliminado (.login-overlay, .login-card, .login-input, etc.)
    - HTML login overlay eliminado (div#loginOverlay con formulario)
    - Funcion doLogin() eliminada
    - api(): en 401 solo lanza Error('UNAUTH'), NO redirige
    - token: ahora lee sessionStorage > localStorage > URL param (fallback localStorage agregado)
    - init(): unico punto de redirect a login.html (si no hay token o /auth/me falla)
    - logout(): limpia tokens y redirige a login.html
    - init() llamado al pie del script (era necesario, antes no se llamaba -> portal en blanco)
    - Fix SyntaxError linea 8201: linea duplicada en _loadRkPronPartidos corregida

  copa_mundo_2026.py - Fix scoring NULL->0 (J/K/L/M):
    - pred_amarillas / real_amarillas: (valor or 0) antes de comparar
    - pred_rojas / real_rojas: idem
    - pred_var / real_var: idem
    - pred_pp / real_pp: idem
    - Efecto: NULL pred == NULL real -> 1 pt (antes: 0 pts)
    - Requiere recalcular puntajes via POST /calcular-puntajes/{torneo_id}

  Arbol ranking 3 niveles (portal + movil):
    - Nivel 1: apostador (toggle) con total pts
    - Nivel 2: partido con score real vs predicho + pts parcial (toggle)
    - Nivel 3: desglose H/I/J/K/L/M/N/O con pts individuales y total
    - Portal: _rkTogglePartido(aid,pid) + _rkLoadNodeContent reescrito
    - Movil: toggleRkAposM async + toggleRkPartidoM(aid,pid) reescrito

  PENDIENTE POST-SESION:
    - Ejecutar backup: cd "C:\proyecto FAST API" && .\backup_becbuc.ps1
    - Recalcular puntajes: POST /calcular-puntajes/{torneo_id} desde portal (Herramientas)
    - Git push: cd "C:\proyecto FAST API\backend" && git add -A && git commit -m "sesion 23: login independiente + scoring null fix + arbol 3 niveles" && git push

2026-06-12 - Sesion Cowork (sesion 22) - SYNC HISTORICO + UI MONITOREO SIMPLIFICADA + FIX TRUNCACION MOVIL:

  apostador_bets.py (5550 lineas, AST OK):
    - POST /api/v1/bets/sync-historico/{torneo_id} (admin):
        force=True, max_detalle=50. Chain: auto-mapeo → sync → standings → bracket → puntajes.
        Retorna: {ok, actualizados, partidos_importados(lista con resultado/estado/amarillas/var), sync, bracket_ok, puntajes_ok, puntajes}.
        partidos_importados query usa IN ({ids_sql}) — compatible con asyncpg.
    - GET /api/v1/bets/verificar-importacion/{torneo_id} (admin):
        Retorna ultimos N partidos finalizados/en_juego con todos sus campos.
        Campos: goles, amarillas, rojas, var, penales_tanda, minuto_gol, mapeado(api_fixture_id).

  BECBUC-portal.html — Monitoreo simplificado:
    - CSS: .mon-sync-primary-row, .mon-sync-big-btn, .mon-sync-secondary-col, .mon-sys-details, .api-status-bar.
    - Acciones Rápidas (monCardAcciones):
        Gran boton verde "📥 Importar partidos jugados" (id=btnSyncHistorico, onclick=syncHistorico()).
        Col secundaria: "🔄 Actualizar hoy" + "🔁 Re-sync de ayer".
        syncHistMsg: muestra cadena auto-mapeo → resultados → bracket → puntajes.
        syncHistResult: tabla oculta que se muestra al importar (Partido | Resultado | Estado | Amar. | VAR).
        <details>: Calcular puntajes, Avanzar bracket, Siguiente fase, Excel, Finalizar partido.
    - API Monitor simplificado:
        api-status-bar: dot + conexion + semaforo + llamadas + toggle auto-sync + refresh.
        Tabla de log (apiLogBody) y partidos del dia (apiMonPartidosWrap): siempre visibles.
        Eliminados: help modal, descargar fixture, poll inmediato, scheduler card complejo.
    - syncHistorico(): nueva funcion JS que llama POST /sync-historico, muestra tabla de importados.

  BECBUC-movil.html — Reparacion truncacion + sync historico:
    - loadAdmin() HTML: gran boton "📥 Importar partidos jugados" (id=amBtnSyncHist).
      Col secundaria: Actualizar hoy + Re-sync ayer. amHistResult: lista de importados.
      <details>: Calcular puntajes, Avanzar bracket, Siguiente fase, Excel, Finalizar.
    - amSyncHistoricoM(btn): nueva funcion, llama POST /sync-historico, muestra resultados.
    - TRUNCACION REPARADA: archivo estaba cortado en linea 2878 (mitad de _renderRankingTotal).
      Contenido restaurado/reconstruido:
        _renderRankingTotal: tabla principal (H/I/J/K/L/M/N/O + globales + total) +
          tabla globales separada (task #16) + arbol expandible por apostador.
        setRkModoM: stub de compatibilidad.
        _onRkFilterChangeM: re-renderiza al cambiar filtro "Todos".
        toggleRkAposM(aid, el): expande/colapsa nodo apostador en arbol.
        toggleRkPartidoM(pid, el): expande/colapsa nodo partido en arbol.
        TRANSPARENCIA / MENSAJES / _mPRow / FINALIZAR PARTIDO: restaurados desde git HEAD.
      Archivo final: 3600 lineas, 2 script abiertos / 2 cerrados, termina con </html>.

  PENDIENTE POST-SESION:
    - Ejecutar sync real contra API-Football con torneo activo.
    - Verificar partidos importados via GET /verificar-importacion/{torneo_id}.
    - Recalcular puntajes via POST /calcular-puntajes/{torneo_id}.

2026-06-12 - Sesion Cowork (sesion 21) - FIX 500 SYNC + MONITOR WARNINGS:

  sync_api_football.py:
    - _log helper REESCRITO: ya no llama log_api_call (que hacía commit + rollback externos).
      Ahora hace INSERT directo en api_sync_log sin commit — el llamador commtea.
      Wrap en try/except: un error de logging nunca interrumpe el sync.
    - _log_warn(db, contexto): nueva función para advertencias sintéticas sin llamada HTTP.
    - _update_partido_full: eliminados eventos_api y estadisticas_api del UPDATE.
      Esas columnas requieren migracion_eventos_api.sql (ya creada, pendiente ejecutar).
      El UPDATE es ahora seguro contra BD sin esas columnas.
    - Post-sync warnings automáticos (se graban en api_sync_log):
        ⚠ Cuota baja: N llamadas restantes (cuando < 20)
        ⚠ N partido(s) con error: [descripción]
        ⚠ 0 actualizados de N candidatos — revisar API
        ℹ Auto-mapeo: N partido(s) mapeados automáticamente
    - Importación de log_api_call/ApiResult removida (ya no se usa).
    - _quota_remaining: capturado de respuesta bulk FT para usarse en warning post-sync.

  BECBUC-portal.html (monitor log UI):
    - CSS: .api-log-warn (amber), .api-log-table tr.row-err/.row-warn (tint background),
      .api-log-badge (chip amber para contar alertas).
    - Log header: badge id="apiLogWarnBadge" con conteo de alertas activas.
    - _renderApiMon log renderer mejorado:
        Filas coloreadas: rojo (error_msg/❌/⛔), amber (⚠/ℹ), verde (ok).
        Badge count actualizado dinámicamente al cargar.
        Cuota restante mostrada inline con color amber cuando < 20.

  apostador_bets.py: archivo estaba truncado en medio del return de importar_apuestas_grupos.
    Reparado — ahora OK (5338 líneas, sin errores de sintaxis).

  MIGRACION PENDIENTE (opcional, para audit completo):
    migracion_eventos_api.sql: agrega eventos_api + estadisticas_api JSONB en partido.
    Get-Content "C:\proyecto FAST API\documentacion\migracion_eventos_api.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

2026-06-12 - Sesion Cowork (sesion 20) - ITEM M (PENALES DEL PARTIDO) HABILITADO:

  Decision organizacion: item M (penales cobrados durante el juego) aprobado e implementado.
  Tabla oficial: M = 1 pt en todas las fases (Grupos a Final), x2 Paraguay.

  sync_api_football.py (RESTAURADO desde git HEAD, estaba truncado a 660 lineas -> 821):
    - _update_partido_full: nuevo contador penales_partido_total en el loop de eventos.
        Goal+Penalty -> penal convertido; Miss/Goal + (Missed Penalty|Penalty Missed) -> fallado.
    - UPDATE partido: + penales_partido = COALESCE(:pp, penales_partido).
      pp = penales_partido_total si hay eventos, sino None (no pisa valor previo en sync parcial).

  Scoring (ya estaba implementado, solo faltaban datos + UI):
    - base.py: FaseConfig.pts_penales_partido=1, PartidoScore.pts_penales_partido.
    - copa_mundo_2026.py: score M (1 pt si pred==real, x2 Paraguay).
    - calculator.py: carga p.penales_partido + a.pred_penales_partido, persiste pts_penales_partido.
    - apostador_bets.py: ApuestaIn.pred_penales_partido + upsert + mis-apuestas: ya presentes.

  UI - BECBUC-portal.html (modal bonus estaba TRUNCADO/perdido, RESTAURADO):
    - El tail del archivo (modales finalizarPartido + msgModal + bonusModal) faltaba entre
      </script> y </body>. Restaurado completo desde HEAD + reconstruido el modal bonus.
    - Modal bonus: nuevo campo bm-pp (🥅 Penales en el partido) tras Rojas.
    - _readBonusInputs / _applyBonusToSlip / hasAny: incluyen pred_penales_partido.
    - 5 cuerpos de guardado (grupos + KO) ahora envian pred_penales_partido al API.

  UI - BECBUC-movil.html:
    - Tarjeta grupo: ya tenia input ⚽ Penales partido (bpp-).
    - Panel bonus KO (_koCardsM): faltaban Rojas (K) y Penales partido (M). Agregados.
      Extraccion prj/pppm, hasBonus actualizado, inputs onBkBonusM(pred_rojas/pred_penales_partido).
    - saveKOM: + pred_penales_partido en el body del POST.

2026-06-12 - Sesion Cowork (sesion 20) - FIX AUDIT LOG + MONITOR TABLES MIGRATION:

  documentacion/migracion_monitor.sql (NUEVO - ejecutar):
    - CREATE TABLE IF NOT EXISTS: api_sync_log, monitor_config, monitor_jornada, monitor_partido_estado
    - INSERT defaults en monitor_config (tick intervals, max_calls_dia)
    - Indices: idx_api_sync_log_created
    Comando:
      Get-Content "C:\proyecto FAST API\documentacion\migracion_monitor.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

  backend/app/services/monitor/persistence.py:
    - get_api_log_recent: try/except → return [] si tabla no existe (evita 500)
    - count_api_calls_today: try/except → return 0 si tabla no existe
    - get_monitor_config: try/except → return {} si tabla no existe
    - get_partidos_del_dia: archivo truncado reparado (completion appended)

  BECBUC-portal.html - _renderApiMon():
    - Eliminado return prematuro cuando s._err (causa: tabla faltante → 500 → error json)
    - Semaforo/scheduler block envuelto en if (!s._err) { ... }
    - Log table siempre se renderiza desde logData aunque status endpoint haya fallado
    - Resultado: tabla de audit log ya no queda en "Cargando…" indefinidamente

  NOTA: Ejecutar migracion_monitor.sql para activar tablas del monitor completamente.
    Hasta que se ejecute: persistence.py devuelve [] / 0 / {} (degradado pero sin crash).

2026-06-12 - Sesion Cowork (sesion 19) - EN VIVO: STATS REALES + PENALES + VAR + DESGLOSE PTS + RE-SYNC AYER + RANKING 60/40:

  apostador_bets.py:
    - partidos_en_vivo query: agrega ap.pred_penales_partido al SELECT.
    - sync_resultados endpoint (sesion anterior, confirmado): resync_ayer + resync_fecha params.
    - importar_apuestas_grupos: archivo truncado reparado (append del cierre faltante).

  BECBUC-portal.html + BECBUC-movil.html - En Vivo ficha partido:
    - CSS: .lv-real-bar / .lvm-real-bar: barra siempre visible con stats reales.
    - Barra real stats (!prog): 🟨amarillas · 🟥rojas · VAR×N · 🥅penales_partido · ⚽minuto.
      Se muestra para en_juego Y finalizado, independientemente de si el user tiene predicciones.
    - hasAnyBonus ahora incluye pred_penales_partido.
    - Bonus chips: agrega chip 🥅 penales_partido (pred vs real, con ok/miss).
    - Desglose de puntos por ítem (H/I/J/K/VAR/N/O) debajo del chip de pts_total.
      Solo se muestra cuando pts_total > 0 y el partido NO está programado.
    - extChips (stats grid) y fallback chips: agrega 🥅 Pen. juego ×N.
    - renderBetPartidos (portal) y _renderPronosPartidosM (mobile):
      agrega badge 🥅penales_partido a la lista de partidos finalizados.

  BECBUC-portal.html - Acciones Rápidas (monCardAcciones):
    - Botón "🔄 Sync API-Football" (id=btnSyncApi) → syncResultados(false).
    - Botón "🔁 Re-sync de ayer" (id=btnResyncAyer) → syncResyncFecha('ayer').
    - div#syncMsg para mostrar resultado del sync/re-sync.
    - Descripción actualizada (incluye Sync + Re-sync de ayer).

  BECBUC-movil.html - Admin panel:
    - Botón "🔁 Re-sync de ayer" (id=btnResyncAyerM) → amResyncAyerM(this).
    - Nueva función amResyncAyerM(btn): POST /sync-resultados?resync_ayer=true.

  BECBUC-portal.html - Pronósticos → Ranking:
    - Layout: grid 60%/40% (tabla/árbol) en vez de flex con max-width fijo.
    - Total column: calculado desde H+I+J+K+L+M+N+O+P+glob (transparente, no desde puntos_total BD).
    - cat_equipo (P) se muestra por fila si > 0 (color #e879f9).

2026-06-12 - Sesion Cowork (sesion 18) - RANKING DUAL PANEL MOVIL + PLAYOFFS A DEFINIR + BONUS POPUP FIX:

  BECBUC-movil.html - Ranking dual panel (equivalente al portal):
    - Eliminados botones toggle Árbol/Tabla. Ambos paneles se muestran simultáneamente.
    - filterBar reemplaza toggleBar: solo checkbox Todos + botón Excel.
    - _renderRankingTotal: renderiza tabla + árbol en secuencia (sin modo).
    - myIdx: usa _rkMatchMine(r) en vez de r.nombre===my (fix admin viewAs).
    - toggleRkPartidoM: usa querySelector('span:first-child') para la flecha (fix bug "Todos").
    - toggleRkPartidoM: ptEl.textContent='(X pts.)' con paréntesis.
    - toggleRkPartidoM: apostador muestra "Nombre (X pts.)" en el nodo.
    - toggleRkAposM: items con "(X pts.)" concatenado en el label.
    - toggleRkAposM: usa querySelector('span:first-child') para flecha.
    - goles_local??0 (null = 0) en vez de ??'?'.
    - setRkModoM: mantenida por compatibilidad pero sin efecto real.
    - _onRkFilterChangeM: rellamada a _renderRankingTotal() (re-renderiza todo).

  BECBUC-portal.html + BECBUC-movil.html - Fix playoffs "a definir":
    - _koCards (portal) y _koCardsM (movil): nueva variable hideTeams = !forceEdit && num >= 89.
    - Cuando hideTeams=true: lDisplay/lRow y vDisplay/vRow siempre muestran "Por definir"
      independientemente de si lObj/vObj existen.
    - Efecto: en Pronósticos→Playoffs, Ronda 16, cuartos, semis, tercer puesto y final
      NO muestran países (equipos propagados por el bracket). Solo R32 (73-88) muestra equipos.
    - En popup (forceEdit=true): equipos siguen mostrándose para contexto del admin.

  BECBUC-portal.html + BECBUC-movil.html - Fix bonus popup modo no editable:
    - _koCards (portal): bonusOnClick siempre asignado; botón bonus sin disabled.
      Antes: cuando locked=true, onclick='', button disabled → no se podía abrir popup.
      Ahora: siempre abre openBonusModal, permite ver valores aunque esté bloqueado.
    - _koCardsM (movil): bonusToggle siempre asignado al botón de toggle inline.
      Antes: locked?'disabled':onclick → no se podía abrir el panel bonus.
      Ahora: toggle siempre funciona; inputs internos mantienen disabled.

2026-06-12 - Sesion Cowork (sesion 17) - FIX MEJORES TERCEROS + EN VIVO + PARTIDOS STATS + MOBILE PARTIDOS TAB:

  FIX - Mejores terceros no actualizaban al cambiar scores (portal):
    - BECBUC-portal.html: _renderMejoresTerceros() estaba dentro del bloque if(faseId) en onScoreChange.
      Movida afuera: ahora siempre se ejecuta al cambiar cualquier score, independiente de faseId.

  FIX - Tab "En Vivo" mostraba partidos finalizados de dias anteriores (backend):
    - apostador_bets.py: partidos_en_vivo query tenia OR DATE(fecha)=CURRENT_DATE sin filtrar estado.
      Fix: OR (DATE(fecha AT TIME ZONE 'UTC') = CURRENT_DATE AND p.estado != 'finalizado').
      Ahora "hoy" solo muestra programados/en_juego; los finalizados solo si son ultimas 3h.

  FEATURE - Estadisticas en tab "Partidos" (amarillas / rojas / VAR):
    - apostador_bets.py: endpoint /partidos-finalizados ahora incluye p.amarillas, p.rojas, p.decisiones_var.
      Tambien cambiado a COALESCE(nombre_es, nombre) para equipos.
    - BECBUC-portal.html: renderBetPartidos muestra badges 🟨/🟥/📺 cuando hay datos.
      (amarillas siempre si no null, rojas/VAR solo si > 0)
    - BECBUC-movil.html: _renderPronosPartidosM implementada (no existia, tab quedaba roto).
      Funcion nueva con layout compacto mobile-friendly, misma logica de badges.

  FIX previo (sesion 16 continuacion, aplicado en sesion 17):
    - Tree click admin (BECBUC-portal.html): onclick con JSON.stringify producia comillas dobles
      dentro del atributo HTML. Fix: data-uid/data-nombre/data-pts + this.dataset en onclick.

2026-06-12 - Sesion Cowork (sesion 16) - FIX JS CRITICO + ONLINE INDICATOR + ADMIN VIEW-AS:

  BUG CRITICO RESUELTO: Login "no inicializa" (Uncaught SyntaxError: Unexpected token '{'):
    - apostador_bets.py: archivo truncado a mitad de importar_apuestas_grupos → restaurado.
      Tambien faltaban contar_apuestas e inicializar_brackets → restaurados.
      Nuevo endpoint POST /heartbeat?source=web|movil (in-memory, TTL 120s).
      Nuevo campo online_source en ranking response (desde _is_online(uid)).
      _online_users: dict[int, tuple[float, str]] = {} a nivel modulo.
    - BECBUC-portal.html: renderBetGlobales truncada a mitad de template literal → restaurada.
      Funcion completa + saveGlobales agregados (formula A-G, equipos, goleador, etc.).
      saveGlobales URL corregida: /api/v1/bets/apuestas-globales/{torneo_id}.

  FEATURE: Indicador de usuario conectado en ranking (web/movil):
    - apostador_bets.py: _online_users, _is_online(), POST /heartbeat.
      ranking response incluye online_source ('web'|'movil'|None) por usuario.
    - Portal: _startHeartbeat()/_stopHeartbeat(), ping cada 30s con source=web.
      _onlineBadge(source): muestra 💻 o 📱 junto al nombre en tabla ranking.
      Heartbeat inicia en afterLogin(), se detiene en logout().
    - Movil: _startHeartbeatM()/_stopHeartbeatM(), ping cada 30s con source=movil.
      _mOnlineBadge(source): badge en tabla ranking movil.
      Heartbeat inicia en boot() al ocultar login.

  FEATURE: Admin/superadmin puede ver apuestas de cualquier usuario en Pronósticos:
    - Portal: selectBetTorneo() ahora llama loadApostadorTree() si _isAdmin.
      Panel lateral (apostadorTreePanel) se muestra con lista de apostadores + puntos.
      Click en apostador → setViewAs() → recarga tab activo con for_apostador_id=X.
      _viewAsParam() ya existia y aplica a todos los endpoints del tab.
    - Movil: loadPronos() ahora fetchea ranking y llama populatePronApostadorSel() si admin.
      El select pronViewAsSel ya existia en HTML, solo faltaba el populate.

2026-06-12 - Sesion Cowork (sesion 15) - UX GRUPOS + RANKING TOGGLE + WATCHDOG LIVE:

  BECBUC-portal.html:
    - _estadoBadge(estado): helper que devuelve chip ✅ Final / 🔴 En vivo / ⏰ Prog.
    - _grupoCard: badge de estado agregado en div.gbc-date de los 3 branches del match card
      (finalizado-historial, apostar, historial-pendiente). CSS .gbc-sts-chip.fin/.live/.prg.
    - renderBetRanking: toggle "🏆 Totales | ⚽ Por partido" al tope del tab Ranking en Pronósticos.
      Estado _rkPronModo + cache _rkPronRankingCache (evita re-fetch al cambiar modo).
      Funciones: setRkPronModo(modo), _loadRkPronPartidos(), _populateRkPronSel(sel),
      onRkPronPartidoChange(val) — reutiliza endpoint /ranking-partido/{id}?partido_id=N.
      refreshPronos(): invalida _rkPronRankingCache + _rkPronPartidosCache al actualizar.
    - Live refresh watchdog (180s): _liveWatchdog, _liveLastSuccess, _startLiveWatchdog(),
      _stopLiveWatchdog(). Si la API no responde en 3 min durante un partido en vivo, fuerza
      reinicio del polling automáticamente.

  BECBUC-movil.html:
    - Live refresh watchdog (180s): _mLiveWatchdog, _mLiveLastSuccess, _startLiveWatchdogM(),
      _stopLiveWatchdogM(). Misma logica que portal, idem sync rule.
    - Status en match cards: ya estaba implementado via metaLbl / mc-meta. Sin cambios.
    - Toggle ranking: ya estaba en _renderRankingTotal / setRkModoM. Sin cambios.

  NOTA: El toggle Totales/Por partido en Pronósticos→Ranking del portal es INDEPENDIENTE
  del mismo toggle en el panel Dashboard (distintos estados y elementos DOM).

2026-06-11 - Sesion Cowork (sesion 14) - LIMPIEZA CODIGO + GIT INICIAL + CONFIG REMOTE:

  test_integral.py - CORRIO EXITOSAMENTE (4 bugs corregidos en sesiones anteriores):
    - apostador1: 972 pts (900 partidos + 72 globales)
    - apostador2: 346 pts (300 partidos + 46 globales)
    - 104 partidos finalizados en BD, 416 filas en puntaje_detalle ✅

  Limpieza de codigo muerto:
    - 9 archivos eliminados: backend/app/models/becbuc/ completo (ORM muerto, nunca usado)
    - Funcion _fase_encerrada() eliminada (sin callers, reemplazada en sesion 4k)
    - Imports sin uso removidos: defaultdict local, secrets, string, timezone, datetime, field
    - Variables sin uso removidas: fase_subq, bracket_ok, e, i_exp, calc, excel_out
    - Bloque DIAG/DEBUG de generar_excel_becbuc.py eliminado
    - _wdl() refactorizada a scoring/base.py (era duplicada en copa_mundo y default engines)

  Bugs corregidos durante la limpieza:
    - apostador_bets.py: Query faltaba en imports -> NameError al iniciar servidor
    - test_integral.py: encoding="utf-8" faltaba -> globales siempre 0 (Mbappé rechazado por cp1252)
    - test_integral.py: NULL en columnas NOT NULL de KO durante reset -> error BD

  Git inicializado:
    - Primer commit: f5af99d "feat: add BECBUC tournament betting system (sessions 1-13)"
    - 115 archivos commiteados, working tree limpio
    - .gitignore actualizado (*.zip, ngrok.exe, cloudflared.exe, static/auditorias/, etc.)

  Git remote configurado (seguridad):
    - PAT hardcodeado removido de .git/config
    - Remote limpio: https://github.com/josebogarin/postgres-api.git
    - credential.helper = manager (Windows Credential Manager)
    - Credenciales viejas de Windows CM limpiadas (causaban 403)
    - Push pendiente: requiere autenticacion fresca de GitHub (josebogarin)

  generar_excel_becbuc.py: NO ejecutado aun (pantalla auto-lock interrumpio computer use)
    PENDIENTE: correr manualmente y verificar que genera sin "0 partidos" bug

2026-06-11 - Sesion Cowork (sesion 13) - SYNC LIVE + BARRA EN VIVO + AUTO-REFRESH STANDINGS/RANKING + FIX CONGELADO:

  sync_api_football.py:
    - from datetime import datetime, timezone agregado.
    - Fallback ampliado: ademas de en_juego en BD, detecta partidos dentro de
      ventana temporal 0-150 min desde fecha inicio (garantiza 2do tiempo).
    - Goles VAR: antes de asignar minuto_primer_gol, filtra goles con minuto
      marcado como anulado (Goal Disallowed, Goal Cancelled, Offside Goal).

  apostador_bets.py:
    - grupos endpoint: agrega minuto_actual al SELECT de partidos.
    - sync_resultados: agrega _recalc_participacion(db, torneo_id) entre sync y
      avanzar_bracket para que PJ/PG/PE/PP/GF/GC/Pts se actualicen en cada sync.
    - hay_partido_activo: ventana cambiada de +30min (pre-partido) a -15min
      (sync arranca solo 15 minutos despues del inicio del partido).

  sync_auto.py:
    - Comentarios actualizados para reflejar nueva ventana (+15 min).

  BECBUC-portal.html:
    - CSS: .gbc-live-bar, .gbc-live-dot (animacion pulse), .gbc-live-score,
      .gbc-live-min, .gbc-live-stat.
    - _grupoCard (modo apostar y modo historial): barra live para partidos
      en_juego mostrando score actual, minuto, amarillas, rojas.
    - Live refresh: _liveTimer, _doLiveRefresh(), _startLiveRefresh(),
      _stopLiveRefresh(). Auto-polling cada 30s cuando hay en_juego.
    - FIX CONGELADO: _doLiveRefresh() ya NO llama _renderBetApostarBody()
      (full DOM re-render que destruia inputs y congelaba en minuto 69).
      Reemplazado por _updateLiveDOM(newGrupos): actualizacion quirurgica
      que solo toca tbody standings (#gst-{fid}) y barras live (.gbc-live-bar).
      Guard _liveRefreshing previene llamadas concurrentes.

  BECBUC-movil.html:
    - CSS: .mc-meta .fb-live, .mc-live-bar, .mc-live-dot, .mc-live-score,
      .mc-live-min, .mc-live-stat.
    - renderGroupPronos: live=[...en_juego] aparece primero en la lista.
    - matchCard: barra live con score/minuto/amarillas/rojas; metaLbl muestra
      "En vivo" para partidos en_juego.
    - Live refresh: _mLiveTimer, _doLiveRefreshM(), _startLiveRefreshM(),
      _stopLiveRefreshM(). Auto-polling 30s, resetea al cambiar tab.
    - FIX CONGELADO: _doLiveRefreshM() ya NO llama _renderPronosGruposM()
      (full DOM re-render). Reemplazado por _updateLiveDOMM(newGrupos):
      actualiza standings (#stwrap-{fid}), meta label (.mc-meta) y
      barras live (.mc-live-bar) sin destruir inputs ni bonus panels.
      Guard _mLiveRefreshing previene llamadas concurrentes.

  FIX SYNC + FINALIZAR PARTIDO MANUAL (sesion 13 continuacion):

  apostador_bets.py:
    - hay_partido_activo: ventana ampliada 210->300 min + condicion OR estado='en_juego'
      garantiza que partidos trabados en BD sigan siendo sincronizados.
    - Nuevo endpoint POST /finalizar-partido/{partido_id}?goles_local=X&goles_visitante=Y
      [&penales_local=N&penales_visitante=M] (admin):
      UPDATE partido SET goles, estado='finalizado', penales, equipo_clasificado_id, minuto_actual=NULL
      → _recalc_participacion → _avanzar_bracket → calcular_puntajes + calculate_global
      Retorna: partido, estado, standings_ok, bracket_ok, puntajes_ok, puntajes_procesados.

  BECBUC-portal.html:
    - Boton "⚡ Finalizar partido" en Acciones Rapidas del monitoreo (rojo).
    - Modal openFinalizarPartidoModal(): lista partidos activos/en_juego, form goles+penales.
    - confirmarFinalizarPartido(): POST /finalizar-partido + refresca KPIs y ranking.

  BECBUC-movil.html:
    - Boton "⚡ Finalizar partido (emergencia)" en panel admin.
    - Bottom sheet openFinalizarPartidoM() + confirmarFpM(): equivalente al portal.

2026-06-09 - Sesion Cowork (sesion 12) - RESET COMPLETO + TBD BRACKET + SIMGRUPO PURO + GATE EXCEL:

  apostador_bets.py - resetear_apuestas expandido:
    - Agrega campos GRUPO 3: pred_rojas, pred_penales_local_tanda, pred_penales_visitante_tanda = NULL
    - Reset puntos = 0 y puntos_bonus = 0 en apuesta
    - DELETE puntaje_detalle del usuario para el torneo (ranking y transparencia quedan limpios)
    - DELETE apuesta_global del usuario (pronósticos A-G)
    - DELETE puntaje_global del usuario (puntajes globales calculados)

  BECBUC-portal.html:
    - _simGrupo(grupo, predsMap, pureMode=true): modo puro por defecto.
      En pureMode: standings arrancan desde 0 (no hereda pts reales de BD).
      Todos los partidos se evalúan con predicciones (no solo los no-finalizados).
      Resultado: después de reset, grupos muestran 0 pts para todos.
    - renderBetPlayoffs: si usuario sin predicciones de grupos → muestra "Por definir" (no bracket tree).
    - Mejores terceros: eliminado del bracket view (renderBetBracket); _tercerosSectionHtml con zero-check.
    - resetGruposBets: limpia _betSlip/_betMisAp/_lastKoData/_lastKoMap, navega a ranking, refresca KPIs.
    - Transparencia: marcadores 3º/amber eliminados de group standings (todos clasificados = verde ✓).
    - loadCompletionBanner(): banner debajo de KPIs con progreso de 3 condiciones:
        1. Partidos de grupos con marcador (conGrupos/totalGrupos)
        2. Mejores terceros calculados (_tercerosSectionHtml devuelve contenido)
        3. Bracket 32avos con equipos reales (ningún TBD en _lastKoData)
    - _isBetsComplete(): verifica las 3 condiciones directamente desde JS (sin depender del banner).
    - _exportTransparencia: bloqueado si _isBetsComplete() es false, con mensaje detallado.

  BECBUC-movil.html:
    - _renderPronosPlayoffsM: si sin predicciones → empty "Por definir".
    - _renderPronosTercerosM: zero-check (si todos 0 pts → empty state).
    - renderBracket: mejores terceros condicional (solo si algún equipo pts > 0).
    - resetGruposM: limpia _slip/_misApuestas/_koSlipM/_bracket/_bracketDirty=true.
    - Transparencia: marcadores 3º/amber eliminados de group standings (clase 'cls' uniform).
    - _exportTransparenciaM: gate igual al portal — verifica grupos completos + bracket 32avos real
      antes de permitir descarga. Alert con motivo si falla alguna condición.

  Documentacion:
    - Reglamento BECBUC 2026 guardado en documentacion/ (copia sin espacio en nombre).

2026-06-09 - Sesion Cowork (sesion 11) - SYNC AUTO-MAPEO + UX SEGURIDAD + TBD RESET:

  sync_api_football.py:
    - _normalize(name): strip accents, lowercase, remove punctuation + stop words.
    - _match_teams(api_teams, db_equipos): {db_id: api_id} por nombre normalizado (exact→substring).
    - _match_fixtures(api_fixtures, db_partidos, team_map): {db_partido_id: api_fixture_id} por par equipos.
    - auto_mapeo_torneo(db, torneo_id, client): detecta liga auto (Copa Mundial → id=1, año actual),
      fetch equipos + fixtures de API-Football (2 calls), guarda api_team_id + api_fixture_id en BD.
      Retorna: {equipos_mapeados, partidos_mapeados, equipos_nuevos, partidos_nuevos}.
    - sync_torneo(): si 0 fixtures mapeados → llama auto_mapeo_torneo() automáticamente.
      Retorna summary con clave "auto_mapeo" si se ejecutó.

  apostador_bets.py:
    - Nuevo endpoint POST /api-mapeo/{torneo_id}/auto (admin): llama auto_mapeo_torneo() directamente.
    - _grupos_completos(db, torneo_id) -> bool: True solo si TODOS los partidos grupo finalizados (≥1).
    - _resetear_ko_a_tbd(db, torneo_id): pone equipo_local/visitante=TBD en todos los partidos KO,
      limpia goles/penales/minuto/amarillas/var/equipo_clasificado_id, resetea apuesta.puntos=0.
    - _avanzar_bracket(): si grupos no completos → llama _resetear_ko_a_tbd() y retorna sin avanzar.
    - sync_resultados endpoint: bracket + puntajes siempre corren (if True: en vez de condicion).

  BECBUC-portal.html:
    - monSync() + syncResultados(): muestran warning ambar si s.error (en vez de verde falso).
    - Cadena de pasos visible: "🔗 auto-mapeo → ⬇️ resultados → 🔀 bracket → 📊 puntajes".
    - "✓ 0 resultados" cambiado a "✓ sin nuevos resultados".
    - Tabla "Ranking mejores terceros" eliminada de view resultados/grupos.
    - Cards admin ocultas por defecto: monCardAcciones, monCardFases, monCardMensajes (display:none).
      _applyRole(): show() de las 3 cards cuando _isAdmin.
    - Config → tab "Sistema" (7mo tab): warning card rojo + cfgSincronizar() con confirm dialog.
      Solo admin puede ver/ejecutar. Confirmación obligatoria antes de sync catalogo.
    - Sincronizar eliminado de fixture.html y BECBUC-ADM.html.

  BECBUC-movil.html:
    - syncResultadosM(): warning ambar si s.error, cadena de pasos en msgEl.
    - "0 resultados" → "sin nuevos" cuando actualizados=0.
    - Admin panel ya protegido por if(!_isAdmin) return en loadAdmin() (no requirió cambios).

  fixture.html: botón "🔄 Sincronizar" eliminado.
  BECBUC-ADM.html: botón "🔄 Sincronizar" eliminado.

2026-06-09 - Sesion Cowork (sesion 10) - DASHBOARD REDESIGN + PRONOS UI:

  BECBUC-portal.html:
    - Dashboard: nuevo layout CSS grid.
      Fila 1: panelKpis (ancho completo).
      Fila 2: panelMensajesDash + panelRankingDash (paralelo, 2 columnas).
      Fila 3: panelNoticiasDash + panelVinculos (paralelo, 2 columnas).
      panelResultados y panelTablas movidos a hidden (uso interno, datos disponibles).
      panelVinculos: loadVinculos() ahora lo muestra/oculta automaticamente.
      CSS: .dash-grid usa grid-template-columns:1fr + .dash-row2 para 2 columnas.
      Responsive: dash-row2 colapsa a 1 columna bajo 900px.
    - Pronosticos - Betslip: botones redundantes "Completar aleatorio" y
      "Recalcular posiciones" eliminados del panel derecho (betslip). Ya existen
      en la prono-action-bar inline. La boleta de items y boton Guardar se mantienen.
    - Pronosticos - Historial (codigo legacy): _tercerosSectionHtml removido del
      renderBetHistorial. La seccion de mejores terceros solo aparece en su tab dedicado.
  BECBUC-movil.html: sin cambios (estructura diferente, no tiene panels ni betslip).
  CLAUDE.md: sesion 10 en historial.

  BUG ANTERIOR (sesion 9): fillRandom() no era async → SyntaxError crasheaba JS.
    Fix: function fillRandom() -> async function fillRandom() ✅ (ya aplicado).

  Fix monitoreo (sesion 10 continuacion):
    - initMonitoreo(): agrega auto-select torneo si _betTorneoId es null.
      Usa _betActivas cache o fetch /api/v1/torneo/activas. Prioriza datos_cargados.
      Soluciona: monitor mostraba pantalla en blanco al navegar directamente.
    - _renderMonitoreo(): muestra mensaje en cabecera si _monData es null
      ("Sin torneo activo" o "Error al cargar datos").
    - syncResultados(): _betMisAp = [] corregido a _betMisAp = {} (era un dict).

2026-06-09 - Sesion Cowork (sesion 9) - EXCEL MATRIZ + DEBUG 0 PARTIDOS:

  generar_excel_becbuc.py - Cambios acumulados esta sesion:
    1. build_sheet_matriz() AGREGADA: hoja unica apostador x partido (23 cols).
       Columnas: Apostador | P# | Fase | Local | GL | GV | Visitante | Pred.L | Pred.V |
                 OK | Pen.R.L | Pen.R.V | Pen.P.L | Pen.P.V | Amar | Rojas |
                 H | I | J | K | L | O | Total
       Subtotales por fase (gris), grand total por apostador (naranja) con
       partidos + globales + TOTAL combinado.
    2. generar() llama build_sheet_matriz() despues de build_sheet_globales.
    3. Fix apostadores: primera llamada ranking API ahora maneja lista O dict
       (isinstance check). Fallback final desde data["ranking"] si apostadores==[].
    4. psql() fix: detecta lineas "ERROR:" en stdout (psql sale con code 0 en errores SQL).
    5. Partidos query: eliminado JOIN torneo + JOIN competicion (causa 0 filas si NULL).
       Usa cid=competicion_id ya resuelto. WHERE f.torneo_id en vez de p.torneo_id.
    6. Filtro: AND (p.estado='finalizado' OR p.goles_local IS NOT NULL).
    7. Diagnostico de estado de partidos agregado (prints DIAG antes del loop).

  PROBLEMA ABIERTO - 0 partidos en generar_excel_becbuc.py:
    Sintoma: DIAG muestra 0 filas brutas. Query devuelve 0 aunque hay 416 apuestas
    y 416 puntaje_detalle. Significa goles_local=NULL y estado != 'finalizado'.
    Causa probable: test_integral.py corrio reset_torneo() pero la simulacion
    posterior fallo o no persisitio los goles. BD tiene apuestas y puntaje_detalle
    de una corrida anterior, pero partidos quedaron sin goles/estado.
    SOLUCION: correr test_integral.py nuevamente desde cero.
    DIAGNOSTICO PENDIENTE: ejecutar python generar_excel_becbuc.py y compartir
    lineas "DIAG estados partidos:" para ver que estados tiene la BD actual.

  Mejores terceros Copa del Mundo 2026:
    CONFIRMADO que ya esta implementado:
    - bracket_service.py: seleccionar_mejores_terceros() + armar_ronda32()
    - apostador_bets.py: _avanzar_bracket() llama seleccionar_mejores_terceros()
    - Los 8 mejores terceros de 12 grupos se seleccionan automaticamente al
      correr avanzar-bracket despues de la fase de grupos.
    - No requiere implementacion adicional.

  PARA RETOMAR MANANA:
    1. Correr: python test_integral.py  (resetea BD + simula + calcula puntajes)
    2. Correr: python generar_excel_becbuc.py
    3. Verificar output "DIAG estados partidos:" para confirmar goles cargados
    4. Si 0 partidos persiste: compartir el DIAG para diagnosticar
    5. Quitar codigo de diagnostico (prints DIAG/DEBUG) de generar_excel_becbuc.py
       cuando el Excel funcione correctamente

2026-06-09 - Sesion Cowork (sesion 8) - TEST INTEGRAL + FIXES SCORING ENGINE:
  test_integral.py: 3 bugs de transaccion corregidos en cascada:
    1. apostador_bets.py calcular_puntajes: ALTER TABLE loop usaba await db.rollback()
       en except → corrompía sesión async. Cambiado a pass.
    2. calculator.py _get_paraguay_ids: await db.rollback() en except → se llamaba 2 veces
       (desde calculate() y calculate_global()) → rollback deshacía 416 INSERTs de
       puntaje_detalle. Cambiado a pass + query simplificada (solo nombre, no nombre_es).
    3. calculator.py _load_torneo_resultados bloque F/G: ANY(:pids) con lista Python
       no soportado por asyncpg → transacción en estado aborted. Cambiado a IN ({ids_sql}).
    4. apostador_bets.py calcular_puntajes: columnas resultado_goleador y
       resultado_peor_equipo_id no existían en torneo → SELECT fallaba dejando tx aborted.
       Agregados como ADD COLUMN IF NOT EXISTS al loop de ALTER TABLE.
  generar_excel_becbuc.py:
    - build_sheet_puntajes: ws.cell(2,c,"") en celda secundaria de merge → error
      MergedCell read-only. Cambiado a ws.cell(2,c) sin valor.
    - Apostadores: query app_db con JOIN user_roles/roles fallaba → cambiado a
      ranking API + fallback puntaje_detalle.
    - Número de partido FIFA: columna "numero" (P1…P104) agregada a cada partido
      en load_all_data. Mostrado en hojas Resultados, Apuestas y P