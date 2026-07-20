$contenido = @'
# BECBUC.md — Estado del Proyecto BECBUC
**Ultima actualizacion:** 2026-06-05
**Leer este archivo COMPLETO antes de tocar cualquier archivo.**

---

## DIRECTORIOS REALES

```
C:\proyecto FAST API\          <- BECBUC (este proyecto, FastAPI)
C:\proyecto FAST API\backend\  <- codigo Python (FastAPI + uvicorn)
C:\proyecto FAST API\backend\static\BECBUC-portal.html  <- portal HTML (~2400+ lineas, todo inline)
C:\proyecto FAST API\documentacion\  <- SQLs de migracion, manuales PDF, seeds
C:\proyecto FAST API\BECBUC.md       <- este archivo

C:\proyectos\                  <- Proyecto RBAC separado (Flask, puerto 5000) -- NO mezclar
```

---

## STACK

| Componente | Detalle |
|---|---|
| Backend | Python + FastAPI + uvicorn (puerto 8000) |
| BD apuestas | PostgreSQL 16 Docker -> base becbuc |
| BD admin | PostgreSQL 16 Docker -> base app_db |
| Contenedor | core-postgres (-U app_user) |
| Portal | HTML estatico unico en /static/BECBUC-portal.html |
| Auth | JWT -- superadmin / admin / apostador |

IMPORTANTE: El rol postgres NO existe en Docker. Siempre usar -U app_user
IMPORTANTE: app_db = administracion/RBAC. becbuc = datos del torneo. Son BDs distintas.

---

## BASE DE DATOS becbuc -- Estado al 2026-06-05

### Tablas activas (9 -- definitivas, ya depuradas)

```
competicion       -> tipos de torneo (Mundial, Champions, etc.)
torneo            -> instancia especifica del torneo
equipo            -> selecciones/clubes
                   + columnas agregadas: codigo_iso, fifa_ranking, fair_play_pts
fase              -> etapas (grupos, r32, r16, cuartos, semis, final)
partido           -> fixture completo con resultados
                   + columnas: minuto_primer_gol, amarillas, decisiones_var
participacion     -> equipos por grupo/fase
apuesta           -> pronosticos de cada apostador por partido
                   + columnas bonus: pred_minuto_gol, pred_amarillas, pred_var, puntos_bonus
auditoria_apuestas -> snapshots Excel generados
mensaje_admin     -> mensajes del admin a apostadores (todos ven lo mismo, sin respuesta)
```

Tablas eliminadas (ya NO existen):
competencias, fases, grupos, equipos, partidos (plurales de fixture_sync),
partido_estadistica, partido_evento, torneo_equipo, jugador_estadistica

### Vistas activas (12 -- prefijo V_)

```
V_DIM_TORNEO           -> dimension torneo + competicion
V_DIM_EQUIPO           -> equipo con ranking FIFA, fair play, URL bandera
V_DIM_FASE             -> fase + torneo + competicion
V_DIM_PARTIDO          -> partido completo con ambos equipos y resultado
V_HECHOS_APUESTAS      -> apuesta + partido + equipos + indicadores de acierto  <- TABLA DE HECHOS
V_RANKING_TORNEO       -> puntos, aciertos y posicion por apostador/torneo
V_RESUMEN_PARTIDO      -> distribucion de pronosticos y efectividad por partido
V_STANDINGS_GRUPOS     -> tabla real de grupos con gd, pts, tiebreaker attrs
V_CALENDARIO           -> todos los partidos ordenados cronologicamente
V_AUDITORIA_PRONOSTICOS -> un pronostico por fila con nombres de paises, fase, resultado
V_AUDITORIA_PUNTAJES   -> igual + puntos por partido, acumulado corrido y posicion (CTE fix aplicado)
V_MEJORES_TERCEROS     -> terceros reales por criterios FIFA con flag clasifica_r32
```

### Base de datos app_db -- tablas relevantes para BECBUC

```
users             -> apostadores (username, email, roles[])
sistema           -> sistemas registrados (multi-tenancy)
diccionario       -> metadatos de campos (tablas + vistas configurables)
portal_kpis       -> KPIs SQL configurables para el dashboard
portal_vinculo    -> hipervinculos del dashboard y sidebar
portal_menu       -> menu dinamico configurable
catalogo_objeto   -> catalogo de tablas/vistas con alias, visibilidad, tipo
```

NOTA: mensaje_admin esta en becbuc, NO en app_db

---

## MIGRACIONES -- Estado al 2026-06-05

