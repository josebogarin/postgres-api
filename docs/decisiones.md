# Bitácora de decisiones técnicas — BECBUC

Formato: fecha | decisión | por qué | alternativas descartadas.
Se agrega en el momento en que se toma la decisión (no al final de la sesión).

| Fecha | Decisión | Por qué | Alternativas descartadas |
|---|---|---|---|
| 2026-06-08 | Scoring engine con patrón **Strategy + Registry** (un engine por competencia) | separar el puntaje de los endpoints; permitir reglamentos distintos por torneo sin tocar el resto | scoring inline en apostador_bets (acoplado, no escala) |
| 2026-06-08 | Reglamento oficial con **escala por fase** (H 4→20, I 8→40) | el 3/1/0 no reflejaba el reglamento BEC BUC | seguir con 3/1/0 |
| 2026-06 | Reglamento **por defecto = Copa del Mundo** (no legacy 3/1/0) | evitar que un torneo sin reglamento puntúe mal en silencio | fallback a legacy 3/1/0 |
| 2026-06 | Ítem P (equipo clasifica) **NO** se duplica para Paraguay | decisión de la organización | duplicar como el resto de ítems |
| 2026-07-02 | Minuto 1er gol: ante empate de distancia mínima, **todos** los empatados suman | decisión de la organización | premiar solo al más cercano |
| 2026-06 | **Bonus mejores terceros eliminado** del scoring | no figura en el reglamento oficial | mantenerlo |
| 2026-06 | Regla **null→0** en K/M (predicción vacía = 0; si el real es 0, acierta) | confirmado por la organización | tratar null como "sin dato" |
| 2026-06 | **Fair Play FIFA** (tarjetas por equipo) para desempatar mejores terceros | criterio oficial FIFA Art.38 | solo Pts/DG/GF |
| 2026-07-20 | Frontend = **2 superficies** (Portal actual + Live nuevo React) | cerrar el rediseño; un solo Live unificado | mantener Portal+Móvil+live legacy en paralelo |
| 2026-07-20 | Retirar **"REGLA UI OBLIGATORIA"** (editar Portal+Móvil juntos) | el Live nuevo es una sola superficie React | seguir con la doble edición |
| 2026-07-20 | **Unificar en un solo repo git** (no submódulos) | equipo de 1, deploy conjunto; submódulos = punteros que se olvidan | git subtree / submódulos |
| 2026-07-20 | **Portabilidad**: rutas relativas (`%~dp0` en .bat, `__file__` en .py) | poder mover/renombrar el directorio | ruta hardcodeada "C:\proyecto FAST API" |
| 2026-07-21 | **Multi-torneo** con selector en el Live (no hardcodear TORNEO_ID) | varios torneos activos en paralelo | TORNEO_ID=2 fijo |
| 2026-07-21 | Torneos de clubes: bracket **ida/vuelta, sin 3er puesto**, encapsulado aparte del Mundial | estructura distinta a selecciones | reusar el bracket del Mundial |
| 2026-07-20 | Refactor: partir el **God file** (repositories/ranking_repo, services/reportes/*, routers admin_extra/database_admin/sistema/diccionario) | aliviar apostador_bets.py; una sola fuente de datos | dejar todo en el God file |
| 2026-08-01 | **Engine copa_clubes** (Opción C): H/I por fase, Cambios (un total, reemplaza VAR), comodín, cruce, tanda, minuto ×2 | reglamento nuevo validado por Monte Carlo (competitividad + suspenso) | opciones A/B (menos equilibradas) |
| 2026-08-01 | **Sustituciones = un total** del partido (local+visitante) | simplifica boleta y BD | dos campos separados (local/visitante) |
| 2026-08-01 | **Login por PIN** (4 dígitos; admin 1964 = solo lectura; recuperar por celular) | acceso simple para un pozo cerrado, sin passwords | login usuario/contraseña |
| 2026-08-01 | **Comodín**: único por torneo, se fija al jugarse su partido | jugada estratégica sin abusos | comodín por fase / editable siempre |
| 2026-08-01 | **Bracket de clubes ordena por `p.id`** (estructura fija), no por fecha | cambiar horarios reordenaba el cuadro y movía llaves de lado | ordenar por fecha |
| 2026-08-01 | Fuente de **fecha/hora de KO = ESPN** (API JSON) | API-Football trae placeholders; CONMEBOL no tiene API usable (SSR/RSC) | API-Football (impreciso) / scraping headless de CONMEBOL (frágil) |
| 2026-08-01 | Guardar **fecha en UTC**, mostrar en `America/Asuncion` (UTC−3 fijo) | consistencia; Paraguay sin DST desde 2024 | guardar hora local |
| 2026-08-01 | `pts_var` reutilizado para guardar **Cambios** en clubes (ranking `cat_sustituciones`) | clubes no usan VAR; evita migración de esquema | columna nueva `pts_sustituciones` |
| 2026-08-02 | **Avance de bracket de clubes POSICIONAL** (`Gan.{L}{k}`, k=orden por p.id) automático en cada sync + endpoint | clubes tienen bracket propio ida/vuelta; reusar la topología sembrada; mantener estructura fija por p.id | reconstruir el cuadro estilo Mundial (pisa las cabezas de serie) |
| 2026-08-02 | **Fase KO se cierra** (bloqueada) cuando TODOS sus partidos están finalizados → no se editan apuestas | evitar edición post-cierre; consistente con grupos | dejar la fase abierta / bloquear solo por partido |
| 2026-08-02 | **Cruce vía tanda (ABIERTA)**: si el apostador predice la llave EMPATADA, NO se le acredita el equipo por la tanda; el bono va al ganador limpio del par | consistencia test↔orquestador; simplicidad (hoy) | acreditar el cruce por la tanda pronosticada — pendiente de decidir |
| 2026-08-02 | Reorganización del proyecto **pospuesta**; backup por `git tag`/rama (no ZIP lento); empezar por scripts→`_cuarentena` | ZIP de ~300 MB es lentísimo; git/GitHub ya es el respaldo | ZIP completo con Compress-Archive |
