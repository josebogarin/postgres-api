-- ============================================================
-- seed_playoff_mundial.sql  (v2 — schema corregido)
-- Reparación fase de grupos + creación playoff Mundial 2026
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\seed_playoff_mundial.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- 1. Reasignar partidos de fase_id=31 ('Group Stage - 3') al grupo correcto
UPDATE partido p
SET fase_id = (
    SELECT pa.fase_id
    FROM participacion pa
    JOIN fase f ON f.id = pa.fase_id
    WHERE pa.equipo_id IN (p.equipo_local_id, p.equipo_visitante_id)
      AND f.torneo_id = 2
      AND f.nombre LIKE 'Grupo %'
    LIMIT 1
)
WHERE p.fase_id = 31
  AND p.torneo_id = 2;

-- 2. Eliminar fases vacías/espurias (ids 19 y 31 si quedan sin partidos)
DELETE FROM fase
WHERE torneo_id = 2
  AND nombre NOT LIKE 'Grupo %'
  AND tipo IN ('grupo', 'otro')
  AND NOT EXISTS (SELECT 1 FROM partido WHERE fase_id = fase.id);

-- 3. Equipo placeholder 'Por Definir' para partidos playoff sin equipos aún
INSERT INTO equipo (nombre, nombre_es)
SELECT 'TBD', 'Por Definir'
WHERE NOT EXISTS (SELECT 1 FROM equipo WHERE nombre = 'TBD');

-- 4. Crear fases de playoff
INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Ronda de 32', 'ronda32', 15, true
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Ronda de 32'
);

INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Octavos de Final', 'ronda16', 20, true
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Octavos de Final'
);

INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Cuartos de Final', 'cuartos', 30, true
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Cuartos de Final'
);

INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Semifinales', 'semis', 40, true
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Semifinales'
);

INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Tercer Puesto', 'tercer_puesto', 45, false
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Tercer Puesto'
);

INSERT INTO fase (torneo_id, nombre, tipo, orden, visible_apostador)
SELECT 2, 'Final', 'final', 50, true
WHERE NOT EXISTS (
    SELECT 1 FROM fase WHERE torneo_id = 2 AND nombre = 'Final'
);

-- 5. Insertar partidos playoff placeholder (equipos = TBD)
-- Partido #73: Ronda de 32 | 2026-06-28 15:00:00 | Los Angeles
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-28 15:00:00'::timestamptz, 'Los Angeles', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-28 15:00:00'::timestamptz
        AND ciudad = 'Los Angeles'
  );

-- Partido #74: Ronda de 32 | 2026-06-29 13:00:00 | Houston
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-29 13:00:00'::timestamptz, 'Houston', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-29 13:00:00'::timestamptz
        AND ciudad = 'Houston'
  );

-- Partido #75: Ronda de 32 | 2026-06-29 16:30:00 | Boston
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-29 16:30:00'::timestamptz, 'Boston', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-29 16:30:00'::timestamptz
        AND ciudad = 'Boston'
  );

-- Partido #76: Ronda de 32 | 2026-06-29 21:00:00 | Monterrey
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-29 21:00:00'::timestamptz, 'Monterrey', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-29 21:00:00'::timestamptz
        AND ciudad = 'Monterrey'
  );

-- Partido #77: Ronda de 32 | 2026-06-30 13:00:00 | Dallas
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-30 13:00:00'::timestamptz, 'Dallas', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-30 13:00:00'::timestamptz
        AND ciudad = 'Dallas'
  );

-- Partido #78: Ronda de 32 | 2026-06-30 17:00:00 | N. York/N. Jersey
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-30 17:00:00'::timestamptz, 'N. York/N. Jersey', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-30 17:00:00'::timestamptz
        AND ciudad = 'N. York/N. Jersey'
  );

-- Partido #79: Ronda de 32 | 2026-06-30 21:00:00 | Ciudad de Mexico
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-06-30 21:00:00'::timestamptz, 'Ciudad de Mexico', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-06-30 21:00:00'::timestamptz
        AND ciudad = 'Ciudad de Mexico'
  );

-- Partido #80: Ronda de 32 | 2026-07-01 12:00:00 | Atlanta
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-01 12:00:00'::timestamptz, 'Atlanta', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-01 12:00:00'::timestamptz
        AND ciudad = 'Atlanta'
  );

-- Partido #81: Ronda de 32 | 2026-07-01 16:00:00 | Seattle
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-01 16:00:00'::timestamptz, 'Seattle', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-01 16:00:00'::timestamptz
        AND ciudad = 'Seattle'
  );

-- Partido #82: Ronda de 32 | 2026-07-01 20:00:00 | San Francisco
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-01 20:00:00'::timestamptz, 'San Francisco', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-01 20:00:00'::timestamptz
        AND ciudad = 'San Francisco'
  );

-- Partido #83: Ronda de 32 | 2026-07-02 15:00:00 | Los Angeles
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-02 15:00:00'::timestamptz, 'Los Angeles', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-02 15:00:00'::timestamptz
        AND ciudad = 'Los Angeles'
  );

-- Partido #84: Ronda de 32 | 2026-07-02 19:00:00 | Toronto
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-02 19:00:00'::timestamptz, 'Toronto', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-02 19:00:00'::timestamptz
        AND ciudad = 'Toronto'
  );

-- Partido #85: Ronda de 32 | 2026-07-03 23:00:00 | Vancouver
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-03 23:00:00'::timestamptz, 'Vancouver', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-03 23:00:00'::timestamptz
        AND ciudad = 'Vancouver'
  );

