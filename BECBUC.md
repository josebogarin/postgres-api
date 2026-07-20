# BECBUC.md - Estado del Proyecto BECBUC
Ultima actualizacion: 2026-06-08 (sesion 3)
Leer este archivo COMPLETO antes de tocar cualquier archivo.

## RETOMAR - PENDIENTES ABIERTOS (al 2026-06-08 sesion 3)

HECHO sesion 2026-06-08 (parte 3) - FIX ALGORITMO BRACKET PLAYOFFS, VERIFICADO LIVE (torneo 2):

  PROBLEMA (reportado por usuario): el bracket KO arrastraba equipos OBSOLETOS de
  simulaciones previas. Convencion: Wnn = ganador del partido nn (P1..P104 secuencial).
  KO_FEEDERS, armar_ronda32, build_num_maps y los renderers de bracket estaban TODOS
  CORRECTOS (verificados vs bracket oficial FIFA 2026). La causa raiz era ko_scoring._set_teams:
  su guard "WHERE estado <> 'finalizado'" impedia re-propagar ganadores a partidos aguas
  abajo ya finalizados -> quedaban equipos viejos (p.ej. R16 89/90/91/92/96 con PERDEDORES
  de sus feeders R32). El bracket NO era funcion pura de los resultados actuales.

  FIX en ko_scoring.py:
    - _set_teams REESCRITO (self-heal): si equipos almacenados == nuevos -> no-op (conserva
      resultado jugado); si DIFIEREN -> reasigna equipos + limpia el resultado de ESE partido
      (estado='programado', NULL goles/goles_*_prorroga/penales/minuto_primer_gol/amarillas/
      decisiones_var) + pone en cero puntos/puntos_bonus de las apuestas de ese partido.
      Asi las rondas profundas obsoletas se auto-corrigen EN CASCADA.
    - _tbd_id(db) helper (cachea id equipo nombre='TBD', placeholder 'Por Definir').
    - avanzar_ronda32 / avanzar_fase_ko: si el feeder (ganador/perdedor o clasificado) es
      None, escriben TBD en vez de saltar -> el "por definir" cascadea limpiando rondas
      profundas. Columnas NOT NULL siempre reciben valor.

  HEAL de datos viejos: POST /api/v1/bets/avanzar-bracket/{torneo_id} (admin) dispara el
  self-heal sobre datos existentes sin re-simular.

  VERIFICADO LIVE torneo 2:
    - ANTES: ~10 mismatches de feeders en R16/QF/SF/Final (89,90,91,92,96,97,98,99,101,102).
    - POST avanzar-bracket -> R32+ reseteados a matchups correctos derivados de standings
      actuales (programado, TBD aguas abajo). bad=0.
    - POST simular-secuencial/2/145 (hasta Final) -> 16 partidos KO finalizados,
      feeder_mismatches=0 (incl. 3er puesto = perdedores de semis). Final: England 0-1 Türkiye.
    - bracket-real: 0 TBD / 0 null tras simulacion completa. El bracket es funcion pura
      de los resultados. Portal y movil consumen el mismo endpoint -> en sync (sin cambio UI).

## RETOMAR - PENDIENTES ABIERTOS (al 2026-06-07 sesion 2)

HECHO sesion 2026-06-07 (parte 2), VERIFICADO LIVE (torneo 2, 4 apostadores, 104 partidos):

