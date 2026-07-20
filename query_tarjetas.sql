\pset format unaligned
\pset fieldsep '|'
SELECT p.numero_fifa,
       ev->>'detail' AS tipo,
       ev->'player'->>'id' AS player_id,
       ev->'player'->>'name' AS player_name,
       ev->>'comments' AS comments,
       ev->'time'->>'elapsed' AS minuto
FROM partido p,
     jsonb_array_elements(p.eventos_api) AS ev
WHERE p.estado = 'finalizado'
  AND p.eventos_api IS NOT NULL
  AND jsonb_array_length(p.eventos_api) > 0
  AND ev->>'type' = 'Card'
ORDER BY p.numero_fifa, (ev->'time'->>'elapsed')::int
LIMIT 50;