### Ya ejecutadas
```
migracion_portal.sql
migracion_portal_menu.sql
migracion_cabecera_detalle.sql
migracion_grupo_calculo.sql
migracion_unificacion_app_db.sql
migracion_user_sistemas.sql
migracion_bonus_partido.sql        -> bonus en apuesta + partido
migracion_mensajes_admin.sql       -> tabla mensaje_admin en becbuc
depuracion_vistas_becbuc.sql       -> drop tablas obsoletas + crear vistas V_
vistas_auditoria_becbuc.sql        -> vistas V_AUDITORIA_* (con CTE fix)
drop_tablas_obsoletas_becbuc.sql   -> torneo_equipo + jugador_estadistica eliminadas
migracion_catalogo_objeto.sql      -> tabla catalogo_objeto en app_db
seed_becbuc_kpis.sql               -> 5 KPIs en portal_kpis de app_db
fix_kpi_titulos.sql                -> corrige encoding de titulos de KPIs
```

### Pendientes
Ninguno conocido al cierre del 5-jun-2026

---

## PORTAL -- BECBUC-portal.html

### Vistas del portal

| ID vista | Nombre visible | Quien la ve |
|---|---|---|
| view-dashboard | Dashboard | todos |
| view-pronos | Pronosticos | apostadores |
| view-grupos | Grupos | todos |
| view-bracket | Resultados (bracket) | todos |
| view-ranking | Ranking | todos |
| view-noticias | Noticias | todos |
| view-mensajes | Mensajes | todos |
| view-config | Configuracion | admin+ |
| view-herramientas | Herramientas | admin+ |

### Funcionalidades implementadas al 2026-06-05

Dashboard:
- Ranking de apostadores: # | Apostador | Plenos | Aciertos | Bonus | Terceros | Pts
- KPIs SQL configurables (panel + sidebar)
- Hipervinculos en sidebar: FIFA, ABC Color, Ultima Hora + configurables desde admin
- Noticias debajo del ranking

Pronosticos (antes llamado Apuestas):
- Solo muestra grupos con partidos pendientes (fase activa)
- Boleta lateral oculta en Resultados y Ranking, visible solo en Pronosticos
- Boton por partido abre modal de bonus (minuto gol / amarillas / VAR)
- Partidos finalizados muestran resultado real + iconos vs prediccion del usuario

Resultados (Bracket):
- R32: muestra paises segun pronosticos del usuario
- R16 en adelante: criterios FIFA (W73, W74, etc.) -- no simula mas alla de R32
- Bracket oficial FIFA 2026 (Arts. 12.6-12.11) con 8 parejas correctas
- Tabla de mejores terceros

Ranking:
- Tabla: # | Apostador | Plenos (+3) | Aciertos (+1) | Bonus partido | Bonus terceros | Total
- Todos los apostadores aparecen aunque tengan 0 puntos
- Columnas bonus siempre visibles (con -- si no hay datos)

Noticias:
- Selector de paises: Paraguay | Argentina | Brasil | Mexico | Espana
- Paraguay, Argentina y Brasil activos por defecto
- Proxy en cascada: rss2json -> allorigins -> corsproxy
- Preferencia guardada en localStorage

Mensajes:
- Badge en sidebar con cantidad no leidos
- Panel en dashboard con preview ultimos 3
- Modal de creacion (solo admin): titulo + contenido
- Soft delete (solo admin)

Configuracion (admin):
- KPIs, Vinculos, Menu: CRUD completo + doble clic para editar
- Cabecera/Detalle: doble clic ya existia

Herramientas (admin):
- tabla.html: arbol izquierdo DB->tablas, abre sin ?tabla= en URL
- Diccionario: configuracion de campos con alias
- api-reference.html: referencia de endpoints en /static/

Reglamento FIFA 2026:
- Guardado en: documentacion/wc-2026-regulations.pdf
- Ruta servida: /static/docs/wc-2026-regulations.pdf

---

## BACKEND -- Archivos clave

```
backend/
   app/
      main.py                    <- registra routers, monta /static
      api/v1/endpoints/
         apostador_bets.py       <- /bets/* (pronosticos, ranking, scoring, mensajes)
         admin.py                <- /admin/* (db-tables, seed-catalogo, etc.)
      core/
         deps.py                 <- CurrentUser, CurrentAdmin, CurrentSuperuser
      services/
         torneo_service.py       <- logica de torneo, fixture, standings
         bracket_service.py      <- tiebreaker FIFA completo
         table_crud.py           <- CRUD generico para tabla.html
   static/
      BECBUC-portal.html
      api-reference.html
      docs/wc-2026-regulations.pdf
      auditorias/                <- Excel generados (sin auth)
   documentacion/
      Manual_Apostador_BECBUC.pdf
      Manual_Administrador_BECBUC.pdf
      Manual_Operacion_BECBUC.pdf
      *.sql
```

