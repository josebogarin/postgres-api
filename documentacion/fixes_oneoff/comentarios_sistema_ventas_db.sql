-- ============================================================
-- COMENTARIOS DE COLUMNAS — Ventas DB (ventas_db)
-- Generado por genera_comentarios_sistemas.py
-- ============================================================

-- categorias
COMMENT ON COLUMN "categorias"."nombre" IS 'Categoria';
COMMENT ON COLUMN "categorias"."descripcion" IS 'Detalle';
COMMENT ON COLUMN "categorias"."es_activo" IS 'Activar';
COMMENT ON COLUMN "categorias"."created_at" IS 'Creado en';

-- clientes
COMMENT ON COLUMN "clientes"."nombre" IS 'Categoria';
COMMENT ON COLUMN "clientes"."es_activo" IS 'Activar';
COMMENT ON COLUMN "clientes"."created_at" IS 'Creado en';

-- detalle_pedido
COMMENT ON COLUMN "detalle_pedido"."id_pedido" IS 'Pedido';
COMMENT ON COLUMN "detalle_pedido"."precio_unit" IS 'Unitario (Gs)';
COMMENT ON COLUMN "detalle_pedido"."subtotal" IS 'Subtotal GS — Monto total del servicio';

-- factura
COMMENT ON COLUMN "factura"."id_pedido" IS 'Pedido';
COMMENT ON COLUMN "factura"."numero_factura" IS 'Factura';
COMMENT ON COLUMN "factura"."fecha_emision" IS 'Fecha';
COMMENT ON COLUMN "factura"."fecha_vencimiento" IS 'Vence en';
COMMENT ON COLUMN "factura"."subtotal" IS 'Subtotal GS — Monto total del servicio';
COMMENT ON COLUMN "factura"."impuesto" IS 'Iva — IVA 13% sobre el total';
COMMENT ON COLUMN "factura"."total" IS 'Total (Gs)';
COMMENT ON COLUMN "factura"."estado" IS 'Estado actual';
COMMENT ON COLUMN "factura"."created_at" IS 'Creado en';

-- item_factura
COMMENT ON COLUMN "item_factura"."id_factura" IS 'Factura';
COMMENT ON COLUMN "item_factura"."descripcion" IS 'Detalle';
COMMENT ON COLUMN "item_factura"."precio_unit" IS 'Unitario (Gs)';
COMMENT ON COLUMN "item_factura"."subtotal" IS 'Subtotal GS — Monto total del servicio';

-- pagos_factura
COMMENT ON COLUMN "pagos_factura"."id_factura" IS 'Factura';
COMMENT ON COLUMN "pagos_factura"."fecha_pago" IS 'Fecha Pago';
COMMENT ON COLUMN "pagos_factura"."monto" IS 'Total (Gs)';
COMMENT ON COLUMN "pagos_factura"."metodo_pago" IS 'Metodo';
COMMENT ON COLUMN "pagos_factura"."referencia" IS 'Referencia';
COMMENT ON COLUMN "pagos_factura"."created_at" IS 'Creado en';

-- pedidos
COMMENT ON COLUMN "pedidos"."id_cliente" IS 'Cliente';
COMMENT ON COLUMN "pedidos"."fecha" IS 'Fecha pedido';
COMMENT ON COLUMN "pedidos"."estado" IS 'Estado actual';
COMMENT ON COLUMN "pedidos"."total" IS 'Total (Gs)';
COMMENT ON COLUMN "pedidos"."notas" IS 'Obs';
COMMENT ON COLUMN "pedidos"."created_at" IS 'Creado en';

-- productos
COMMENT ON COLUMN "productos"."nombre" IS 'Categoria';
COMMENT ON COLUMN "productos"."descripcion" IS 'Detalle';
COMMENT ON COLUMN "productos"."es_activo" IS 'Activar';
COMMENT ON COLUMN "productos"."created_at" IS 'Creado en';
