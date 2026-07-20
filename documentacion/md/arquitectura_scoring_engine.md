# BECBUC – Arquitectura: Scoring Engine por Competencia

**Fecha:** 2026-06-08  
**Base normativa:** Reglamento_BEC_BUC_2026.pdf (prevalece sobre toda lógica anterior)  
**Objetivo:** encapsular la lógica de puntuación por competencia en un módulo dedicado, de modo que cambiar las reglas de una competencia no afecte a otras ni al backend general.

---

## 1. Diagnóstico: diferencias reglamento vs implementación actual

### 1.1 Tabla de puntajes oficial (reglamento)

| Concepto | GR | 16avos | 8vos | 4tos | Semis | 3P | Final |
|---|---|---|---|---|---|---|---|
| H – Resultado (gana/pierde/empata) | 4 | 6 | 8 | 10 | 12 | 14 | 20 |
| I – Marcador exacto (reg + alargue) | 8 | 12 | 16 | 20 | 24 | 28 | 40 |
| J – Tarjetas amarillas | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| K – Tarjetas rojas | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| L – Intervenciones VAR | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| M – Penales cobrados (tiempo de juego) | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| N – Minuto primer gol (aproximación) | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| O – Penales convertidos en tanda (2/equipo) | N/A | 2×eq | 2×eq | 2×eq | 2×eq | 2×eq | 2×eq |
| P – Equipo que clasifica / gana | 1 | 2 | 4 | 6 | 8 | 10 | 12 |

**Pronósticos globales (una vez, antes del torneo):**

| Concepto | Pts |
|---|---|
| A – Campeón mundial | 20 |
| B – Equipos finalistas (10/equipo, máx 20) | 20 |
| C – Goleador del Mundial | 20 |
| D – Peor equipo del Mundial | 20 |
| E – Mayor goleada: goles ganador + goles perdedor (10 c/u) | 20 |
| F – Etapa hasta donde llega Paraguay | 6 |
| G – Cantidad de goles de Paraguay | 6 |
| **TOTAL GLOBALES** | **112** |

**Total máximo base: 2.556 puntos** (sin doble Paraguay)  
**Partidos de Paraguay: doble puntaje en todos los conceptos del partido** (no globales)

### 1.2 Gaps vs implementación actual

| Gap | Severidad | Detalle |
|---|---|---|
| Puntaje plano 3/1 en vez de escala por fase | 🔴 CRÍTICO | Grupos: debería ser 4/8. Semis: 12/24. Final: 20/40 |
| Tarjetas rojas no implementadas | 🔴 CRÍTICO | No existe `pred_rojas` ni `partido.rojas` |
| Penales durante partido (M) no implementados | 🔴 CRÍTICO | `pred_penales` se usa para tanda, no para cobrados en juego |
| Penales tanda: boolean en vez de cantidad por equipo | 🔴 CRÍTICO | Debe ser `pred_penales_local_tanda` + `pred_penales_visitante_tanda` (INT), 2pts/equipo acertado |
| Pronósticos globales (A–G) no implementados | 🔴 CRÍTICO | 112 pts ausentes del sistema |
| Doble puntaje partidos Paraguay no implementado | 🟠 ALTO | El reglamento lo exige |
| Equipo que clasifica en grupos sin puntaje separado | 🟠 ALTO | Actualmente no hay pts_equipo en grupos |
| Puntaje equipo KO: 5 pts plano en vez de escala | 🟠 ALTO | Debe ser 2/4/6/8/10/12 según fase |
| Reglas hardcodeadas en apostador_bets.py | 🟡 MEDIO | Imposible cambiar sin tocar endpoint |
| Bonus terceros: +10 pts plano sin base reglamentaria | 🟡 MEDIO | No está en el reglamento oficial; revisar |

---

## 2. Arquitectura objetivo

### 2.1 Principio de diseño

**Strategy Pattern + Registry:** cada competencia registra su propia `ScoringEngine`. El calculator recibe `competicion_id` y resuelve el engine correcto. El backend (endpoints, persistencia, ranking) no cambia al agregar competencias.

