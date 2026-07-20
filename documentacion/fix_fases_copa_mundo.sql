-- FIX FASES COPA DEL MUNDO 2026
-- Ejecutar DESPUES de ver el resultado de diagnostico_fases.sql
-- Comando: Get-Content "C:\proyecto FAST API\documentacion\fix_fases_copa_mundo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- 1. Ver estado actual antes de modificar
\echo '=== FASES ACTUALES ==='
SELECT f.id, f.torneo_id, f.nombre, f.tipo, f.orden,
       COUNT(p.id) AS partidos
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id
GROUP BY f.id, f.torneo_id, f.nombre, f.tipo, f.orden
ORDER BY f.torneo_id, f.orden, f.nombre;

-- 2. Eliminar fases que NO pertenecen al torneo Copa del Mundo 2026
--    (Group Stage - 3/4/5/6 y Qualification Round 1/2/3 y similares)
--    ATENCION: solo elimina fases SIN partidos asociados (safe delete)
\echo ''
\echo '=== ELIMINANDO FASES SIN PARTIDOS CON NOMBRES INCORRECTOS ==='
DELETE FROM fase
WHERE nombre ~* '(group stage|qualification round|qualifying)'
  AND id NOT IN (SELECT DISTINCT fase_id FROM partido WHERE fase_id IS NOT NULL)
RETURNING id, torneo_id, nombre, tipo;

-- 3. Si las fases incorrectas TIENEN partidos, reasignar partidos a la fase correcta
--    primero y luego eliminar. Verificar con la query de diagnóstico.

-- 4. Asegurar que las fases de grupo se llamen correctamente (A, B, C... L)
--    Si hay más de 12 grupos, ver cuáles sobran
\echo ''
\echo '=== FASES TIPO GRUPO RESTANTES ==='
SELECT id, torneo_id, nombre, tipo, orden,
       (SELECT COUNT(*) FROM partido p WHERE p.fase_id = f.id) AS partidos
FROM fase f
WHERE tipo = 'grupo'
ORDER BY torneo_id, nombre;

-- 5. Verificar fases KO
\echo ''
\echo '=== FASES KO RESTANTES ==='
SELECT id, torneo_id, nombre, tipo, orden,
       (SELECT COUNT(*) FROM partido p WHERE p.fase_id = f.id) AS partidos
FROM fase f
WHERE tipo NOT IN ('grupo')
ORDER BY torneo_id, f.orden;

-- 6. Renombrar "Octavos de Final" a "Ronda de 32" si tiene 16 partidos (es la R32 mal nombrada)
\echo ''
\echo '=== REVISANDO NOMBRE "Octavos de Final" ==='
SELECT f.id, f.nombre, f.tipo, COUNT(p.id) AS partidos,
       MIN(p.fecha) AS primera_fecha, MAX(p.fecha) AS ultima_fecha
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id
WHERE f.nombre ILIKE '%octavo%'
GROUP BY f.id, f.nombre, f.tipo;

-- Renombrar si el "Octavos de Final" real tiene 16 partidos (= es Ronda de 32)
UPDATE fase
SET nombre = 'Ronda de 32', tipo = 'ronda32', orden = 15
WHERE nombre ILIKE '%octavo%'
  AND (SELECT COUNT(*) FROM partido p WHERE p.fase_id = fase.id) = 16
RETURNING id, nombre, tipo, orden;

-- 7. Estado final
\echo ''
\echo '=== ESTADO FINAL DE FASES ==='
SELECT t.nombre AS torneo, f.id, f.nombre, f.tipo, f.orden,
       COUNT(p.id) AS partidos,
       SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END) AS finalizados
FROM fase f
JOIN torneo t ON t.id = f.torneo_id
LEFT JOIN partido p ON p.fase_id = f.id
GROUP BY t.nombre, f.id, f.nombre, f.tipo, f.orden
ORDER BY t.nombre, f.orden, f.nombre;
