# Assessment de Arquitectura y Calidad — BECBUC

**Fecha:** 2026-07-20
**Contexto:** BECBUC nació como prueba piloto para validar una API FastAPI y se consolidó como producto. El torneo 2026 está **cerrado** (puntajes finales congelados), lo que da una **red de seguridad ideal** para refactorizar: cualquier cambio se puede validar contra un resultado conocido e inmutable.
**Alcance de este documento:** solo *assessment + plan*. No se refactoriza código ni se mueven archivos.

---

## 1. Resumen ejecutivo

BECBUC funciona y cumple su objetivo, pero arrastra la deuda técnica típica de un prototipo que se volvió producto: **la lógica de negocio no tiene un lugar definido** — vive mayormente dentro de los endpoints (con SQL crudo), y está **duplicada** entre el backend (Python) y los frontends (JavaScript). El síntoma más visible es un **"God file"**: `apostador_bets.py`, con **12.775 líneas, 115 endpoints y 356 consultas SQL crudas**, que concentra apuestas, ranking, scoring, sincronización y generación de Excel. Del lado del frontend, hay **4 HTML monolíticos** (23.300 líneas en total) con CSS y JS incrustados y mucha duplicación entre Portal y Móvil.

Nada de esto impide operar, pero sí hace el sistema **difícil de mantener, testear y respaldar**. La buena noticia: ya existen **islas de buena arquitectura** (el motor de scoring con patrón Strategy/Registry, los servicios de bracket/torneo, el módulo monitor) que sirven de modelo a seguir para el resto.

**Recomendación:** un refactor **incremental y verificado por fases**, sin reescritura big-bang. Prioridad 1: introducir una **capa de repositorio** y **partir el God file** en routers finos por dominio. Prioridad 2: **consolidar el frontend** extrayendo un núcleo común y eliminando la duplicación de lógica con el backend. Todo apalancado en un **"golden master"**: el ranking/puntajes final del torneo cerrado como test de no-regresión.

---

## 2. Inventario y métricas de calidad

### 2.1 Backend — archivos más grandes y sus responsabilidades

| Archivo | Líneas | Responsabilidad actual (mezclada) |
|---|---:|---|
| `api/v1/endpoints/apostador_bets.py` | **12.775** | **God file**: apuestas, ranking, scoring, sync, mensajes, Excel de auditoría, live-panel, globales… 115 endpoints + 356 SQL crudos |
| `services/sync_api_football.py` | 2.640 | Sync API-Football + ESPN + parsing de eventos/tarjetas + update de partidos |
| `api/v1/endpoints/admin.py` | 1.399 | CRUD genérico de tablas + DDL/DML + 42 SQL crudos |
| `services/scoring/calculator.py` | 1.177 | Orquestador de scoring (buena separación, pero muy largo) |
| `services/bracket_service.py` | 1.029 | Lógica de bracket KO + tiebreakers FIFA |
| `services/torneo_service.py` | 972 | Standings, fixtures, sync de competiciones |
| `services/table_crud.py` | 486 | CRUD genérico de tablas |
| `services/monitor/*` | ~1.650 | Scheduler, poller, persistence, api_client, state_mapper (bien modularizado) |
| `services/scoring/*` (engines) | ~600 | base + copa_mundo_2026 + default + registry (**referencia de buena arquitectura**) |
| `api/v1/endpoints/portal.py`, `torneo.py` | 423 / 390 | Datos de portal / torneos (con SQL crudo: 18 / 13) |

**Dónde vive hoy la lógica de negocio:** mayormente **en los endpoints**. Evidencia dura:

- **433 llamadas a `text()` (SQL crudo) en la capa de endpoints**, de las cuales **356 están en `apostador_bets.py`**. No hay una capa de repositorio/DAO: los routers arman SQL, aplican reglas y serializan, todo junto.
- El scoring **sí** está bien encapsulado en `services/scoring/` (Strategy + Registry por competencia). Pero el endpoint `calcular-puntajes` y todo el ranking/auditoría vuelven a mezclar SQL + reglas en `apostador_bets.py`.
- `admin.py` expone CRUD genérico + DDL directo — potente pero riesgoso (SQL/DDL desde HTTP).

### 2.2 Frontend — las 4 superficies + legacy

