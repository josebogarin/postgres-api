-- restaurar_partido143.sql
-- Restaura resultados de Mexico 2-0 South Africa (partido_id=143, torneo_id=2)
-- Fixture API-Football: 1489369

UPDATE partido SET
    goles_local       = 2,
    goles_visitante   = 0,
    estado            = 'finalizado',
    amarillas         = 3,
    rojas             = 3,
    decisiones_var    = 0,
    minuto_primer_gol = 9,
    penales_local     = NULL,
    penales_visitante = NULL,
    api_fixture_id    = 1489369
WHERE id = 143;

-- Verificar
SELECT id, goles_local, goles_visitante, estado,
       amarillas, rojas, decisiones_var, minuto_primer_gol,
       api_fixture_id
FROM partido WHERE id = 143;
