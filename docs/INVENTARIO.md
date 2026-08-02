# INVENTARIO — FASE 0 (read-only, no se movió nada)

Generado: 2026-08-01. Raíz: `C:\proyecto FAST API`.
Listado completo por archivo (ruta · bytes · fecha · líneas): **`docs/INVENTARIO_archivos.tsv`** (1608 archivos, sin `node_modules/.venv/.git/.next/__pycache__`).

## 1. Resumen ejecutivo
- **520 archivos sueltos en la raíz** (243 .py, 111 .txt, 49 .ps1, 24 .bat, 22 .xlsx, 10 .md, 9 .sql, 8 .vbs…). Es el mayor foco de desorden.
- **Dos frontends**: `frontend/` ("web-app", mod. 2026-05-17, **VIEJO**) vs `frontend-becbuc/` (el Live actual, mod. 2026-07-20).
- **App extra**: `web/` = una app **Flask** aparte (app.py + templates) — no es el backend FastAPI.
- **Backend limpio**: `backend/app/` NO tiene rutas `C:\` ni contraseñas hardcodeadas (0 y 0). La deuda de portabilidad está en los **scripts sueltos** y en `.bat/.ps1/.vbs`.
- **Peso muerto grande**: `_backups/` (34 MB) + `C:\proyecto FAST API\_backups/` (dir con nombre corrupto), `node_modules` (x2), `.venv`, 209 `__pycache__`, `.next` (x2), builds regenerables (`backend/static/v2` == `frontend-becbuc/out`).

## 2. Árbol top-level (tamaño · propósito · destino propuesto)
| Carpeta | Tamaño | Qué es | Destino |
|---|---|---|---|
| `backend/` | 12 MB | FastAPI (app/, alembic/, static/, tests). **Entrypoint: `backend/app/main.py`** | backend/ (se mantiene) |
| `frontend-becbuc/` | 305 MB* | Live nuevo React/Next (fuente). *incluye node_modules/.next | frontend/ (renombrar) |
| `frontend/` | ~? (21.392 arch.) | Next viejo "web-app" (2026-05) con .next+node_modules | **_cuarentena** (confirmar obsoleto) |
| `web/` | chico | App Flask separada (app.py, templates, .env) | **DUDA** (ver §8) |
| `documentacion/` | 56 MB | SQLs, PDFs, reglamentos, seeds, imágenes | docs/ + data/ |
| `bat/` | 300 KB | .bat de arranque/mantenimiento (usan %~dp0) | scripts/ |
| `_backups/` | 34 MB | backups de safe_write + snapshots static | **_cuarentena** (o borrar fuera de sesión) |
| `C:\proyecto FAST API\_backups/` | 27 MB | dir con **nombre corrupto** (bug de ruta), .bak viejos | **_cuarentena** |
| `plantillas/` | chico | scaffolding (expo, nextjs, python-api-client) — no es BECBUC | **DUDA** (referencia o basura) |
| `tools/`, `tests/`, `skills/`, `docs/` | chico | util db_env / golden tests / skill / docs | scripts|tests|skills|docs |
| `proyectos/`, `Apuestas/` | vacío | solo .gitkeep / vacío | borrar (fuera de sesión) |

## 3. Los 520 archivos de la raíz — clasificación propuesta
- **scripts/ (mantenimiento/diagnóstico)**: 243 `.py` (`actualizar_*`, `diag_*`, `fix_*`, `verificar_*`, `_patch_*`, `assess_*`, `auditoria_*`, `sync_*`, `inferir_fechas_*`, `set_fecha_partido`, `restaurar_*`…), 49 `.ps1`, 8 `.vbs`. **La mayoría son one-off ya ejecutados** → separar los ~10 útiles/recientes de los históricos (estos últimos a `_cuarentena` o `scripts/historico/`).
- **data/ (no versionado)**: 22 `.xlsx` (pronósticos/consolidados), 111 `.txt` (**~77 son `*_out.txt`/`*_log.txt` = salidas de scripts → basura/data**), 1 `.csv`, 1 `.zip`.
- **docs/**: 10 `.md` (ASSESSMENT_ARQUITECTURA, CRUD_SYSTEM_DESIGN, DATABASE_EXPLORER_API, INICIAR, test_integral_report, soporte_microsoft_nameservers, **BECBUC.md** = ¿CLAUDE viejo?), 4 `.docx`. (CLAUDE.md/ESTADO.md quedan en raíz.)
- **documentacion/ o db/**: 9 `.sql`.
- **assets**: 14 `.jpg`, 3 `.png` (logos/capturas).
- **skills/**: 3 `.skill`.
- **basura/cuarentena**: nombres corruptos `0`, `Ingles)`, `goles_visitante)`, `CLAUDE.md.20260709_225247.bak`, `2` .exe (¿ngrok?), .bak sueltos.

## 4. AUDITORÍA DE PORTABILIDAD (crítico)
Conteo de ocurrencias (código, sin node_modules/.venv/_backups):
| Patrón | Ocurrencias | Dónde se concentra |
|---|---|---|
| `C:\...` (ruta absoluta) | **198** | scripts sueltos (44 archivos .py), .bat, .ps1, .vbs. `backend/app/` = **0** |
| `localhost` | **517** | scripts, .bat/.ps1, htmls viejos, `web/`, frontend viejo. `frontend-becbuc/src` = **0** |
| `superpassword` (pass BD) | **197** | 147 scripts .py sueltos (conexión psycopg2 hardcodeada). `backend/app/` = **0** |
| `catalina` (pass admin) | **133** | scripts + htmls (auto-login). |
| `becbuc2026` (pass apostadores) | 11 | scripts/seed. |
| `f13bee…` (API-key API-Football) | 12 | scripts + `backend/.env` (ok en .env). |
| `127.0.0.1` | 18 | scripts/ps1. |
| puertos `:8000`/`:5432`/`:3000` | 250 / 44 / 14 | omnipresentes (URLs y conexiones). |

Ejemplos (archivo:línea): `actualizar_r32_desde_excel.py:9` (`cd "C:\proyecto FAST API"`), `:30` (`C:\Users\Jose Bogarin\Downloads`); `actualizar_eventos_api.py:27` (`host=localhost … password=superpassword`).
**Buena noticia**: el núcleo (`backend/app/`, `frontend-becbuc/src`) ya está limpio; la portabilidad se resuelve sobre todo en los **scripts sueltos** (centralizar conexión BD y ROOT en un módulo) y en `.bat/.ps1` (ya usan `%~dp0` varios).

## 5. Basura / candidatos a `_cuarentena` (con motivo)
| Ítem | Motivo |
|---|---|
| `frontend/` (Next viejo "web-app") | reemplazado por `frontend-becbuc/`; tiene .next+node_modules (21k archivos) |
| `_backups/` (34 MB) y `C:\proyecto FAST API\_backups/` | snapshots de safe_write / .bak; el dir del 2º tiene nombre corrupto |
| `**/__pycache__` (209), `.pytest_cache`, `**/.venv`, `**/node_modules`, `**/.next` | generados/regenerables (van a .gitignore, no a git) |
| `*_out.txt` (42) + `*_log.txt` (35) sueltos | salidas de scripts |
| `backend/static/v2` == `frontend-becbuc/out` | build regenerable (duplicado exacto) |
| nombres corruptos: `0`, `Ingles)`, `goles_visitante)` | artefactos de comandos mal armados |
| `plantillas/` | scaffolding externo, no BECBUC |
| `proyectos/` (solo .gitkeep), `Apuestas/` (vacío) | placeholders vacíos |
> Recordatorio: en esta sesión NO se borra nada; lo sospechoso iría a `_cuarentena/` con motivo (FASE 2).

## 6. Duplicados
- **Por contenido (mismo hash): 65 grupos.** Los mayores: los 4 HTML de `backend/static/` copiados x12 en `_backups/static_pre_v2_*`; `backend/app/main.py` x9 (backups `main.py.bak`); todo `backend/static/v2/*` == `frontend-becbuc/out/*` (build).
- **Mismo nombre en varias carpetas**: `page.tsx` x12 (en `frontend/` viejo), los HTML del portal/movil/live x12 (backups), `main.py.bak` x11, `__init__.py` x22 (normal).

## 7. Huérfanos y entrypoints
- **Entrypoint backend**: `backend/app/main.py` (uvicorn `app.main:app`).
- **Entrypoint frontend**: `frontend-becbuc/package.json` (scripts `build:export` → `static/v2`).
- **Huérfanos probables** (nadie los importa): la mayoría de los 243 `.py` sueltos son ejecutables one-off (no importados por el backend); los htmls legacy (`becbuc-live*.html`) fuera del portal; `web/` (Flask) y `frontend/` (Next viejo) no los referencia el sistema actual. *Confirmación fina requiere grep de imports en FASE 2.*

## 8. DUDAS (no clasifico sin tu OK)
1. **`web/`** (app Flask con templates): ¿está en uso (algún acceso/deploy) o es una capa vieja para cuarentena?
2. **`frontend/`** (Next "web-app", 2026-05): ¿confirmás que quedó obsoleto y reemplazado por `frontend-becbuc/`? → a `_cuarentena`.
3. **`plantillas/`**: ¿son plantillas de referencia que querés conservar, o basura?
4. **Scripts sueltos `.py` (243)**: ¿los separo en `scripts/` (útiles) vs `scripts/historico/` (one-off ya usados), o directamente los históricos a `_cuarentena`?
5. **`BECBUC.md`** en la raíz: parece un CLAUDE.md/estado viejo. ¿A `docs/` o a `_cuarentena`?
6. **`.exe` sueltos** (¿`ngrok.exe`?), **`documentacion/` (56 MB)**: ¿qué PDFs/seeds conservar en `docs/` vs `data/`?