Superficies consolidadas (las 4 que el negocio reconoce):

| Superficie | Archivo | Líneas |
|---|---|---:|
| **Portal** (desktop) | `BECBUC-portal.html` | **11.330** |
| **Aplicación web (móvil)** | `BECBUC-movil.html` | 4.757 |
| **BECBUC Playoff Live** | `becbuc-live-playoffs.html` | 4.279 |
| **BECBUC Live** | `becbuc-live.html` | 2.965 |
| | **Total 4 superficies** | **~23.331** |

Cada una es un **HTML monolítico** con **CSS y JavaScript incrustados** en el mismo archivo. Problemas concretos:

- **Duplicación Portal ↔ Móvil**: hay una "REGLA UI OBLIGATORIA" en el CLAUDE.md que exige tocar los dos archivos en cada cambio de UI. Eso es la señal inequívoca de que **falta código compartido**: se mantiene dos veces lo mismo.
- **Lógica de negocio duplicada backend ↔ frontend**: `becbuc-live.html` reimplementa el **motor de scoring en JS** (`FASE_PTS`, `calcScore`, H/I/J/K/L/M/N/O) que ya existe en Python. Dos fuentes de verdad para las mismas reglas → riesgo de divergencia.
- **Superficies legacy/utilitarias** que inflan el footprint y confunden: `tester.html` (2.267), `tabla.html` (2.915), `diccionario.html` (1.907), `portal.html` genérico (1.913), `importar-apuestas.html` (1.733), `cabecera_detalle.html` (1.496), `fixture.html` (1.270), `apostador.html` (1.306), `BECBUC-ADM*.html`, `config_cabecera.html`, `usuarios.html`, `api-reference.html`, `BECBUC-pronos.html` (huérfano). Muchas son andamiaje del prototipo.

### 2.3 Repositorio / infraestructura / footprint

- **Repos git anidados**: `backend/` y `frontend/` tienen su propio `.git` (gitlinks, sin `.gitmodules`). Consecuencia práctica: los commits del repo padre **no versionan** los cambios de código de `backend/` (el fix del ítem F y el movimiento de backups B1 quedaron sin commitear en el repo de `backend`). **Hay que decidir**: unificar en un solo repo o formalizar submódulos.
- **venv dentro del árbol** (`backend/.venv`) con rutas absolutas hardcodeadas → infla backups y ata el proyecto a la ruta.
- **Cientos de scripts one-off** (ya movidos a `bat/`: 261 `.bat`) + `.py` sueltos de diagnóstico/fix de sesiones pasadas.
- **Backup/recovery pesado**: el ZIP de backup ronda **278 MB** porque arrastra código + generados. Fuentes de peso: `node_modules`, `.venv`, logs (había un `uvicorn_test.log` de **71 MB**), `_backups/`, Excels generados y `static/auditorias/`.
- **Sin tests de la lógica de negocio**: los tests existentes cubren solo el boilerplate (auth, users, roles). El scoring/bracket/ranking —el corazón del producto— no tiene tests.

---

## 3. Code smells concretos (priorizados)

1. **God file** — `apostador_bets.py` (12.775 líneas, 115 endpoints). Imposible de leer, revisar o testear como unidad.
2. **Data access en los routers** — 356 `text()` SQL crudos en endpoints, sin capa de repositorio. Reglas + SQL + serialización mezclados.
3. **Doble fuente de verdad del scoring** — reglas de puntaje en Python *y* en JS (`becbuc-live.html`). Divergen con facilidad (justamente el tipo de bug del ítem F).
4. **HTML monolíticos** — 3k–11k líneas con CSS+JS embebido; sin módulos, sin reutilización, editables solo con herramientas anti-truncación (`safe_write`).
5. **Duplicación Portal/Móvil** — dos implementaciones de la misma UI mantenidas en paralelo por regla manual.
6. **Generación de reportes (Excel) dentro de endpoints** — `_build_auditoria_workbook` y afines viven en el God file.
7. **DDL/SQL arbitrario expuesto por HTTP** — `admin.py` permite operaciones de esquema desde la UI; útil en prototipo, riesgoso en producto.
8. **Footprint de repo/backup inflado** — generados y dependencias mezclados con el fuente; repos anidados; venv en el árbol.
9. **Ausencia de tests de dominio** — no hay red de seguridad automatizada para el core.

