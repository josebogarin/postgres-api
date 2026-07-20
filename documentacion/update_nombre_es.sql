-- Actualizar nombre_es de equipos para resolución automática en importación
-- Sesión 29 — ejecutar:
-- Get-Content "C:\proyecto FAST API\documentacion\update_nombre_es.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

UPDATE equipo SET nombre_es = 'COSTA DE MARFIL'       WHERE nombre = 'Ivory Coast'       AND (nombre_es IS NULL OR nombre_es = nombre);
UPDATE equipo SET nombre_es = 'INGLATERRA'             WHERE nombre = 'England'            AND (nombre_es IS NULL OR nombre_es = nombre);
UPDATE equipo SET nombre_es = 'ALEMANIA'               WHERE nombre = 'Germany'            AND (nombre_es IS NULL OR nombre_es = nombre);
UPDATE equipo SET nombre_es = 'COREA DEL SUR'          WHERE nombre ILIKE 'korea republic'         AND (nombre_es IS NULL OR nombre_es = nombre);
UPDATE equipo SET nombre_es = 'ESPAÑA'                 WHERE nombre = 'Spain'              AND (nombre_es IS NULL OR nombre_es = nombre);
UPDATE equipo SET nombre_es = 'BOSNIA Y HERZEGOVINA'   WHERE nombre ILIKE 'bosnia%'        AND (nombre_es IS NULL OR nombre_es = nombre);

-- Verificar
SELECT nombre, nombre_es FROM equipo
WHERE nombre IN ('Ivory Coast','England','Germany','Spain')
   OR nombre ILIKE 'korea%'
   OR nombre ILIKE 'bosnia%'
ORDER BY nombre;
