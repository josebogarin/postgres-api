-- ============================================================
-- Seed KPIs de BECBUC en portal_kpis (app_db)
-- Ejecutar: Get-Content "...\seed_becbuc_kpis.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

DO $$
DECLARE
  v_id BIGINT;
BEGIN
  SELECT id INTO v_id
  FROM sistema
  WHERE UPPER(nombre) = 'BECBUC' OR nombre_bd = 'becbuc'
  LIMIT 1;

  IF v_id IS NULL THEN
    RAISE NOTICE 'Sistema BECBUC no encontrado en app_db. Levantá el backend primero (crea el sistema al arrancar).';
    RETURN;
  END IF;

  -- Idempotente: elimina y recrea
  DELETE FROM portal_kpis WHERE id_sistema = v_id;

  INSERT INTO portal_kpis
    (id_sistema, titulo, icono, color, query_sql, formato, decimales, prefijo, sufijo, orden, es_activo)
  VALUES
    -- 1. Apostadores que han apostado al menos una vez
    (v_id,
     'Apostadores',
     'ti-users',
     'cyan',
     'SELECT COUNT(DISTINCT apostador_id) FROM apuesta a JOIN partido p ON p.id = a.partido_id WHERE p.torneo_id = (SELECT id FROM torneo ORDER BY id DESC LIMIT 1)',
     'number', 0, '', '', 1, true),

    -- 2. Total de pronósticos registrados
    (v_id,
     'Pronósticos',
     'ti-report-analytics',
     'teal',
     'SELECT COUNT(*) FROM apuesta a JOIN partido p ON p.id = a.partido_id WHERE p.torneo_id = (SELECT id FROM torneo ORDER BY id DESC LIMIT 1)',
     'number', 0, '', '', 2, true),

    -- 3. Puntaje en juego (suma de puntos ya calculados)
    (v_id,
     'Pts en juego',
     'ti-coin',
     'amber',
     'SELECT COALESCE(SUM(a.puntos), 0) FROM apuesta a JOIN partido p ON p.id = a.partido_id WHERE p.torneo_id = (SELECT id FROM torneo ORDER BY id DESC LIMIT 1) AND a.puntos IS NOT NULL',
     'number', 0, '', ' pts', 3, true),

    -- 4. Puntaje máximo de un apostador
    (v_id,
     'Maximo',
     'ti-trending-up',
     'green',
     'SELECT COALESCE(MAX(sub.total), 0) FROM (SELECT a.apostador_id, SUM(COALESCE(a.puntos,0)) AS total FROM apuesta a JOIN partido p ON p.id = a.partido_id WHERE p.torneo_id = (SELECT id FROM torneo ORDER BY id DESC LIMIT 1) GROUP BY a.apostador_id) sub',
     'number', 0, '', ' pts', 4, true),

    -- 5. Puntaje mínimo de un apostador (entre los que tienen pronósticos)
    (v_id,
     'Minimo',
     'ti-trending-down',
     'red',
     'SELECT COALESCE(MIN(sub.total), 0) FROM (SELECT a.apostador_id, SUM(COALESCE(a.puntos,0)) AS total FROM apuesta a JOIN partido p ON p.id = a.partido_id WHERE p.torneo_id = (SELECT id FROM torneo ORDER BY id DESC LIMIT 1) GROUP BY a.apostador_id) sub',
     'number', 0, '', ' pts', 5, true);

  RAISE NOTICE 'KPIs de BECBUC insertados (id_sistema = %). Líder y Último se cargan vía endpoint /bets/stats.', v_id;
END $$;
