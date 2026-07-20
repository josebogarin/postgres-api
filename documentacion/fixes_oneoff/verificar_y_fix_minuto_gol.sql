-- ============================================================
-- 1. SOLO DIFERENCIAS (goles, amarillas, rojas, VAR)
-- ============================================================
WITH excel_data(num, gl, gv, amar, rojas, var_cnt) AS (VALUES
  (1, 2, 0, 3, 3, 1),
  (2, 2, 1, 1, 0, 0),
  (3, 1, 1, 5, 0, 0),
  (4, 4, 1, 6, 0, 2),
  (5, 0, 1, 4, 0, 0),
  (6, 2, 0, 1, 0, 0),
  (7, 1, 1, 2, 0, 0),
  (8, 1, 1, 3, 0, 1),
  (9, 1, 0, 4, 0, 0),
  (10, 7, 1, 0, 0, 0),
  (11, 2, 2, 3, 0, 0),
  (12, 5, 1, 1, 0, 1),
  (13, 1, 1, 1, 0, 0),
  (14, 0, 0, 2, 0, 0),
  (15, 2, 2, 1, 0, 0),
  (16, 1, 1, 4, 0, 1),
  (17, 3, 1, 0, 0, 1),
  (18, 1, 4, 1, 0, 0),
  (19, 3, 0, 0, 0, 1),
  (20, 3, 1, 1, 0, 2),
  (21, 1, 0, 3, 0, 0),
  (22, 4, 2, 0, 0, 1),
  (23, 1, 1, 4, 0, 0),
  (24, 1, 3, 2, 0, 0),
  (25, 1, 1, 3, 0, 0),
  (26, 4, 1, 3, 1, 1),
  (27, 6, 0, 2, 2, 3),
  (28, 1, 0, 2, 0, 0),
  (29, 3, 0, 4, 0, 0),
  (30, 0, 1, 3, 0, 0),
  (31, 0, 1, 2, 1, 0),
  (32, 2, 0, 7, 0, 1),
  (33, 2, 1, 0, 0, 0),
  (34, 0, 0, 6, 0, 0),
  (35, 5, 1, 3, 0, 0),
  (36, 0, 4, 0, 0, 0),
  (37, 2, 2, 4, 0, 1),
  (38, 4, 0, 2, 0, 1),
  (39, 0, 0, 2, 1, 2),
  (40, 1, 3, 3, 0, 0),
  (41, 3, 2, 0, 0, 0),
  (42, 3, 0, 1, 0, 0),
  (43, 2, 0, 4, 0, 1),
  (44, 1, 2, 2, 0, 1),
  (45, 0, 0, 2, 0, 0),
  (46, 0, 1, 2, 0, 0),
  (47, 5, 0, 2, 0, 0),
  (48, 1, 0, 3, 0, 0),
  (49, 0, 3, 3, 0, 0),
  (50, 4, 2, 3, 0, 1),
  (51, 2, 1, 3, 0, 0),
  (52, 3, 1, 2, 0, 0),
  (53, 0, 3, 1, 0, 0),
  (54, 1, 0, 2, 0, 0),
  (55, 0, 2, 3, 0, 0),
  (56, 2, 1, 4, 0, 1),
  (57, 1, 1, 3, 0, 0),
  (58, 1, 3, 0, 0, 0),
  (59, 3, 2, 2, 0, 1),
  (60, 0, 0, 2, 0, 0),
  (61, 1, 4, 2, 0, 0),
  (62, 5, 0, 4, 1, 1),
  (63, 1, 1, 7, 0, 1),
  (64, 1, 5, 2, 0, 2),
  (65, 0, 0, 4, 0, 0),
  (66, 0, 1, 4, 1, 0),
  (67, 0, 2, 3, 0, 1),
  (68, 2, 1, 2, 0, 1),
  (69, 3, 3, 1, 0, 0),
  (70, 1, 3, 3, 0, 0),
  (71, 0, 0, 1, 0, 2),
  (72, 3, 1, 5, 0, 1),
  (73, 0, 1, 0, 0, 2),
  (74, 1, 1, 4, 0, 1),
  (75, 1, 1, 1, 0, 0),
  (76, 2, 1, 5, 0, 1),
  (77, 3, 0, 0, 0, 0),
  (78, 1, 2, 1, 0, 0),
  (79, 2, 0, 3, 1, 0),
  (80, 2, 1, 2, 0, 1),
  (81, 2, 0, 1, 1, 1),
  (82, 3, 2, 2, 0, 1)
)
SELECT
  p.numero_fifa,
  COALESCE(el.nombre_es,el.nombre) AS local,
  p.goles_local AS bd_gl, e.gl AS xls_gl,
  p.goles_visitante AS bd_gv, e.gv AS xls_gv,
  COALESCE(ev.nombre_es,ev.nombre) AS visitante,
  p.amarillas AS bd_am, e.amar AS xls_am,
  p.rojas AS bd_ro,     e.rojas AS xls_ro,
  p.decisiones_var AS bd_var, e.var_cnt AS xls_var
