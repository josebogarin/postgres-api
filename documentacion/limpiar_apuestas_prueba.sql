-- ============================================================
-- LIMPIEZA DE APUESTAS DE PRUEBA
-- Usuarios: jose, andres, apostador2, apostador5
-- ============================================================
-- PASO 1: Verificar IDs (ejecutar en app_db para confirmar)
--   docker exec -it core-postgres psql -U app_user -d app_db
-- ============================================================
SELECT id, username, is_active
FROM users
WHERE username IN ('jose', 'andres', 'apostador2', 'apostador5')
   OR username ILIKE 'apostador 2'
   OR username ILIKE 'apostador 5'
ORDER BY id;

-- ============================================================
-- PASO 2: Limpiar datos en becbuc
-- Reemplazar (1,2,3,4) con los IDs reales encontrados arriba
-- Ejecutar en becbuc:
--   docker exec -it core-postgres psql -U app_user -d becbuc
-- ============================================================

-- Ver qué apostadores tienen datos ahora:
SELECT u.username, COUNT(pd.id) AS filas_puntaje,
       COALESCE(SUM(pd.pts_total),0) AS pts_total
FROM puntaje_detalle pd
JOIN apuesta a ON a.partido_id = pd.partido_id AND a.apostador_id = pd.apostador_id
-- (No se puede hacer JOIN cross-db; usar los IDs directamente)
GROUP BY u.username;

-- ============================================================
-- LIMPIEZA REAL (reemplazar los IDs según PASO 1)
-- ============================================================
BEGIN;

-- Reemplazar (1, 2, 5) con los IDs reales:
DO $$
DECLARE
  ids_prueba INT[] := ARRAY[1, 2, 5];   -- <-- AJUSTAR CON IDs REALES
BEGIN
  DELETE FROM puntaje_detalle WHERE apostador_id = ANY(ids_prueba);
  DELETE FROM puntaje_global   WHERE apostador_id = ANY(ids_prueba);
  DELETE FROM apuesta_global   WHERE apostador_id = ANY(ids_prueba);
  DELETE FROM apuesta          WHERE apostador_id = ANY(ids_prueba);

  RAISE NOTICE 'Limpieza completada para apostadores: %', ids_prueba;
END;
$$;

COMMIT;

-- Verificar que quedó limpio:
SELECT apostador_id, COUNT(*) AS registros
FROM apuesta
WHERE apostador_id = ANY(ARRAY[1, 2, 5])   -- <-- AJUSTAR
GROUP BY apostador_id;