```
Endpoint calcular_puntajes(torneo_id)
    │
    ▼
ScoringRegistry.get(competicion.codigo)   ← resuelve engine
    │
    ▼
ScoringEngine (por competencia)
    ├── score_partido(apuesta, partido, fase_tipo, es_paraguay) → PartidoScore
    ├── score_global(apuesta_global, torneo_real) → GlobalScore
    └── get_config() → ScoringConfig (tabla de multiplicadores)
    │
    ▼
ScoringCalculator.persist(db, scores)    ← escribe puntaje_detalle + apuesta
```

### 2.2 Árbol de archivos nuevo

```
backend/app/
├── services/
│   ├── scoring/                           ← NUEVO paquete
│   │   ├── __init__.py
│   │   ├── base.py                        ← clases abstractas + dataclasses
│   │   ├── registry.py                    ← mapa codigo_competencia → engine
│   │   ├── calculator.py                  ← orquestador: carga, puntúa, persiste
│   │   └── engines/
│   │       ├── __init__.py
│   │       ├── copa_mundo_2026.py          ← engine reglamento oficial
│   │       └── default.py                 ← engine legacy 3/1/0 (fallback)
│   ├── bracket_service.py  (sin cambios)
│   ├── ko_scoring.py       (sin cambios)
│   └── torneo_service.py   (sin cambios)
├── api/v1/endpoints/
│   ├── apostador_bets.py                  ← refactor: delega scoring a calculator
│   └── scoring_admin.py                   ← NUEVO: CRUD reglas por competencia (admin)
├── models/becbuc/
│   ├── scoring_rule.py                    ← NUEVO: tabla scoring_rule
│   ├── apuesta_global.py                  ← NUEVO: tabla apuesta_global
│   ├── apuesta.py                         ← ampliar cols
│   └── partido.py                         ← ampliar cols
└── documentacion/
    ├── migracion_scoring_v2.sql           ← NUEVO: migraciones BD
    └── arquitectura_scoring_engine.md     ← este documento
```

---

## 3. Detalle de cada componente nuevo

### 3.1 `base.py` – Contratos

```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class FaseConfig:
    """Multiplicadores y puntos por tipo de fase."""
    pts_resultado: int        # H
    pts_marcador_exacto: int  # I
    pts_amarillas: int = 1   # J
    pts_rojas: int = 1       # K
    pts_var: int = 1         # L
    pts_penales_partido: int = 1  # M
    pts_minuto_gol: int = 1  # N
    pts_penales_tanda_por_equipo: int = 2  # O (0 si es grupo)
    pts_equipo_clasifica: int = 0  # P

@dataclass
class ScoringConfig:
    """Configuración completa de reglas para una competencia."""
    nombre: str
    fases: dict[str, FaseConfig]          # fase_tipo → FaseConfig
    pts_campeon: int = 0
    pts_finalista_por_equipo: int = 0
    pts_goleador: int = 0
    pts_peor_equipo: int = 0
    pts_mayor_goleada_ganador: int = 0
    pts_mayor_goleada_perdedor: int = 0
    pts_etapa_paraguay: int = 0
    pts_goles_paraguay: int = 0
    doble_puntaje_paraguay: bool = False

@dataclass
class PartidoScore:
    partido_id: int
    apostador_id: int
    fase_tipo: str
    multiplicador: int           # 1 normal, 2 si es Paraguay
    pts_resultado: int = 0
    pts_marcador: int = 0
    pts_amarillas: int = 0
    pts_rojas: int = 0
    pts_var: int = 0
    pts_penales_partido: int = 0
    pts_minuto: int = 0
    pts_penales_tanda: int = 0   # suma local + visitante
    pts_equipo: int = 0
    pts_total: int = 0
    # detalle para auditoría
    teams_match: bool = True
    gano_minuto: bool = False
    detalles: dict = field(default_factory=dict)

@dataclass
class GlobalScore:
    apostador_id: int
    pts_campeon: int = 0
    pts_finalistas: int = 0
    pts_goleador: int = 0
    pts_peor_equipo: int = 0
    pts_mayor_goleada: int = 0
    pts_etapa_paraguay: int = 0
    pts_goles_paraguay: int = 0
    pts_total: int = 0

class ScoringEngine(Protocol):
    """Contrato que debe implementar cada engine de competencia."""
    def get_config(self) -> ScoringConfig: ...
    def score_partido(
        self,
        apuesta: dict,
        partido: dict,
        fase_tipo: str,
        es_paraguay: bool = False,
        ko_teams_match: bool = True,
    ) -> PartidoScore: ...
    def score_global(
        self,
        apuesta_global: dict,
        torneo_resultados: dict,
    ) -> GlobalScore: ...
```

