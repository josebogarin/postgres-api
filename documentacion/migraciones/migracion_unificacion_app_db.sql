-- ============================================================
-- MIGRACIÓN: Corrección de relaciones en app_db
-- Fecha: 2026-05-23
-- Ejecutar en psql como app_user
-- ============================================================

-- ── 1. cabecera: cambiar id_sistema de varchar → bigint FK → sistema.id ──
-- Primero eliminamos las restricciones que dependen de la columna actual

ALTER TABLE cabecera DROP CONSTRAINT IF EXISTS cabecera_id_sistema_fkey;
ALTER TABLE cabecera DROP CONSTRAINT IF EXISTS cabecera_id_sistema_nombre_key;
DROP INDEX IF EXISTS idx_cabecera_sistema;
DROP INDEX IF EXISTS ix_cabecera_id_sistema;

-- Agregar columna temporal bigint
ALTER TABLE cabecera ADD COLUMN id_sistema_new BIGINT;

-- Poblar con el id numérico de sistema haciendo join por el nombre
-- (ajustar si la lógica de negocio es diferente)
UPDATE cabecera c
SET id_sistema_new = s.id
FROM sistema s
WHERE c.id_sistema::text = s.id::text
   OR c.id_sistema = s.nombre;

-- Eliminar columna vieja y renombrar la nueva
ALTER TABLE cabecera DROP COLUMN id_sistema;
ALTER TABLE cabecera RENAME COLUMN id_sistema_new TO id_sistema;

-- Agregar NOT NULL y FK
ALTER TABLE cabecera ALTER COLUMN id_sistema SET NOT NULL;
ALTER TABLE cabecera
    ADD CONSTRAINT cabecera_id_sistema_fkey
    FOREIGN KEY (id_sistema) REFERENCES sistema(id) ON DELETE RESTRICT;

-- Recrear índices y unique
CREATE INDEX ix_cabecera_id_sistema ON cabecera(id_sistema);
ALTER TABLE cabecera
    ADD CONSTRAINT cabecera_id_sistema_nombre_key UNIQUE (id_sistema, nombre);


-- ── 2. detalle: eliminar id_sistema y renombrar cabecera_id → id_cabecera ──

-- Eliminar columna id_sistema de detalle (si existe)
ALTER TABLE detalle DROP CONSTRAINT IF EXISTS detalle_id_sistema_fkey;
DROP INDEX IF EXISTS ix_detalle_id_sistema;
ALTER TABLE detalle DROP COLUMN IF EXISTS id_sistema;

-- Renombrar cabecera_id → id_cabecera
ALTER TABLE detalle DROP CONSTRAINT IF EXISTS detalle_cabecera_id_nombre_key;
ALTER TABLE detalle DROP CONSTRAINT IF EXISTS detalle_cabecera_id_fkey;
DROP INDEX IF EXISTS idx_detalle_cabecera;

ALTER TABLE detalle RENAME COLUMN cabecera_id TO id_cabecera;

-- Recrear FK y constraints con el nuevo nombre
ALTER TABLE detalle
    ADD CONSTRAINT detalle_id_cabecera_fkey
    FOREIGN KEY (id_cabecera) REFERENCES cabecera(id) ON DELETE CASCADE;

CREATE INDEX ix_detalle_id_cabecera ON detalle(id_cabecera);

ALTER TABLE detalle
    ADD CONSTRAINT detalle_id_cabecera_nombre_key UNIQUE (id_cabecera, nombre);


-- ── 3. diccionario: corregir id_sistema (varchar → bigint FK → sistema.id) ──
-- Si ya existe como varchar, hacer la conversión igual que cabecera
ALTER TABLE diccionario DROP CONSTRAINT IF EXISTS diccionario_id_sistema_fkey;
DROP INDEX IF EXISTS ix_diccionario_id_sistema;

DO $$
BEGIN
    -- Si la columna ya existe como varchar, convertirla
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diccionario'
          AND column_name = 'id_sistema'
          AND data_type != 'bigint'
    ) THEN
        ALTER TABLE diccionario ADD COLUMN id_sistema_new BIGINT;
        UPDATE diccionario d
        SET id_sistema_new = s.id
        FROM sistema s
        WHERE d.id_sistema::text = s.id::text
           OR d.id_sistema::text = s.nombre;
        ALTER TABLE diccionario DROP COLUMN id_sistema;
        ALTER TABLE diccionario RENAME COLUMN id_sistema_new TO id_sistema;

    -- Si no existe, crearla directamente como bigint
    ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diccionario'
          AND column_name = 'id_sistema'
    ) THEN
        ALTER TABLE diccionario ADD COLUMN id_sistema BIGINT;
    END IF;
END $$;

ALTER TABLE diccionario
    ADD CONSTRAINT diccionario_id_sistema_fkey
    FOREIGN KEY (id_sistema) REFERENCES sistema(id) ON DELETE SET NULL;

CREATE INDEX ix_diccionario_id_sistema ON diccionario(id_sistema);


-- ── 4. Verificación ──────────────────────────────────────────────────────
\d cabecera
\d detalle
