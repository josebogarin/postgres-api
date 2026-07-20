-- Agrega campo numero_partido_fifa a pronosticos_aux
ALTER TABLE pronosticos_aux
    ADD COLUMN IF NOT EXISTS numero_partido_fifa INTEGER;

-- Verificacion
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pronosticos_aux'
ORDER BY ordinal_position;