### 3.2 `engines/copa_mundo_2026.py` – Reglamento oficial

```python
from ..base import ScoringEngine, ScoringConfig, FaseConfig, PartidoScore, GlobalScore

FASES = {
    "grupo": FaseConfig(
        pts_resultado=4, pts_marcador_exacto=8,
        pts_penales_tanda_por_equipo=0, pts_equipo_clasifica=1,
    ),
    "ronda32": FaseConfig(
        pts_resultado=6, pts_marcador_exacto=12,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=2,
    ),
    "ronda16": FaseConfig(
        pts_resultado=8, pts_marcador_exacto=16,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=4,
    ),
    "cuartos": FaseConfig(
        pts_resultado=10, pts_marcador_exacto=20,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=6,
    ),
    "semis": FaseConfig(
        pts_resultado=12, pts_marcador_exacto=24,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=8,
    ),
    "tercer_puesto": FaseConfig(
        pts_resultado=14, pts_marcador_exacto=28,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=10,
    ),
    "final": FaseConfig(
        pts_resultado=20, pts_marcador_exacto=40,
        pts_penales_tanda_por_equipo=2, pts_equipo_clasifica=12,
    ),
}

CONFIG = ScoringConfig(
    nombre="Copa del Mundo FIFA 2026 – Reglamento BEC BUC",
    fases=FASES,
    pts_campeon=20,
    pts_finalista_por_equipo=10,
    pts_goleador=20,
    pts_peor_equipo=20,
    pts_mayor_goleada_ganador=10,
    pts_mayor_goleada_perdedor=10,
    pts_etapa_paraguay=6,
    pts_goles_paraguay=6,
    doble_puntaje_paraguay=True,
)

class CopasMundoScoringEngine:
    def get_config(self) -> ScoringConfig:
        return CONFIG

    def score_partido(self, apuesta, partido, fase_tipo, es_paraguay=False, ko_teams_match=True) -> PartidoScore:
        cfg = FASES.get(fase_tipo)
        if not cfg:
            raise ValueError(f"Fase desconocida: {fase_tipo}")

        mult = 2 if es_paraguay and CONFIG.doble_puntaje_paraguay else 1
        s = PartidoScore(
            partido_id=partido["id"],
            apostador_id=apuesta["apostador_id"],
            fase_tipo=fase_tipo,
            multiplicador=mult,
            teams_match=ko_teams_match,
        )

        if not ko_teams_match:
            return s  # sin equipos correctos: 0 en todo

        pl = apuesta.get("pred_local")
        pv = apuesta.get("pred_visitante")
        rl = partido.get("goles_local")
        rv = partido.get("goles_visitante")

        if None in (pl, pv, rl, rv):
            return s

        # H – Resultado
        def wdl(l, v): return "L" if l > v else ("E" if l == v else "V")
        if wdl(pl, pv) == wdl(rl, rv):
            s.pts_resultado = cfg.pts_resultado * mult

        # I – Marcador exacto
        if pl == rl and pv == rv:
            s.pts_marcador = cfg.pts_marcador_exacto * mult

        # J – Amarillas
        if apuesta.get("pred_amarillas") is not None and partido.get("amarillas") is not None:
            if apuesta["pred_amarillas"] == partido["amarillas"]:
                s.pts_amarillas = cfg.pts_amarillas * mult

        # K – Rojas
        if apuesta.get("pred_rojas") is not None and partido.get("rojas") is not None:
            if apuesta["pred_rojas"] == partido["rojas"]:
                s.pts_rojas = cfg.pts_rojas * mult

        # L – VAR
        if apuesta.get("pred_var") is not None and partido.get("decisiones_var") is not None:
            if apuesta["pred_var"] == partido["decisiones_var"]:
                s.pts_var = cfg.pts_var * mult

        # M – Penales durante el partido
        if apuesta.get("pred_penales_partido") is not None and partido.get("penales_partido") is not None:
            if apuesta["pred_penales_partido"] == partido["penales_partido"]:
                s.pts_penales_partido = cfg.pts_penales_partido * mult

        # N – Minuto primer gol (aproximación: el más cercano gana)
        # Este ítem se calcula fuera del engine (requiere comparar todos los apostadores)
        # El calculator llama _resolve_minuto_winners() y luego llama engine.award_minuto()

        # O – Penales en tanda (solo KO, y solo si hubo tanda real)
        if cfg.pts_penales_tanda_por_equipo > 0:
            tuvo_tanda = partido.get("penales_local") is not None
            if tuvo_tanda:
                for pred_key, real_key in [
                    ("pred_penales_local_tanda", "penales_local"),
                    ("pred_penales_visitante_tanda", "penales_visitante"),
                ]:
                    if apuesta.get(pred_key) is not None:
                        if apuesta[pred_key] == partido[real_key]:
                            s.pts_penales_tanda += cfg.pts_penales_tanda_por_equipo * mult

        # P – Equipo que clasifica
        if apuesta.get("pred_equipo_clasifica") is not None and partido.get("equipo_clasificado_id") is not None:
            if apuesta["pred_equipo_clasifica"] == partido["equipo_clasificado_id"]:
                s.pts_equipo = cfg.pts_equipo_clasifica * mult

        s.pts_total = (
            s.pts_resultado + s.pts_marcador + s.pts_amarillas + s.pts_rojas +
            s.pts_var + s.pts_penales_partido + s.pts_minuto +
            s.pts_penales_tanda + s.pts_equipo
        )
        return s

    def score_global(self, apuesta_global, torneo_resultados) -> GlobalScore:
        # ... lógica de pronósticos globales A–G
        pass
```

