DO $$
DECLARE
  v_sistema_id  BIGINT;
  v_cabecera_id BIGINT;
BEGIN
  SELECT id INTO v_sistema_id FROM sistema WHERE nombre = 'Ventas DB' LIMIT 1;
  IF v_sistema_id IS NULL THEN RAISE NOTICE 'No encontrado'; RETURN; END IF;

  SELECT id INTO v_cabecera_id FROM cabecera WHERE id_sistema = v_sistema_id AND nombre = 'factura' LIMIT 1;
  IF v_cabecera_id IS NULL THEN
    INSERT INTO cabecera (id_sistema, nombre, descripcion, es_activo)
    VALUES (v_sistema_id, 'factura', 'Facturas de venta', true)
    RETURNING id INTO v_cabecera_id;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cabecera_id AND nombre = 'item_factura') THEN
    INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
    VALUES (v_cabecera_id, 'item_factura', 'Items de factura', 'id_factura', true);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cabecera_id AND nombre = 'pagos_factura') THEN
    INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
    VALUES (v_cabecera_id, 'pagos_factura', 'Pagos de factura', 'id_factura', true);
  END IF;

  RAISE NOTICE 'OK. Sistema: %, Cabecera: %', v_sistema_id, v_cabecera_id;
END;
$$;
