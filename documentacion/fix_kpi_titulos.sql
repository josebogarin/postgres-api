-- ============================================================
-- Fix: corrige títulos de KPIs con encoding roto
-- Ejecutar en app_db:
-- Get-Content "C:\proyecto FAST API\documentacion\fix_kpi_titulos.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

UPDATE portal_kpis SET titulo = 'Maximo'
WHERE titulo ILIKE '%ximo%' AND titulo NOT ILIKE 'Maximo';

UPDATE portal_kpis SET titulo = 'Minimo'
WHERE titulo ILIKE '%nimo%' AND titulo NOT IN ('Minimo','Apostadores','Pronósticos','Pronosticos');

-- Verificar
SELECT id, titulo, orden FROM portal_kpis ORDER BY orden;