### 3.3 `registry.py` – Registro de engines

```python
from .engines.copa_mundo_2026 import CopasMundoScoringEngine
from .engines.default import DefaultScoringEngine

_ENGINES: dict[str, type] = {
    "copa_mundo_2026": CopasMundoScoringEngine,
    # "liga_local_2027": LigaLocalScoringEngine,  ← agregar sin tocar el resto
}

def get_engine(codigo_competencia: str):
    cls = _ENGINES.get(codigo_competencia)
    if not cls:
        return DefaultScoringEngine()
    return cls()
```

### 3.4 `calculator.py` – Orquestador

```python
# El calculator sustituye la función calcular_puntajes interna de apostador_bets.py
# apostador_bets.py queda como thin router que llama:
#   result = await ScoringCalculator(db).calculate(torneo_id)

class ScoringCalculator:
    def __init__(self, db):
        self.db = db

    async def calculate(self, torneo_id: int) -> dict:
        torneo = await self._load_torneo(torneo_id)
        engine = get_engine(torneo["competicion_codigo"])
        apuestas = await self._load_apuestas(torneo_id)
        partidos = await self._load_partidos_finalizados(torneo_id)
        minuto_winners = self._resolve_minuto_winners(apuestas, partidos)

        scores: list[PartidoScore] = []
        for ap in apuestas:
            partido = partidos[ap["partido_id"]]
            score = engine.score_partido(
                apuesta=ap,
                partido=partido,
                fase_tipo=partido["fase_tipo"],
                es_paraguay=partido.get("es_paraguay", False),
                ko_teams_match=await self._check_ko_teams(ap, partido),
            )
            # Añadir pts_minuto si ganó ese ítem
            if ap["id"] in minuto_winners:
                score.pts_minuto = engine.get_config().fases[partido["fase_tipo"]].pts_minuto_gol
                score.gano_minuto = True
                score.pts_total += score.pts_minuto

            scores.append(score)

        await self._persist(torneo_id, scores)
        return self._summary(scores)
```

---

## 4. Cambios en base de datos

### 4.1 Tabla `apuesta` – columnas a agregar

