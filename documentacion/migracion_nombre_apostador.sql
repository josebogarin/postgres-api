-- Agrega nombre_apostador a tabla apuesta (becbuc)
-- Permite identificar al apostador sin cruzar a app_db

ALTER TABLE apuesta ADD COLUMN IF NOT EXISTS nombre_apostador VARCHAR(200);

-- Verificacion
SELECT COUNT(*) AS filas_apuesta, COUNT(nombre_apostador) AS con_nombre
FROM apuesta;
