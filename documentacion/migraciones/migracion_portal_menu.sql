-- ============================================================
-- Tabla: portal_menu
-- Ítems de menú dinámico por sistema para el portal
-- ============================================================

CREATE TABLE IF NOT EXISTS portal_menu (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sistema  bigint NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
    titulo      varchar(255) NOT NULL,
    orden       integer NOT NULL DEFAULT 0,
    descripcion text,
    tabla       varchar(255),   -- nombre de tabla/vista a abrir (usa /tabla o /cabecera)
    url         varchar(500),   -- URL de página web secundaria (si no es tabla)
    icono       varchar(100) NOT NULL DEFAULT 'ti-table',
    es_activo   boolean NOT NULL DEFAULT true,
    created_at  timestamp NOT NULL DEFAULT now(),
    updated_at  timestamp NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portal_menu_sistema ON portal_menu(id_sistema);
CREATE INDEX IF NOT EXISTS idx_portal_menu_orden   ON portal_menu(id_sistema, orden);

COMMENT ON TABLE  portal_menu                IS 'Ítems de menú dinámico del portal, por sistema';
COMMENT ON COLUMN portal_menu.tabla          IS 'Nombre de tabla/vista a abrir en /tabla o /cabecera';
COMMENT ON COLUMN portal_menu.url            IS 'URL de página web secundaria (alternativa a tabla)';
COMMENT ON COLUMN portal_menu.icono          IS 'Clase de ícono Tabler (ej: ti-table, ti-chart-bar)';