Backend (apostador_bets.py):
  - FIX bug "Secuencial hasta aqui": _calc_pts (~l.1284 dentro de calcular_puntajes)
    crasheaba con 'NoneType > NoneType' por apuestas placeholder (pred NULL que crea
    verificar_registros). Guard: si algun pred/real es None -> 0 pts. Cubre tambien
    Simular etapa, Secuencial y Calcular puntajes.
  - EXCEL DE AUDITORIA UNIFICADO: nuevo helper _build_auditoria_workbook(db, torneo_id)
    (justo despues de _PHASE_LABELS_FULL, ~l.1925). Devuelve (Workbook, torneo_nombre).
    Formato UNICO en TODAS las salidas de export:
      * Hoja 1 "Puntaje general": apostadores activos (incl. 0 pts) con sumatoria
        Marcador + Bonus partido + Bonus 3ros = Total, rankeada desc.
      * Una hoja por fase (_PHASE_LABELS_FULL). Grupos sub-agrupado por "▣ Grupo X".
        Por partido: header "⚽ Jn · Local vs Visit · Real x-y · xMult", luego 3 buckets
        en orden (3,1,0) clasificados por pts_marcador_base:
        ✅ PLENO (marcador exacto) / ➕ GANADOR (acerto resultado) / ✗ CERO ACIERTO.
        Cols por apostador: Apostador, Pronostico, Marcador, Min, Amar, VAR, Bonus, Total.
        Dentro de cada bucket: orden por pts_total desc, luego nombre.
  - ORDEN JERARQUICO DE BRACKET (R32+): dentro del helper KO_BRACKET_ORDER ordena los
    partidos KO con el MISMO orden visual izquierda->derecha de pronosticos/resultado
    (_renderBracketTree del portal), mapeando via build_num_maps (pid2num). Orden por
    num FIFA: ronda32 [74,77,73,75,83,84,81,82,76,78,79,80,86,88,85,87];
    ronda16 [89,90,93,94,91,92,95,96]; cuartos [97,98,99,100]; semis [101,102];
    tercer_puesto [103]; final [104]. Grupos siguen (jornada, partido_id).
    VERIFICADO: octavos y cuartos salen en orden de bracket (ganadores de 89/90 -> 97...).
  - 3 ENDPOINTS UNIFICADOS al helper (mismo Excel): puntos_por_fase_excel (GET,
    FileResponse a /static/exports), exportar_transparencia (GET, StreamingResponse),
    generar_auditoria (POST, guarda /static/auditorias + registra auditoria_apuestas + url).
    transparencia/export y puntos-por-fase/excel ahora byte-identicos. Los 3 dan 200.

ko_scoring.py:
  - FIX "error alchemy" (asyncpg NotNullViolationError en equipo_local_id): _set_teams
    (~l.120). Al simular UNA fase, _avanzar_bracket avanza TODO el bracket; si la fase
    alimentadora no se jugo el ganador es None -> UPDATE ... SET equipo_local_id=NULL
    violaba NOT NULL. Fix: si local_id o visit_id es None, NO ejecuta el UPDATE.
    simular-fase / reset-fase / secuencial -> 200.

HECHO esta sesion (2026-06-07 parte 1), VERIFICADO LIVE:

