-- Migración: minuto actual de juego en partido (para visualización en vivo)
ALTER TABLE partido ADD COLUMN IF NOT EXISTS minuto_actual SMALLINT;

-- puntaje_detalle: asegurar columna pts_penales_partido
ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_partido SMALLINT DEFAULT 0;