---

## 4. Arquitectura objetivo

### 4.1 Backend por capas (dónde vive cada cosa)

```
HTTP → Router (fino)  →  Service (dominio)  →  Repository (datos)  →  DB
             │                  │                     │
        valida/serializa   reglas de negocio     SQL / ORM encapsulado
```

- **Routers (finos):** solo parsean request, invocan un service y devuelven la respuesta. **Cero SQL, cero reglas.** Objetivo: ningún `text()` en `api/v1/endpoints/`.
- **Services (dominio BECBUC):** las reglas viven acá. Ya existe el ejemplo a imitar: `services/scoring/` (Strategy + Registry). Faltan sus pares: `bets_service`, `ranking_service`, `sync_service` (ya empezado), `reportes_service` (Excel).
- **Repositories:** encapsulan el acceso a datos (SQLAlchemy). Un repo por agregado: `ApuestaRepo`, `PartidoRepo`, `PuntajeRepo`, `TorneoRepo`, `RankingRepo`. Todo el SQL crudo migra acá.
- **Models / Schemas:** ya existen y están razonables.

**Qué es "backend clásico" (infra, reusable, estable):** autenticación/JWT, usuarios, roles, permisos, CRUD genérico, auditoría, config, sesión de BD. Esto ya está bien ubicado en `app/core`, `app/crud`, `app/api` (auth/users/roles). **No es dominio BECBUC** y conviene mantenerlo aislado y quieto.

**Qué es "dominio BECBUC" (el producto):** apuestas, scoring, bracket/KO, torneo/fases, ranking, globales, sincronización, reportes. Es lo que hay que **sacar del God file** y llevar a services + repositories.

### 4.2 Frontend — 4 superficies con núcleo común

Las 4 superficies comparten hoy, copiado y pegado, mucho más de lo que debería:

- **Cliente API** (fetch + manejo de JWT + `ngrok-skip-browser-warning` + manejo de 401).
- **Formato e i18n** (fechas UTC→local, banderas por ISO/Twemoji, labels de fase).
- **Componentes de visualización**: tabla de ranking, ficha de partido, desglose de puntajes por ítem (H–O), árbol de bracket SVG.
- **Reglas de puntaje** (hoy reimplementadas en JS).
- **Tema/CSS** (paletas, tarjetas, chips de estado).

**Objetivo:** extraer un núcleo compartido — p. ej. `static/js/becbuc-core.js` (cliente API + formato + componentes) y `static/css/becbuc.css` — y que las 4 superficies lo consuman. Con eso:

- **Desaparece la "REGLA UI OBLIGATORIA"**: se cambia una vez, no dos.
- **Una sola fuente de verdad del scoring**: el frontend **consume los puntajes del backend** en vez de recalcular. La simulación en vivo puede quedar como *preview* explícito, claramente separado del puntaje oficial.
- Cada superficie queda como una *shell* delgada + su lógica específica.

Decisión a tomar (fuera de este assessment): mantener HTML+JS vanilla modularizado (más liviano, menos build) **vs.** consolidar en el `frontend/` que ya tiene `node_modules` (framework). Para la meta "robusto, liviano, mantenible", **vanilla modularizado** es el camino de menor fricción salvo que se quiera invertir en un framework.

---

## 5. Plan de reducción / limpieza (footprint de backup & recovery)

Objetivo: que un backup/recovery sea **chico y rápido** (solo lo necesario para reconstruir el sistema).

**Sacar del repo y del backup de código** (van por otro canal): `node_modules`, `.venv`, `*.log`, `_backups/`, `static/auditorias/*`, Excels generados, dumps. El `.gitignore` ya cubre parte; falta afinar (`_backups/` y outputs ya agregados hoy).

**Reducir/consolidar fuente:**
- **Partir `apostador_bets.py`** por dominio en routers finos: `bets`, `ranking`, `scoring_admin`, `sync_admin`, `reportes/excel`, `live`, `globales`. Cada uno delega a su service.
- **Extraer el JS/CSS** de los 4 HTML a archivos servidos aparte + núcleo común → los HTML pasan de 4k–11k líneas a *shells* de cientos de líneas.
- **Retirar superficies legacy** no usadas en producción (evaluar una por una: `tester`, `portal.html` genérico, `cabecera_detalle`, `config_cabecera`, `fixture`, `api-reference`, `BECBUC-pronos` huérfano…). Mover a un archivo o borrar.
- **Consolidar los scripts**: dejar en la raíz solo la infraestructura viva (`sync_auto.py`, `safe_write.py`, `backup_becbuc.ps1`, `generar_excel_becbuc.py`, arranque); el resto (ya en `bat/`) puede archivarse/borrarse con el torneo cerrado.

