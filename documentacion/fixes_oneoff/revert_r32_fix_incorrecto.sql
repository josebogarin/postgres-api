-- revert_r32_fix_incorrecto.sql
-- REVERTER el fix incorrecto que cambio los visitantes de Argentina y Colombia.
-- El fix apunto a numero_fifa=86 y 87, pero esos son Argentina y Colombia (correctos).
-- Restaurar los visitantes originales:
--   P86 Argentina vs Cape Verde Islands  (no Algeria)
--   P87 Colombia   vs Ghana               (no Senegal)

BEGIN;

-- Verificar estado actual (incorrecto)
SELECT p.numero_fifa, el.nombre AS local, ev.nombre AS visitante, p.estado
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.numero_fifa IN (86, 87)
ORDER BY p.numero_fifa;

-- Restaurar P86: visitante = Cape Verde Islands
UPDATE partido
SET equipo_visitante_id = (
    SELECT id FROM equipo
    WHERE LOWER(nombre) LIKE '%cape verde%'
       OR LOWER(nombre_es) LIKE '%cabo verde%'
    LIMIT 1
)
WHERE numero_fifa = 86
  AND estado != 'finalizado';

-- Restaurar P87: visitante = Ghana
UPDATE partido
SET equipo_visitante_id = (
    SELECT id FROM equipo
    WHERE LOWER(nombre) = 'ghana'
    LIMIT 1
)
WHERE numero_fifa = 87
  AND estado != 'finalizado';

-- Verificar estado corregido
SELECT p.numero_fifa, el.nombre AS local, ev.nombre AS visitante, p.estado
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.numero_fifa IN (86, 87)
ORDER BY p.numero_fifa;

COMMIT;
