-- ============================================================
-- PATCH v2: Corregir competiciones y agregar temporadas activas
-- Ejecutar en app_db
-- ============================================================

-- Corrección de competiciones (liga 6 = Africa Cup, no Mundial Femenino)
DELETE FROM competicion WHERE api_league_id = 6;

UPDATE competicion SET
    nombre       = 'Copa Mundial FIFA',
    nombre_corto = 'Mundial',
    emoji        = '🌍'
WHERE api_league_id = 1;

UPDATE competicion SET
    nombre       = 'UEFA Champions League',
    nombre_corto = 'Champions',
    emoji        = '⭐'
WHERE api_league_id = 2;

UPDATE competicion SET
    nombre       = 'UEFA Eurocopa',
    nombre_corto = 'Eurocopa',
    emoji        = '🏆'
WHERE api_league_id = 4;

UPDATE competicion SET
    nombre       = 'Copa América',
    nombre_corto = 'Copa América',
    emoji        = '🏆'
WHERE api_league_id = 9;

UPDATE competicion SET
    nombre       = 'Copa Libertadores',
    nombre_corto = 'Libertadores',
    emoji        = '🦅'
WHERE api_league_id = 13;

-- Insertar torneos activos con la temporada correcta de la API
INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
SELECT id, 2026, 'Copa Mundial FIFA 2026',      2026, 'en_curso'
FROM competicion WHERE api_league_id = 1
ON CONFLICT (competicion_id, anio) DO UPDATE SET api_season=2026, estado='en_curso';

INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
SELECT id, 2026, 'Champions League 2025/26',    2025, 'en_curso'
FROM competicion WHERE api_league_id = 2
ON CONFLICT (competicion_id, anio) DO UPDATE SET api_season=2025, estado='en_curso';

INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
SELECT id, 2024, 'UEFA Eurocopa 2024',           2024, 'finalizado'
FROM competicion WHERE api_league_id = 4
ON CONFLICT (competicion_id, anio) DO UPDATE SET api_season=2024, estado='finalizado';

INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
SELECT id, 2024, 'Copa América 2024',            2024, 'finalizado'
FROM competicion WHERE api_league_id = 9
ON CONFLICT (competicion_id, anio) DO UPDATE SET api_season=2024, estado='finalizado';

INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
SELECT id, 2026, 'Copa Libertadores 2026',       2026, 'en_curso'
FROM competicion WHERE api_league_id = 13
ON CONFLICT (competicion_id, anio) DO UPDATE SET api_season=2026, estado='en_curso';

SELECT c.emoji, c.nombre, t.anio, t.api_season, t.estado
FROM torneo t JOIN competicion c ON c.id = t.competicion_id
ORDER BY c.id;