Backend (apostador_bets.py):
  - _PHASE_LABELS_FULL (titulos largos: "Fase de grupos", "Octavos de final", etc).
  - _audit_log(action, resource, ...) helper -> inserta en app_db.audit_logs (CAST json).
  - Logging rico: simulacion:grupos/fase/secuencial, avance:bracket, puntajes:calculo,
    reset:fase/torneo, *:bloqueada (warnings de modificacion en fase encerrada).
  - _fase_encerrada(db, fase_id): True si una fase con orden mayor ya tiene finalizados.
    Usado en simular_resultados/simular_fase/reset_fase -> 409 + audit warning.
  - verificar_registros (GET/POST /verificar-registros/{torneo_id}, ?reparar=bool):
    asegura placeholder en apuesta para todo apostador activo x partido de grupo.
  - reset_torneo: paso 5 re-crea placeholders apuesta tras borrar (rehabilita carga).
  - exportar_transparencia (GET /transparencia/{torneo_id}/export): Excel.
    REESTRUCTURADO: hoja por fase agrupada por partido (encabezado equipos+real+xM),
    apostadores rankeados desc por pts_total dentro de cada partido (#1 en verde).
    Cols: #,Apostador,Pronostico,Marcador,Min,Amar,VAR,Bonus,Total.
    Hoja "Ranking general" (idx 0): ficha subtotales por item por apostador, rankeada.
  - fases_apuesta_estado (GET /fases-apuesta-estado/{torneo_id}, cualquier user):
    por fase {bloqueada, motivo, icono}. Bloqueada si: periodo vencido (todos los
    partidos ya comenzaron / fase concluida) o equipos sin clasificar (fase previa
    con partidos no concluida). Devuelve fase_habilitada_id.

Frontend portal + movil (AMBOS, REGLA UI):
  - Transparencia: titulo "Fase de grupos" (no "Grupo A"), nombre apostador grande
    destacado, boton "Exportar Excel" (_exportTransparencia / _exportTransparenciaM).
  - Panel admin: boton "Verificar/habilitar registros" (verificarRegistros[M]).
  - Pronosticos: tira de chips de estado por fase (🔓 habilitada / 🔒 bloqueada,
    tooltip motivo). Portal: _faseEstadoChips(). Movil: faseEstadoChipsM() + CSS .fe-*.

PENDIENTE (no empezado o a medias):
  - Bloqueo de edicion en fases encerradas: backend HECHO; falta deshabilitar inputs
    en el frontend para fases bloqueadas (usar fases-apuesta-estado).
  - #22 Dashboard: panel resultados actuales + partidos de la fase en juego.
  - #23 Indicadores: cuadrar menu vertical vs panel + verificar reset.
  - #27 Monitoreo: botones globales "RESET todo" y "SIMULAR todo".
  - #28 Fechas de apuesta inicio/fin por fase en BD + mensajes automaticos.
  - #30 Reglas de puntaje configurables por fase (BD + UI Monitoreo).

VERIFICADO live esta sesion: Excel unificado (3 endpoints 200, byte-identicos), orden
de bracket KO correcto, andres y los 4 apostadores aparecen en "Puntaje general".
Bug "Secuencial" y "error alchemy" corregidos y probados (simular/reset/secuencial 200).

Credenciales test: superadmin user 'admin' pass 'faute'.
Nota entorno: el mount bash de apostador_bets.py esta STALE/truncado (~linea 1050);
py_compile da falsos errores. Verificar con Read/Edit y servidor live (openapi.json),
NO con bash. Sandbox Python 3.10; proyecto corre 3.12.

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
C:\proyecto FAST API\documentacion\  <- SQLs, manuales PDF, seeds
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

## BASE DE DATOS becbuc - Estado al 2026-06-05

Tablas activas (9):
  competicion       -> tipos de torneo
  torneo            -> instancia especifica del torneo
  equipo            -> selecciones/clubes + codigo_iso, fifa_ranking, fair_play_pts
  fase              -> etapas (grupos, r32, r16, cuartos, semis, final)
  partido           -> fixture + minuto_primer_gol, amarillas, decisiones_var
  participacion     -> equipos por grupo/fase
  apuesta           -> pronosticos + pred_minuto_gol, pred_amarillas, pred_var, puntos_bonus
  auditoria_apuestas -> snapshots Excel
  mensaje_admin     -> mensajes admin a apostadores (en becbuc, NO en app_db)

Tablas eliminadas (NO existen mas):
  competencias, fases, grupos, equipos, partidos (plurales fixture_sync)
  partido_estadistica, partido_evento, torneo_equipo, jugador_estadistica

Vistas activas (12):
  V_DIM_TORNEO, V_DIM_EQUIPO, V_DIM_FASE, V_DIM_PARTIDO
  V_HECHOS_APUESTAS      <- tabla de hechos principal para analytics
  V_RANKING_TORNEO, V_RESUMEN_PARTIDO, V_STANDINGS_GRUPOS, V_CALENDARIO
  V_AUDITORIA_PRONOSTICOS, V_AUDITORIA_PUNTAJES (CTE fix aplicado), V_MEJORES_TERCEROS

Base de datos app_db (tablas relevantes para BECBUC):
  users, sistema, diccionario, portal_kpis, portal_vinculo, portal_menu, catalogo_objeto

## MIGRACIONES - Estado al 2026-06-05

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

Pendientes: Ninguno al 2026-06-05

## PORTAL - BECBUC-portal.html

Vistas:
  view-dashboard   -> Dashboard (todos)
  view-pronos      -> Pronosticos (apostadores)
  view-grupos      -> Grupos (todos)
  view-bracket     -> Resultados bracket (todos)
  view-ranking     -> Ranking (todos)
  view-noticias    -> Noticias (todos)
  view-mensajes    -> Mensajes (todos)
  view-config      -> Configuracion (admin+)
  view-herramientas -> Herramientas (admin+)

Funcionalidades al 2026-06-05:

Dashboard:
  - Ranking apostadores: # Apostador Plenos Aciertos Bonus Terceros Pts
  - KPIs SQL configurables (panel + sidebar)
  - Hipervinculos en sidebar: FIFA, ABC Color, Ultima Hora + configurables
  - Noticias debajo del ranking

Pronosticos (antes Apuestas):
  - Solo muestra grupos con partidos pendientes
  - Boleta oculta en Resultados y Ranking
  - Modal bonus por partido: minuto gol / amarillas / VAR
  - Partidos finalizados: resultado real + iconos vs prediccion

Resultados Bracket:
  - R32: paises segun pronosticos del usuario
  - R16+: criterios FIFA (W73, W74...) no simula mas alla de R32
  - Bracket oficial FIFA 2026 Arts 12.6-12.11
  - Tabla mejores terceros

Ranking:
  - Plenos(+3) Aciertos(+1) Bonus partido Bonus terceros Total
  - Todos los apostadores aparecen aunque tengan 0 puntos
  - Columnas bonus siempre visibles

Noticias:
  - Selector paises: Paraguay Argentina Brasil Mexico Espana
  - Paraguay Argentina Brasil activos por defecto
  - Proxy cascada: rss2json -> allorigins -> corsproxy
  - Preferencia en localStorage

Mensajes:
  - Badge sidebar con no leidos
  - Preview ultimos 3 en dashboard
  - Modal creacion solo admin
  - Soft delete solo admin

Configuracion admin:
  - KPIs Vinculos Menu: CRUD + doble clic para editar
  - Cabecera/Detalle: doble clic existia

Herramientas admin:
  - tabla.html: arbol DB->tablas, abre sin ?tabla= en URL
  - Diccionario con alias
  - api-reference.html en /static/
  - Reglamento FIFA: /static/docs/wc-2026-regulations.pdf

## BACKEND - Archivos clave

apostador_bets.py  <- /bets/* pronosticos, ranking, scoring, mensajes
admin.py           <- /admin/* db-tables, seed-catalogo
deps.py            <- CurrentUser, CurrentAdmin, CurrentSuperuser
torneo_service.py  <- logica torneo, fixture, standings
bracket_service.py <- tiebreaker FIFA completo
table_crud.py      <- CRUD generico tabla.html

Endpoints clave:
  POST /api/v1/auth/login
  GET  /api/v1/bets/mis-apuestas/{torneo_id}
  POST /api/v1/bets/guardar-apuestas
  GET  /api/v1/bets/grupos/{torneo_id}
  GET  /api/v1/bets/mi-bracket/{torneo_id}
  GET  /api/v1/bets/ranking/{torneo_id}
  GET  /api/v1/bets/apostadores
  GET  /api/v1/bets/stats/{torneo_id}
  POST /api/v1/bets/simular-resultados/{torneo_id}  <- admin
  POST /api/v1/bets/calcular-puntajes/{torneo_id}   <- admin
  GET  /api/v1/bets/mensajes
  POST /api/v1/bets/mensajes                         <- admin
  DELETE /api/v1/bets/mensajes/{id}                  <- admin
  GET  /api/v1/admin/db-tables                       <- CurrentAdmin
  POST /api/v1/admin/seed-catalogo

Fix 5-jun: db-tables, list_rows, patch_row, delete_row usan CurrentAdmin

## BUGS CONOCIDOS

bracket_service.py -> _sort_grupo():
  Aplica gd/gf global ANTES de H2H
  Segun Art.13 FIFA deberia ser al reves
  Fix requiere reestructurar (trabajo futuro)

## SISTEMA DE PUNTUACION

  Marcador exacto (pleno):       3 pts
  Ganador correcto (acierto):    1 pt
  Fallo:                         0 pts
  Mas terceros acertados:       +10 pts (bonus unico)
  Minuto primer gol:             variable (mas cercano gana)
  Amarillas exacto:              1 pt
  VAR si/no:                     1 pt

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

### Prioridad proxima sesion
  A. Interfaz movil de apuestas (HTML optimizado celular): pronos, ranking, grupos, mensajes
  B. URL fija becbuc.lambdapy.org -> pendiente respuesta soporte Microsoft (cambio nameservers a Cloudflare)
     Nameservers Cloudflare: delilah.ns.cloudflare.com / watson.ns.cloudflare.com
     Nameservers actuales Microsoft: ns1-4.bdm.microsoftonline.com
     Solicitud enviada a soporte Microsoft. Cuando respondan -> configurar Cloudflare Tunnel en 10 min.
     Archivo: C:\proyecto FAST API\soporte_microsoft_nameservers.md

### Pendientes tecnicos
  1. Cargar fixture real playoff desde api-football.com (32 partidos R32->Final)
  2. Fix tiebreaker H2H en bracket_service.py segun Art.13 FIFA
  3. Sincronizacion automatica resultados desde API
  4. Seed catalogo_objeto: POST /api/v1/admin/seed-catalogo?id_sistema=<ID>
  5. Poblar equipo.codigo_iso y equipo.fifa_ranking con datos reales

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

## HISTORIAL SESIONES

2026-06-08 - Sesion Cowork (parte 3):
  - FIX ALGORITMO BRACKET PLAYOFFS (reportado por usuario: equipos obsoletos
    arrastrados, comprometiendo apuestas y simulacion).
  - Causa raiz: ko_scoring._set_teams con guard "estado <> 'finalizado'" no
    re-propagaba ganadores a partidos aguas abajo ya finalizados. KO_FEEDERS,
    armar_ronda32, build_num_maps y renderers estaban correctos.
  - _set_teams reescrito (self-heal): no-op si equipos iguales; si difieren
    reasigna + limpia resultado (programado, NULL goles/prorroga/penales/bonus) +
    cero puntos apuesta. Cascada auto-corrige rondas profundas obsoletas.
  - _tbd_id helper + avanzar_ronda32/avanzar_fase_ko escriben TBD cuando el feeder
    no esta resuelto (cascadea "por definir", respeta NOT NULL).
  - Heal de datos viejos: POST /bets/avanzar-bracket/{torneo_id}.
  - VERIFICADO LIVE torneo 2: antes ~10 mismatches de feeders; tras avanzar-bracket
    + simular-secuencial hasta Final -> 16 KO finalizados, feeder_mismatches=0
    (incl. 3er puesto). Bracket = funcion pura de resultados. Portal/movil en sync.

2026-06-07 - Sesion Cowork (parte 2):
  - FIX bug "Secuencial hasta aqui": _calc_pts crasheaba 'NoneType > NoneType' por
    apuestas placeholder con pred NULL. Guard de None -> 0 pts.
  - FIX "error alchemy" NotNullViolationError equipo_local_id en ko_scoring._set_teams:
    al avanzar bracket con fase alimentadora sin jugar, no escribir NULL.
  - Excel de auditoria UNIFICADO: helper _build_auditoria_workbook. Hoja "Puntaje
    general" + hoja por fase con buckets Pleno/Ganador/Cero (por pts_marcador_base),
    cols Marcador/Min/Amar/VAR/Bonus/Total. Mismo formato en los 3 endpoints de export
    (transparencia/export, puntos-por-fase/excel, auditoria POST).
  - Orden jerarquico de bracket (R32+) en hojas KO = orden visual d