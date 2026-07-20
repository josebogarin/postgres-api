-- =============================================================================
-- COMENTARIOS DE TABLAS Y COLUMNAS — app_db
-- Ejecutar: Get-Content "comentarios_app_db.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- =============================================================================

-- ── users ────────────────────────────────────────────────────────────────────
COMMENT ON TABLE users IS 'Usuarios del sistema. Autenticación vía JWT con bcrypt.';
COMMENT ON COLUMN users.id            IS 'Identificador único (bigint autoincrement)';
COMMENT ON COLUMN users.username      IS 'Nombre de usuario único, usado para login';
COMMENT ON COLUMN users.email         IS 'Correo electrónico único';
COMMENT ON COLUMN users.password_hash IS 'Hash bcrypt de la contraseña (passlib)';
COMMENT ON COLUMN users.is_active     IS 'Indica si el usuario está activo y puede iniciar sesión';
COMMENT ON COLUMN users.created_at    IS 'Fecha y hora de creación del usuario';

-- ── roles ─────────────────────────────────────────────────────────────────────
COMMENT ON TABLE roles IS 'Roles del sistema. Pre-sembrados: superadmin, admin, operator, viewer.';
COMMENT ON COLUMN roles.id          IS 'Identificador único';
COMMENT ON COLUMN roles.name        IS 'Nombre del rol (único). Ej: superadmin, admin';
COMMENT ON COLUMN roles.description IS 'Descripción del rol y sus capacidades';

-- ── permissions ───────────────────────────────────────────────────────────────
COMMENT ON TABLE permissions IS 'Permisos granulares del sistema. Ej: user:create, sistema:manage.';
COMMENT ON COLUMN permissions.id          IS 'Identificador único';
COMMENT ON COLUMN permissions.name        IS 'Clave del permiso. Formato recurso:acción (ej: user:read)';
COMMENT ON COLUMN permissions.description IS 'Descripción de lo que permite este permiso';

-- ── sistema ───────────────────────────────────────────────────────────────────
COMMENT ON TABLE sistema IS 'Sistemas externos registrados con sus conexiones de base de datos PostgreSQL.';
COMMENT ON COLUMN sistema.id              IS 'Identificador único (bigint)';
COMMENT ON COLUMN sistema.nombre          IS 'Nombre visible del sistema';
COMMENT ON COLUMN sistema.descripcion     IS 'Descripción opcional del sistema';
COMMENT ON COLUMN sistema.host_bd         IS 'Host del servidor PostgreSQL externo';
COMMENT ON COLUMN sistema.puerto_bd       IS 'Puerto del servidor PostgreSQL (default 5432)';
COMMENT ON COLUMN sistema.nombre_bd       IS 'Nombre de la base de datos. Se usa como slug en la API (db_slug)';
COMMENT ON COLUMN sistema.usuario_bd      IS 'Usuario de conexión a la base de datos externa';
COMMENT ON COLUMN sistema."contraseña_bd" IS 'Contraseña de conexión a la base de datos externa';
COMMENT ON COLUMN sistema.es_activo       IS 'Indica si el sistema está activo y visible para los usuarios';
COMMENT ON COLUMN sistema.created_at      IS 'Fecha de creación del registro';
COMMENT ON COLUMN sistema.updated_at      IS 'Fecha de última actualización';

-- ── cabecera ──────────────────────────────────────────────────────────────────
COMMENT ON TABLE cabecera IS 'Grupos o categorías de configuración asociadas a un sistema.';
COMMENT ON COLUMN cabecera.id          IS 'Identificador único';
COMMENT ON COLUMN cabecera.id_sistema  IS 'FK al sistema al que pertenece la cabecera';
COMMENT ON COLUMN cabecera.nombre      IS 'Nombre de la cabecera';
COMMENT ON COLUMN cabecera.descripcion IS 'Descripción opcional';
COMMENT ON COLUMN cabecera.es_activo   IS 'Indica si la cabecera está activa';
COMMENT ON COLUMN cabecera.created_at  IS 'Fecha de creación';
COMMENT ON COLUMN cabecera.updated_at  IS 'Fecha de última actualización';

