-- =============================================================================
-- MIGRACIÓN: campo_fk en detalle + configuración factura/item_factura/pagos_factura
-- Ejecutar: Get-Content "migracion_cabecera_detalle.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- =============================================================================

-- Paso 1: Agregar campo_fk a detalle (si no existe)
ALTER TABLE detalle ADD COLUMN IF NOT EXISTS campo_fk VARCHAR(100);

-- Paso 2: Insertar configuración cabecera-detalle
-- IMPORTANTE: Cambiar 'Nombre del Sistema' por el nombre exacto del sistema en app_db
DO $$
DECLARE
  v_sistema_id  BIGINT;
  v_cabecera_id BIGINT;
BEGIN
  SELECT id INTO v_sistema_id
  FROM sistema
  WHERE nombre = 'Nombre del Sistema'  -- <-- CAMBIAR AQUI
  LIMIT 1;

  IF v_sistema_id IS NULL THEN
    RAISE NOTICE 'AVISO: Sistema no encontrado. Verificar el nombre del sistema.';
    RETURN;
  END IF;

  -- Insertar cabecera (factura) si no existe
  SELECT id INTO v_cabecera_id
  FROM cabecera
  WHERE id_sistema = v_sistema_id AND nombre = 'factura'
  LIMIT 1;

  IF v_cabecera_id IS NULL THEN
    INSERT INTO cabecera (id_sistema, nombre, descripcion, es_activo)
    VALUES (v_sistema_id, 'factura', 'Facturas de venta', true)
    RETURNING id INTO v_cabecera_id;
    RAISE NOTICE 'Cabecera "factura" creada con ID: %', v_cabecera_id;
  ELSE
    RAISE NOTICE 'Cabecera "factura" ya existia con ID: %', v_cabecera_id;
  END IF;

  -- item_factura
  IF NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cabecera_id AND nombre = 'item_factura') THEN
    INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
    VALUES (v_cabecera_id, 'item_factura', 'Items de factura', 'id_factura', true);
    RAISE NOTICE 'Detalle "item_factura" creado.';
  END IF;

  -- pagos_factura
  IF NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cabecera_id AND nombre = 'pagos_factura') THEN
    INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
    VALUES (v_cabecera_id, 'pagos_factura', 'Pagos de factura', 'id_factura', true);
    RAISE NOTICE 'Detalle "pagos_factura" creado.';
  END IF;

  RAISE NOTICE 'Configuracion completada. Sistema ID: %, Cabecera ID: %', v_sistema_id, v_cabecera_id;
END;
$$;
