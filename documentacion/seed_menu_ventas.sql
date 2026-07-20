-- ============================================================
-- Seed: ítems de menú para el sistema Ventas DB (id=8)
-- ============================================================

DO $$
DECLARE
  v_sid bigint;
BEGIN
  SELECT id INTO v_sid FROM sistema WHERE nombre_bd = 'ventas_db' LIMIT 1;

  IF v_sid IS NULL THEN
    RAISE NOTICE 'Sistema ventas_db no encontrado.';
    RETURN;
  END IF;

  -- Reemplazar ítems existentes
  DELETE FROM portal_menu WHERE id_sistema = v_sid;

  INSERT INTO portal_menu (id_sistema, titulo, orden, descripcion, tabla, url, icono, es_activo)
  VALUES
    (v_sid, 'Facturas',  1, 'Facturas con sus ítems y pagos (vista maestro-detalle)', 'factura',   NULL, 'ti-receipt',       true),
    (v_sid, 'Pedidos',   2, 'Registro de pedidos',                                   'pedidos',   NULL, 'ti-clipboard-list',true),
    (v_sid, 'Pagos',     3, 'Pagos registrados',                                     'pagos_factura', NULL, 'ti-cash',       true),
    (v_sid, 'Productos', 4, 'Catálogo de productos',                                 'productos', NULL, 'ti-box',           true)
  ON CONFLICT DO NOTHING;

  RAISE NOTICE 'Menú Ventas DB actualizado para sistema id=%', v_sid;
END $$;