FROM partido p
JOIN fase f ON f.id = p.fase_id
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
JOIN excel_data e ON e.num = p.numero_fifa
WHERE f.torneo_id = 2
  AND (
    p.goles_local IS DISTINCT FROM e.gl OR
    p.goles_visitante IS DISTINCT FROM e.gv OR
    p.amarillas IS DISTINCT FROM e.amar OR
    p.rojas IS DISTINCT FROM e.rojas OR
    p.decisiones_var IS DISTINCT FROM e.var_cnt
  )
ORDER BY p.numero_fifa;

-- ============================================================
-- 2. ACTUALIZAR minuto_primer_gol donde es NULL en BD
-- ============================================================
WITH excel_minuto(num, min_gol) AS (VALUES
  (1, 9),
  (2, 59),
  (3, 21),
  (4, 7),
  (5, 28),
  (6, 27),
  (7, 21),
  (8, 17),
  (9, 90),
  (10, 6),
  (11, 51),
  (12, 7),
  (13, 41),
  (14, 99),
  (15, 7),
  (16, 20),
  (17, 66),
  (18, 29),
  (19, 17),
  (20, 21),
  (21, 95),
  (22, 12),
  (23, 6),
  (24, 40),
  (25, 6),
  (26, 74),
  (27, 16),
  (28, 50),
  (29, 23),
  (30, 2),
  (31, 2),
  (32, 11),
  (33, 30),
  (34, 99),
  (35, 5),
  (36, 4),
  (37, 21),
  (38, 10),
  (39, 99),
  (40, 15),
  (41, 43),
  (42, 14),
  (43, 38),
  (44, 36),
  (45, 99),
  (46, 54),
  (47, 6),
  (48, 76),
  (49, 7),
  (50, 10),
  (51, 46),
  (52, 29),
  (53, 54),
  (54, 63),
  (55, 7),
  (56, 2),
  (57, 56),
  (58, 3),
  (59, 2),
  (60, 99),
  (61, 7),
  (62, 4),
  (63, 5),
  (64, 28),
  (65, 99),
  (66, 42),
  (67, 62),
  (68, 31),
  (69, 28),
  (70, 19),
  (71, 99),
  (72, 10),
  (73, 90),
  (74, 42),
  (75, 72),
  (76, 29),
  (77, 45),
  (78, 39),
  (79, 22),
  (80, 25),
  (81, 45),
  (82, 25)

)
UPDATE partido p
SET minuto_primer_gol = e.min_gol
FROM excel_minuto e
JOIN fase f ON f.id = p.fase_id
WHERE p.numero_fifa = e.num
  AND f.torneo_id = 2
  AND p.minuto_primer_gol IS NULL;

SELECT
  p.numero_fifa,
  COALESCE(el.nombre_es,el.nombre)||' vs '||COALESCE(ev.nombre_es,ev.nombre) AS partido,
  p.minuto_primer_gol AS min_bd
FROM partido p
JOIN fase f ON f.id = p.fase_id
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE f.torneo_id=2 AND p.estado='finalizado' AND p.minuto_primer_gol IS NULL
ORDER BY p.numero_fifa;