**Backup separado por naturaleza:** (a) **código** (repo git, liviano), (b) **datos** (dumps de BD, versionados aparte), (c) **generados** (no se respaldan, se regeneran). Hoy están todos mezclados en un ZIP de 278 MB.

**Repos anidados:** decidir **unificar** `backend/`+`frontend/` en un solo repo (más simple para backup/recovery) o formalizar submódulos con `.gitmodules`. La situación actual (gitlinks sin registrar) es la peor de las dos: confunde y hace que commits del padre no versionen el hijo.

---

## 6. Roadmap por fases (riesgo + verificación)

Cada fase termina con verificación. **Red de seguridad transversal:** el **golden master** = ranking + `puntaje_detalle` + `puntaje_global` del torneo cerrado. Se congela hoy como snapshot; después de cada fase se recalcula y se compara: **debe dar idéntico**.

**Fase 0 — Higiene de repo y backup (riesgo BAJO).**
Afinar `.gitignore`; separar backup en código/datos/generados; decidir y ejecutar la estrategia de repos anidados; sacar el venv del árbol (o documentar recreación). *Verificación:* backup nuevo << 278 MB; `git status` limpio; uvicorn arranca.

**Fase 1 — Red de seguridad de dominio (riesgo BAJO, alto valor).**
Congelar el golden master del torneo cerrado como fixture. Escribir tests de no-regresión de scoring/bracket/ranking que lo reproduzcan. *Verificación:* los tests pasan contra el estado actual.

**Fase 2 — Capa de repositorio + piloto (riesgo MEDIO).**
Crear `repositories/` y migrar el SQL crudo de **1–2 endpoints piloto** (p. ej. ranking) fuera del router. *Verificación:* golden master idéntico; endpoints responden igual (mismos JSON).

**Fase 3 — Partir el God file (riesgo MEDIO, con git como respaldo).**
Dividir `apostador_bets.py` en routers finos por dominio, delegando a services/repos. Se hace endpoint por endpoint, no de golpe. *Verificación:* tras cada grupo, golden master idéntico + smoke test de los 115 endpoints (status 200 y forma del payload).

**Fase 4 — Núcleo de frontend compartido (riesgo MEDIO).**
Extraer `becbuc-core.js` + `becbuc.css`; migrar las 4 superficies a consumirlo; eliminar el scoring JS duplicado (consumir del backend). *Verificación:* las 4 superficies sirven 200 y renderizan igual; captura visual antes/después.

**Fase 5 — Reducción de superficies legacy + documentación (riesgo BAJO).**
Retirar HTML no usados; documentar la arquitectura final y un **runbook de backup/recovery**. *Verificación:* la app sirve todas las superficies vivas; recovery probado desde backup limpio.

---

## 7. Métricas de éxito

| Métrica | Hoy | Meta |
|---|---:|---|
| Líneas del archivo más grande (`apostador_bets.py`) | 12.775 | < 800 por router |
| `text()` SQL crudos en endpoints | 433 | 0 (todo en repositorios) |
| Fuentes de verdad del scoring | 2 (Py + JS) | 1 (Python) |
| Líneas del HTML más grande (Portal) | 11.330 | *shell* < 1.000 + módulos |
| Tamaño de backup de código | ~278 MB (mezclado) | código liviano + datos aparte |
| Cobertura de tests del dominio | ~0 | scoring/bracket/ranking cubiertos |

---

## 8. Próximo paso sugerido

Empezar por **Fase 0 + Fase 1** (bajo riesgo, alto valor): higiene de repo/backup y **congelar el golden master + tests de no-regresión**. Eso construye la red de seguridad que hace segura toda la refactorización posterior. Recién con esos tests en verde conviene tocar el God file (Fase 2–3).

*Documento de assessment — no se modificó código ni se movieron archivos.*