```sql
-- Migración: migracion_scoring_v2.sql
ALTER TABLE apuesta
  ADD COLUMN IF NOT EXISTS pred_rojas               INT     DEFAULT NULL,  -- K
  ADD COLUMN IF NOT EXISTS pred_penales_partido     INT     DEFAULT NULL,  -- M (cobrados en juego)
  ADD COLUMN IF NOT EXISTS pred_penales_local_tanda  INT    DEFAULT NULL,  -- O local
  ADD COLUMN IF NOT EXISTS pred_penales_visitante_tanda INT DEFAULT NULL,  -- O visitante
  ADD COLUMN IF NOT EXISTS pred_equipo_clasifica    INT     DEFAULT NULL;  -- P (equipo_id)

-- pred_penales (boolean actual) queda como campo legacy;
-- los nuevos campos O usan pred_penales_local_tanda / pred_penales_visitante_tanda
```

### 4.2 Tabla `partido` – columnas a agregar

```sql
ALTER TABLE partido
  ADD COLUMN IF NOT EXISTS rojas           INT DEFAULT NULL,  -- K real
  ADD COLUMN IF NOT EXISTS penales_partido INT DEFAULT NULL,  -- M real (cobrados en juego)
  ADD COLUMN IF NOT EXISTS equipo_clasificado_id INT REFERENCES equipo(id);  -- P real
```

### 4.3 Tabla `apuesta_global` – nueva

```sql
CREATE TABLE IF NOT EXISTS apuesta_global (
  id               SERIAL PRIMARY KEY,
  torneo_id        INT NOT NULL REFERENCES torneo(id),
  apostador_id     INT NOT NULL,
  -- A
  pred_campeon_id  INT REFERENCES equipo(id),
  -- B
  pred_finalista1_id INT REFERENCES equipo(id),
  pred_finalista2_id INT REFERENCES equipo(id),
  -- C
  pred_goleador    VARCHAR(100),
  -- D
  pred_peor_equipo_id INT REFERENCES equipo(id),
  -- E
  pred_mayor_goleada_ganador INT,
  pred_mayor_goleada_perdedor INT,
  -- F
  pred_etapa_paraguay VARCHAR(30),
  -- G
  pred_goles_paraguay INT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (torneo_id, apostador_id)
);
```

### 4.4 Tabla `puntaje_global` – nueva (resultado pronósticos globales)

```sql
CREATE TABLE IF NOT EXISTS puntaje_global (
  id              SERIAL PRIMARY KEY,
  torneo_id       INT NOT NULL REFERENCES torneo(id),
  apostador_id    INT NOT NULL,
  pts_campeon     INT DEFAULT 0,
  pts_finalistas  INT DEFAULT 0,
  pts_goleador    INT DEFAULT 0,
  pts_peor_equipo INT DEFAULT 0,
  pts_mayor_goleada INT DEFAULT 0,
  pts_etapa_paraguay INT DEFAULT 0,
  pts_goles_paraguay INT DEFAULT 0,
  pts_total       INT DEFAULT 0,
  calculado_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (torneo_id, apostador_id)
);
```

### 4.5 Tabla `puntaje_detalle` – columnas a agregar

```sql
ALTER TABLE puntaje_detalle
  ADD COLUMN IF NOT EXISTS pts_resultado   INT DEFAULT 0,  -- H (separado de marcador)
  ADD COLUMN IF NOT EXISTS pts_rojas       INT DEFAULT 0,  -- K
  ADD COLUMN IF NOT EXISTS pts_penales_partido INT DEFAULT 0,  -- M
  ADD COLUMN IF NOT EXISTS pts_penales_tanda   INT DEFAULT 0,  -- O (reemplaza pts_penales)
  ADD COLUMN IF NOT EXISTS pts_equipo      INT DEFAULT 0;  -- P
```

### 4.6 Tabla `competicion` – columna codigo

```sql
ALTER TABLE competicion
  ADD COLUMN IF NOT EXISTS codigo VARCHAR(50) UNIQUE;

UPDATE competicion SET codigo = 'copa_mundo_2026'
  WHERE nombre ILIKE '%mundial%' OR nombre ILIKE '%copa%mundo%';
```

---

## 5. Plan de migración por fases