### Endpoints clave

```
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
GET  /static/auditorias/{archivo}                  <- sin auth
```

### Niveles de auth (deps.py)

```
CurrentUser      -> cualquier usuario autenticado
CurrentAdmin     -> admin o superadmin
CurrentSuperuser -> solo superadmin
```

Fix 5-jun: db-tables, list_rows, patch_row, delete_row, seed-diccionario
usan CurrentAdmin (antes solo CurrentSuperuser)

---

## BUGS CONOCIDOS

Tiebreaker de grupos (bracket_service.py -> _sort_grupo()):
- Aplica gd/gf global ANTES de H2H
- Segun Art. 13 reglamento FIFA deberia ser al reves
- Fix requiere reestructurar la funcion (trabajo futuro)

---

## SISTEMA DE PUNTUACION

| Evento | Puntos |
|---|---|
| Marcador exacto (pleno) | 3 |
| Ganador correcto (acierto) | 1 |
| Fallo | 0 |
| Mas terceros acertados (bonus unico) | +10 |
| Minuto primer gol (mas cercano gana) | variable |
| Amarillas (exacto) | 1 |
| VAR (si/no) | 1 |

---

## ARRANCAR EL SERVIDOR

```powershell
cd "C:\proyecto FAST API\backend"
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Portal: http://localhost:8000/static/BECBUC-portal.html
```

---

## COMANDOS DOCKER FRECUENTES

```powershell
# Conectar a becbuc
docker exec -it core-postgres psql -U app_user -d becbuc

# Listar tablas y vistas
docker exec core-postgres psql -U app_user -d becbuc -c "\dt"
docker exec core-postgres psql -U app_user -d becbuc -c "\dv"

# Ejecutar migracion
Get-Content "C:\proyecto FAST API\documentacion\archivo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

# Backup
docker exec core-postgres pg_dump -U app_user becbuc > backup_becbuc_20260605.sql
```

---

## PROXIMOS PASOS

1. Cargar fixture real de playoff desde api-football.com (R32 -> Final, 32 partidos)
2. Fix tiebreaker H2H en bracket_service.py segun Art. 13 reglamento FIFA
3. Sincronizacion automatica de resultados desde API cuando lleguen resultados reales
4. Seed catalogo_objeto para cada sistema: POST /api/v1/admin/seed-catalogo?id_sistema=<ID>
5. Poblar equipo.codigo_iso y equipo.fifa_ranking con datos reales

---

## HISTORIAL DE SESIONES

### 2026-06-05 -- Sesion principal en Cowork
- Bracket eliminatorias con arbol oficial FIFA (Arts. 12.6-12.11)
- R32 muestra paises segun pronosticos; R16+ muestra criterios FIFA
- Sistema de scoring: simular resultados aleatorios + calcular 3/1/0
- Ranking con tabla detallada plenos/aciertos/bonus/terceros
- Boleta oculta en Resultados y Ranking
- Pronosticos solo muestran partidos pendientes (fase activa)
- Noticias: selector de paises, feeds deportivos, proxy en cascada
- Dashboard: ranking reemplaza padron, hipervinculos en sidebar
- Mensajes del admin: CRUD, badge, modal, soft delete
- Bonus por partido: modal, inputs minuto/amarillas/VAR, calculo en backend
- tabla.html: arbol carga sin ?tabla=, CurrentAdmin en endpoints DML
- Catalogo de objetos: migracion + seed-catalogo + arbol usa alias
- Doble clic para editar en KPIs, Vinculos y Menu
- BD becbuc depurada: 9 tablas, 12 vistas V_, tablas obsoletas eliminadas
- Manuales PDF actualizados: apostador (15 pags) + administrador (16 pags)
- Fix full_name -> username en endpoint mensajes
- Fix BECBUCSession -> usar DBSession (que ya era BECBUCSession renombrado)
- Fix window function anidada en V_AUDITORIA_PUNTAJES (CTE intermedio)
- Fix encoding KPI titulos (Maximo/Minimo sin tilde)
- Fix _get_engine_for_slug con fallback a DATABASE_URL
- api-reference.html creado en /static/

### 2026-05-23
- Diagnostico de acceso al portal en puerto 8000

### 2026-05-21
- Backend RBAC Flask completo en C:\proyectos (proyecto separado)

---

Actualizado automaticamente al cierre de sesion
'@

$ruta = "C:\proyecto FAST API\BECBUC.md"
[System.IO.File]::WriteAllText($ruta, $contenido, [System.Text.Encoding]::UTF8)
Write-Host "Archivo escrito en: $ruta"
Get-Content $ruta | Select-Object -First 3
