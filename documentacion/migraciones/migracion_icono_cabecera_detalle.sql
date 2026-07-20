-- ============================================================
-- Migración: agregar columna icono a cabecera y detalle
-- icono : varchar(50) NULL  (ej: '📦', 'table', 'list-bullet')
-- ============================================================

ALTER TABLE cabecera
  ADD COLUMN IF NOT EXISTS icono varchar(50) NULL;

ALTER TABLE detalle
  ADD COLUMN IF NOT EXISTS icono varchar(50) NULL;

COMMENT ON COLUMN cabecera.icono IS 'Emoji o nombre de ícono para visualización en UI';
COMMENT ON COLUMN detalle.icono  IS 'Emoji o nombre de ícono para visualización en UI';
