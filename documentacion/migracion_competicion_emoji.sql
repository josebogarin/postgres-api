-- Agrega columna emoji a competicion (si no existe)
ALTER TABLE competicion ADD COLUMN IF NOT EXISTS emoji VARCHAR(10);