-- ── detalle ───────────────────────────────────────────────────────────────────
COMMENT ON TABLE detalle IS 'Ítems o detalles dentro de una cabecera. Se eliminan en cascada.';
COMMENT ON COLUMN detalle.id          IS 'Identificador único';
COMMENT ON COLUMN detalle.id_cabecera IS 'FK a la cabecera padre (ON DELETE CASCADE)';
COMMENT ON COLUMN detalle.nombre      IS 'Nombre del detalle';
COMMENT ON COLUMN detalle.descripcion IS 'Descripción opcional';
COMMENT ON COLUMN detalle.es_activo   IS 'Indica si el detalle está activo';
COMMENT ON COLUMN detalle.created_at  IS 'Fecha de creación';
COMMENT ON COLUMN detalle.updated_at  IS 'Fecha de última actualización';

-- ── diccionario ───────────────────────────────────────────────────────────────
COMMENT ON TABLE diccionario IS 'Metadatos de campos/columnas por sistema. Guía la UI del CRUD genérico.';
COMMENT ON COLUMN diccionario.id              IS 'Identificador único';
COMMENT ON COLUMN diccionario.id_sistema      IS 'FK al sistema (SET NULL si se elimina el sistema)';
COMMENT ON COLUMN diccionario.campo           IS 'Nombre del campo/columna en la base de datos';
COMMENT ON COLUMN diccionario.alias           IS 'Etiqueta amigable para mostrar en la interfaz de usuario';
COMMENT ON COLUMN diccionario.descripcion     IS 'Descripción del propósito del campo';
COMMENT ON COLUMN diccionario.tipo_dato       IS 'Tipo de dato PostgreSQL (varchar, int, boolean, numeric, etc.)';
COMMENT ON COLUMN diccionario.es_visible      IS 'Si es false, el campo no se muestra en la tabla CRUD';
COMMENT ON COLUMN diccionario.es_solo_lectura IS 'Si es true, el campo no se puede editar desde la UI';
COMMENT ON COLUMN diccionario.es_obligatorio  IS 'Si es true, el campo es requerido al crear/editar';
COMMENT ON COLUMN diccionario.orden_campo     IS 'Posición del campo en la tabla y formulario (menor = primero)';
COMMENT ON COLUMN diccionario.decimales       IS 'Cantidad de decimales para campos numéricos';
COMMENT ON COLUMN diccionario.texto_ayuda     IS 'Tooltip o texto de ayuda que se muestra junto al campo';
COMMENT ON COLUMN diccionario.valor_defecto   IS 'Valor predeterminado al crear un nuevo registro';
COMMENT ON COLUMN diccionario.multivalor      IS 'Opciones para campos tipo select. Formato: val|label;val2|label2 o SELECT SQL';
COMMENT ON COLUMN diccionario.crear_en        IS 'Fecha de creación del registro en el diccionario';
COMMENT ON COLUMN diccionario.actualizar_en   IS 'Fecha de última actualización del registro';

-- ── audit_logs ────────────────────────────────────────────────────────────────
COMMENT ON TABLE audit_logs IS 'Registro de auditoría automático de todas las acciones sobre la API.';
COMMENT ON COLUMN audit_logs.id          IS 'Identificador único (bigint autoincrement, no UUID)';
COMMENT ON COLUMN audit_logs.user_id     IS 'ID del usuario que realizó la acción (nullable)';
COMMENT ON COLUMN audit_logs.user_email  IS 'Email del usuario al momento de la acción';
COMMENT ON COLUMN audit_logs.action      IS 'Acción realizada: CREATE, READ, UPDATE, DELETE';
COMMENT ON COLUMN audit_logs.resource    IS 'Nombre del recurso afectado (tabla o endpoint)';
COMMENT ON COLUMN audit_logs.resource_id IS 'ID del recurso específico afectado';
COMMENT ON COLUMN audit_logs.method      IS 'Método HTTP: GET, POST, PATCH, DELETE';
COMMENT ON COLUMN audit_logs.path        IS 'Ruta completa del endpoint invocado';
COMMENT ON COLUMN audit_logs.status_code IS 'Código de respuesta HTTP devuelto';
COMMENT ON COLUMN audit_logs.ip_address  IS 'Dirección IP del cliente que realizó la solicitud';
COMMENT ON COLUMN audit_logs.details     IS 'Información adicional en formato JSONB';
COMMENT ON COLUMN audit_logs.created_at  IS 'Timestamp del evento (con zona horaria)';

