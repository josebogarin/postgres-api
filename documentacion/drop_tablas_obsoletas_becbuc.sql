-- ============================================================
-- Drop de tablas obsoletas en becbuc (complemento del 5-jun-2026)
--
-- Tablas creadas en migracion_torneos.sql (versión vieja del schema)
-- que nunca se usan en el portal ni en ningún endpoint activo.
--
-- Tablas activas que NO se tocan:
--   competicion, torneo, equipo, fase, partido, participacion,
--   apuesta, auditoria_apuestas, mensaje_admin
--
-- Ejecutar en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\drop_tablas_obsoletas_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

DROP TABLE IF EXISTS torneo_equipo         CASCADE;
DROP TABLE IF EXISTS jugador_estadistica   CASCADE;

-- Por si quedaron restos de alguna migración previa
DROP TABLE IF EXISTS partido_estadistica   CASCADE;
DROP TABLE IF EXISTS partido_evento        CASCADE;
DROP TABLE IF EXISTS partidos              CASCADE;
DROP TABLE IF EXISTS equipos               CASCADE;
DROP TABLE IF EXISTS grupos                CASCADE;
DROP TABLE IF EXISTS fases                 CASCADE;
DROP TABLE IF EXISTS competencias          CASCADE;

-- Verificación: tablas que deben quedar
SELECT tablename AS tabla, 'OK' AS estado
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'competicion','torneo','equipo','fase','partido',
    'participacion','apuesta','auditoria_apuestas','mensaje_admin'
  )
ORDER BY tablename;
