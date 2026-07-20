-- Fix VAR incorrecto en P27 y P39 (sobreescrito por ESPN verify)
-- P27 Canada vs Qatar (id=169): ESPN puso 3, correcto es 2
-- P39 Belgium vs Iran  (id=180): ESPN puso 2, correcto es 1

UPDATE partido SET decisiones_var = 2 WHERE id = 169;
UPDATE partido SET decisiones_var = 1 WHERE id = 180;

-- Verificar
SELECT id,
       COALESCE(el.nombre_es, el.nombre) AS local,
       COALESCE(ev.nombre_es, ev.nombre) AS visitante,
       decisiones_var AS var_corregido
FROM partido p
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.id IN (169, 180);
