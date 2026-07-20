-- FIX: Activar solo la competicion de Copa Mundial FIFA 2026
-- El portal filtra torneos por competicion.es_activo = TRUE
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\fix_torneo_activo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

\echo '=== COMPETICIONES ACTUALES ==='
SELECT c.id, c.nombre, c.es_activo, t.id AS torneo_id, t.nombre AS torneo, t.estado
FROM competicion c
LEFT JOIN torneo t ON t.competicion_id = c.id
ORDER BY c.id;

\echo ''
\echo '=== DESACTIVANDO TODAS LAS COMPETICIONES ==='
UPDATE competicion SET es_activo = FALSE;

\echo ''
\echo '=== ACTIVANDO SOLO LA COMPETICION DE COPA MUNDIAL FIFA 2026 ==='
-- La competicion del torneo id=2 (Copa Mundial FIFA 2026)
UPDATE competicion SET es_activo = TRUE
WHERE id = (SELECT competicion_id FROM torneo WHERE id = 2);

\echo ''
\echo '=== VERIFICACION: torneos que devolvera /activas ==='
SELECT t.id, t.nombre, t.estado, t.datos_cargados, c.nombre AS competicion, c.es_activo
FROM torneo t
JOIN competicion c ON c.id = t.competicion_id
WHERE c.es_activo = TRUE
ORDER BY t.id;

\echo ''
\echo '=== FASES OK: Copa Mundial FIFA 2026 (id=2) ==='
SELECT f.nombre, f.tipo, COUNT(p.id) AS partidos
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id
WHERE f.torneo_id = 2
GROUP BY f.id, f.nombre, f.tipo, f.orden
ORDER BY f.orden, f.nombre;