-- Partido #86: Ronda de 32 | 2026-07-03 14:00:00 | Dallas
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-03 14:00:00'::timestamptz, 'Dallas', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-03 14:00:00'::timestamptz
        AND ciudad = 'Dallas'
  );

-- Partido #87: Ronda de 32 | 2026-07-03 18:00:00 | Miami
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-03 18:00:00'::timestamptz, 'Miami', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-03 18:00:00'::timestamptz
        AND ciudad = 'Miami'
  );

-- Partido #88: Ronda de 32 | 2026-07-03 21:30:00 | Kansas City
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-03 21:30:00'::timestamptz, 'Kansas City', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Ronda de 32'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-03 21:30:00'::timestamptz
        AND ciudad = 'Kansas City'
  );

-- Partido #89: Octavos de Final | 2026-07-04 13:00:00 | Houston
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-04 13:00:00'::timestamptz, 'Houston', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-04 13:00:00'::timestamptz
        AND ciudad = 'Houston'
  );

-- Partido #90: Octavos de Final | 2026-07-04 17:00:00 | Filadelfia
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-04 17:00:00'::timestamptz, 'Filadelfia', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-04 17:00:00'::timestamptz
        AND ciudad = 'Filadelfia'
  );

-- Partido #91: Octavos de Final | 2026-07-05 16:00:00 | N. York/N. Jersey
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-05 16:00:00'::timestamptz, 'N. York/N. Jersey', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-05 16:00:00'::timestamptz
        AND ciudad = 'N. York/N. Jersey'
  );

-- Partido #92: Octavos de Final | 2026-07-05 20:00:00 | Ciudad de Mexico
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-05 20:00:00'::timestamptz, 'Ciudad de Mexico', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-05 20:00:00'::timestamptz
        AND ciudad = 'Ciudad de Mexico'
  );

-- Partido #93: Octavos de Final | 2026-07-06 15:00:00 | Dallas
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-06 15:00:00'::timestamptz, 'Dallas', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-06 15:00:00'::timestamptz
        AND ciudad = 'Dallas'
  );

-- Partido #94: Octavos de Final | 2026-07-06 20:00:00 | Seattle
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-06 20:00:00'::timestamptz, 'Seattle', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-06 20:00:00'::timestamptz
        AND ciudad = 'Seattle'
  );

-- Partido #95: Octavos de Final | 2026-07-07 12:00:00 | Atlanta
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-07 12:00:00'::timestamptz, 'Atlanta', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-07 12:00:00'::timestamptz
        AND ciudad = 'Atlanta'
  );

-- Partido #96: Octavos de Final | 2026-07-07 16:00:00 | Vancouver
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-07 16:00:00'::timestamptz, 'Vancouver', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Octavos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-07 16:00:00'::timestamptz
        AND ciudad = 'Vancouver'
  );

-- Partido #97: Cuartos de Final | 2026-07-09 16:00:00 | Boston
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-09 16:00:00'::timestamptz, 'Boston', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Cuartos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-09 16:00:00'::timestamptz
        AND ciudad = 'Boston'
  );

-- Partido #98: Cuartos de Final | 2026-07-10 15:00:00 | Los Angeles
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-10 15:00:00'::timestamptz, 'Los Angeles', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Cuartos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-10 15:00:00'::timestamptz
        AND ciudad = 'Los Angeles'
  );

-- Partido #99: Cuartos de Final | 2026-07-11 17:00:00 | Miami
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-11 17:00:00'::timestamptz, 'Miami', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Cuartos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-11 17:00:00'::timestamptz
        AND ciudad = 'Miami'
  );

-- Partido #100: Cuartos de Final | 2026-07-11 21:00:00 | Kansas City
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-11 21:00:00'::timestamptz, 'Kansas City', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Cuartos de Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-11 21:00:00'::timestamptz
        AND ciudad = 'Kansas City'
  );

-- Partido #101: Semifinales | 2026-07-14 15:00:00 | Dallas
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-14 15:00:00'::timestamptz, 'Dallas', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Semifinales'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-14 15:00:00'::timestamptz
        AND ciudad = 'Dallas'
  );

-- Partido #102: Semifinales | 2026-07-15 15:00:00 | Atlanta
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-15 15:00:00'::timestamptz, 'Atlanta', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Semifinales'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-15 15:00:00'::timestamptz
        AND ciudad = 'Atlanta'
  );

-- Partido #103: Tercer Puesto | 2026-07-18 17:00:00 | Miami
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-18 17:00:00'::timestamptz, 'Miami', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Tercer Puesto'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-18 17:00:00'::timestamptz
        AND ciudad = 'Miami'
  );

-- Partido #104: Final | 2026-07-19 15:00:00 | N. York/N. Jersey
INSERT INTO partido (torneo_id, fase_id, equipo_local_id, equipo_visitante_id, fecha, ciudad, estado)
SELECT 2, f.id, tbd.id, tbd.id,
       '2026-07-19 15:00:00'::timestamptz, 'N. York/N. Jersey', 'programado'
FROM fase f
CROSS JOIN (SELECT id FROM equipo WHERE nombre = 'TBD') tbd
WHERE f.torneo_id = 2
  AND f.nombre = 'Final'
  AND NOT EXISTS (
      SELECT 1 FROM partido
      WHERE torneo_id = 2
        AND fase_id = f.id
        AND fecha = '2026-07-19 15:00:00'::timestamptz
        AND ciudad = 'N. York/N. Jersey'
  );

-- 6. Verificación final
SELECT f.nombre, f.tipo, f.orden, COUNT(p.id) AS partidos
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = 2
WHERE f.torneo_id = 2
GROUP BY f.id, f.nombre, f.tipo, f.orden
ORDER BY f.orden, f.nombre;

COMMIT;