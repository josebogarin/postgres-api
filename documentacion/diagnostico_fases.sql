-- DIAGNOSTICO: ver todos los torneos y sus fases
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\diagnostico_fases.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

\echo '=== TORNEOS EN LA BD ==='
SELECT id, nombre, activo FROM torneo ORDER BY id;

\echo ''
\echo '=== FASES POR TORNEO ==='
SELECT t.id AS torneo_id, t.nombre AS torneo,
       f.id AS fase_id, f.nombre, f.tipo, f.orden,
       COUNT(p.id) AS partidos
FROM fase f
JOIN torneo t ON t.id = f.torneo_id
LEFT JOIN partido p ON p.fase_id = f.id
GROUP BY t.id, t.nombre, f.id, f.nombre, f.tipo, f.orden
ORDER BY t.id, f.orden, f.nombre;

\echo ''
\echo '=== PARTIDOS POR TORNEO (resumen) ==='
SELECT t.id, t.nombre, COUNT(p.id) AS total_partidos,
       SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END) AS finalizados
FROM torneo t
LEFT JOIN partido p ON p.torneo_id = t.id
GROUP BY t.id, t.nombre
ORDER BY t.id;