-- ── user_roles ────────────────────────────────────────────────────────────────
COMMENT ON TABLE user_roles IS 'Asociación muchos-a-muchos entre usuarios y roles.';
COMMENT ON COLUMN user_roles.user_id IS 'FK al usuario';
COMMENT ON COLUMN user_roles.role_id IS 'FK al rol';

-- ── user_role_permissions ─────────────────────────────────────────────────────
COMMENT ON TABLE user_role_permissions IS 'Permisos asignados a cada rol (muchos-a-muchos).';
COMMENT ON COLUMN user_role_permissions.role_id        IS 'FK al rol';
COMMENT ON COLUMN user_role_permissions.permission_id  IS 'FK al permiso';

-- ── user_permissions ──────────────────────────────────────────────────────────
COMMENT ON TABLE user_permissions IS 'Permisos directos asignados a usuarios, independientes de su rol.';
COMMENT ON COLUMN user_permissions.user_id        IS 'FK al usuario';
COMMENT ON COLUMN user_permissions.permission_id  IS 'FK al permiso';

-- ── user_sistemas ─────────────────────────────────────────────────────────────
COMMENT ON TABLE user_sistemas IS 'Sistemas autorizados por usuario. Controla el acceso multi-sistema.';
COMMENT ON COLUMN user_sistemas.user_id    IS 'FK al usuario';
COMMENT ON COLUMN user_sistemas.sistema_id IS 'FK al sistema autorizado para ese usuario';

-- ── portal_kpis ───────────────────────────────────────────────────────────────
COMMENT ON TABLE portal_kpis IS 'KPIs configurables del portal. Cada uno ejecuta una query SQL para obtener su valor.';
COMMENT ON COLUMN portal_kpis.id         IS 'Identificador único';
COMMENT ON COLUMN portal_kpis.id_sistema IS 'FK al sistema al que pertenece el KPI';
COMMENT ON COLUMN portal_kpis.titulo     IS 'Título visible en el card del KPI';
COMMENT ON COLUMN portal_kpis.query_sql  IS 'Consulta SQL SELECT que devuelve un único valor numérico';
COMMENT ON COLUMN portal_kpis.formato    IS 'Formato: number (default), currency, percent';
COMMENT ON COLUMN portal_kpis.decimales  IS 'Cantidad de decimales a mostrar en el valor';
COMMENT ON COLUMN portal_kpis.prefijo    IS 'Texto antes del valor (ej: $, USD)';
COMMENT ON COLUMN portal_kpis.sufijo     IS 'Texto después del valor (ej: %, unidades)';
COMMENT ON COLUMN portal_kpis.icono      IS 'Nombre del ícono Tabler Icons (ej: chart-bar)';
COMMENT ON COLUMN portal_kpis.color      IS 'Color del borde izquierdo del card en formato hex';
COMMENT ON COLUMN portal_kpis.orden      IS 'Posición en la grilla del portal (menor = primero)';
COMMENT ON COLUMN portal_kpis.es_activo  IS 'Indica si el KPI está activo y visible';
COMMENT ON COLUMN portal_kpis.created_at IS 'Fecha de creación';
COMMENT ON COLUMN portal_kpis.updated_at IS 'Fecha de última actualización';

-- ── portal_vinculos ───────────────────────────────────────────────────────────
COMMENT ON TABLE portal_vinculos IS 'Accesos rápidos configurables del portal por sistema.';
COMMENT ON COLUMN portal_vinculos.id          IS 'Identificador único';
COMMENT ON COLUMN portal_vinculos.id_sistema  IS 'FK al sistema al que pertenece el vínculo';
COMMENT ON COLUMN portal_vinculos.titulo      IS 'Título visible del acceso rápido';
COMMENT ON COLUMN portal_vinculos.url         IS 'URL de destino al hacer clic';
COMMENT ON COLUMN portal_vinculos.icono       IS 'Ícono Tabler Icons';
COMMENT ON COLUMN portal_vinculos.descripcion IS 'Descripción corta que aparece debajo del título';
COMMENT ON COLUMN portal_vinculos.orden       IS 'Posición en la lista (menor = primero)';
COMMENT ON COLUMN portal_vinculos.es_activo   IS 'Indica si el vínculo está activo y visible';
COMMENT ON COLUMN portal_vinculos.created_at  IS 'Fecha de creación';
COMMENT ON COLUMN portal_vinculos.updated_at  IS 'Fecha de última actualización';
