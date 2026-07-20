-- ============================================================
-- migracion_puntaje_item.sql
-- Tabla de auditoría granular por ítem de puntaje.
-- Cada fila = un partido (o torneo para globales) x apostador x ítem.
--
-- categoría 'partido' → items H, I, J, K, L, M, N, O, P
--   partido_id NOT NULL — una fila por partido+apostador+ítem
--
-- categoría 'global'  → items A, B, C, D, E, F, G
--   partido_id IS NULL — una fila por torneo+apostador+ítem
--   solo se calcula cuando hay campeón definido (fin del torneo)
--
-- UPSERT: el scoring engine hace INSERT ON CONFLICT DO UPDATE.
-- Constraint: no se puede repetir partido+apostador+ítem (ni torneo+apostador+ítem para globales).
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_puntaje_item.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

CREATE TABLE IF NOT EXISTS puntaje_item (
    id              SERIAL PRIMARY KEY,
    torneo_id       INT         NOT NULL,
    partido_id      INT,                    -- NULL para ítems globales (A-G)
    apostador_id    INT         NOT NULL,
    categoria       VARCHAR(10) NOT NULL,   -- 'partido' | 'global'
    item            VARCHAR(2)  NOT NULL,   -- A-G (globales) | H-P (partido)

    -- Contexto del partido (NULL para globales)
    fase_tipo       VARCHAR(30),
    fase_nombre     VARCHAR(80),
    fecha_partido   TIMESTAMPTZ,
    local_nombre    VARCHAR(100),
    visit_nombre    VARCHAR(100),

    -- Valores comparados
    resultado       TEXT,   -- valor real  (ej: "L", "2-1", "3", "4-2")
    apuesta         TEXT,   -- valor apostado

    -- Puntaje asignado (ya incluye multiplicador x2 Paraguay si aplica)
    puntaje         INT         NOT NULL DEFAULT 0,
    multiplicador   INT         NOT NULL DEFAULT 1,  -- 1 normal, 2 Paraguay

    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Índice único para ítems de partido (partido_id NOT NULL) ──────────────────
CREATE UNIQUE INDEX IF NOT EXISTS uq_puntaje_item_partido
    ON puntaje_item (partido_id, apostador_id, item)
    WHERE partido_id IS NOT NULL;

-- ── Índice único para ítems globales (partido_id IS NULL) ────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS uq_puntaje_item_global
    ON puntaje_item (torneo_id, apostador_id, item)
    WHERE partido_id IS NULL;

-- ── Índices de consulta ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_puntaje_item_torneo
    ON puntaje_item (torneo_id);

CREATE INDEX IF NOT EXISTS idx_puntaje_item_apostador
    ON puntaje_item (torneo_id, apostador_id);

CREATE INDEX IF NOT EXISTS idx_puntaje_item_partido_apost
    ON puntaje_item (partido_id, apostador_id);