### Fase A – BD (sin romper nada, ~1 hora)
1. Ejecutar `migracion_scoring_v2.sql`: agregar columnas nuevas (todas con DEFAULT NULL/0 → backwards compatible)
2. Agregar `competicion.codigo` y poblar con `'copa_mundo_2026'`
3. Crear tablas `apuesta_global`, `puntaje_global`

### Fase B – Scoring engine (código puro, sin tocar endpoints, ~3 horas)
1. Crear `backend/app/services/scoring/` con `base.py`, `registry.py`
2. Implementar `engines/copa_mundo_2026.py` con reglamento oficial
3. Implementar `engines/default.py` (legacy 3/1/0 para compatibilidad)
4. Implementar `calculator.py` orquestador
5. Tests unitarios del engine (sin BD)

### Fase C – Refactor endpoints (~2 horas)
1. `calcular_puntajes` en `apostador_bets.py` → delega a `ScoringCalculator`
2. Nuevo endpoint `POST /apuestas-globales/{torneo_id}` para guardar pronósticos A–G
3. Nuevo endpoint `GET /apuestas-globales/{torneo_id}` para leer
4. `calcular-puntajes` incluye score_global al final
5. Ranking suma `puntaje_global.pts_total` al total

### Fase D – Frontend (~3 horas)
1. **Portal + Móvil**: formulario de pronósticos globales (campeón, finalistas, etc.) en tab Pronós → nuevo sub-tab "Globales"
2. Campos de input nuevos en cada partido: tarjetas rojas, penales cobrados en juego
3. Toggle penales tanda: cambiar de SÍ/NO a inputs numéricos (1–5 por equipo)
4. Ranking: columna pts_globales + desglose en transparencia

### Fase E – Verificación y ajuste (~1 hora)
1. Simular torneo 2 completo con nuevo engine
2. Comparar totales vs planilla Excel manual
3. Ajustar si hay diferencias

---

## 6. Lo que NO cambia (protegido por encapsulamiento)

| Componente | Estado |
|---|---|
| `bracket_service.py` | ✅ Sin cambios |
| `ko_scoring.py` | ✅ Sin cambios |
| `torneo_service.py` | ✅ Sin cambios |
| `fases_apuesta_estado` endpoint | ✅ Sin cambios |
| `resetear-apuestas` endpoint | ✅ Sin cambios |
| Lógica de bracket visual | ✅ Sin cambios |
| Auth / JWT / deps | ✅ Sin cambios |
| Frontend (excepto campos nuevos) | ✅ Cambios aditivos solamente |

---

## 7. Inconsistencias del reglamento a clarificar con la organización

| # | Ítem | Pregunta |
|---|---|---|
| 1 | **Bonus mejores terceros** | El reglamento oficial NO menciona el bono +10 pts por acertar mejores terceros. ¿Se mantiene o elimina? |
| 2 | **Minuto primer gol** | "El más cercano gana": si dos apostadores equidistan, ¿ambos suman o hay desempate? |
| 3 | **Equipo clasifica en grupos** | El reglamento dice "1 pto por clasificado acertado". ¿Aplica para los 32 clasificados o solo los 24 directos + 8 mejores terceros? |
| 4 | **Paraguay en R32** | Si Paraguay clasifica y juega en 16avos, ¿el doble puntaje aplica al partido de 16avos? ¿A todos sus partidos KO? |
| 5 | **Penales tanda en 3P** | El 3er puesto no tiene penales en FIFA 2026. ¿Se excluye el ítem O para ese partido? |
| 6 | **Mayor goleada** | Si hay dos goleadas con el mismo score, ¿se toma la primera o cualquiera es válida? |

---

## 8. Resumen ejecutivo para comenzar

**Prioridad inmediata (antes de cualquier dato real):**

1. **Ejecutar Fase A** (migraciones BD) — no rompe nada, solo agrega columnas
2. **Implementar engine `copa_mundo_2026.py`** — código aislado, testeable sin BD
3. **Conectar `calcular_puntajes` al nuevo calculator** — un cambio de ~20 líneas en el endpoint

El reglamento cambia drásticamente los puntajes base (grupos: 4/8 en vez de 1/3, Final: 20/40). Todos los puntajes calculados hasta ahora son incorrectos contra el reglamento oficial y deben recalcularse tras la Fase C.
