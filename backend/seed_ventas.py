"""
Pobla ventas_db con esquema clásico y datos ficticios.
Usa DROP TABLE ... CASCADE para limpiar estructura previa.
También registra el sistema en app_db si no existe.

Uso:
    python seed_ventas.py
"""

import asyncio
import asyncpg
from decimal import Decimal

# ── Configuración ─────────────────────────────────────────────────────────────
VENTAS_DSN = "postgresql://app_user:superpassword@localhost:5432/ventas_db"
APPDB_DSN  = "postgresql://app_user:superpassword@localhost:5432/app_db"

# Primero mostramos qué tablas existen para diagnóstico
DDL_DROP = """
DROP TABLE IF EXISTS pagos_factura  CASCADE;
DROP TABLE IF EXISTS items_factura  CASCADE;
DROP TABLE IF EXISTS item_factura   CASCADE;
DROP TABLE IF EXISTS factura        CASCADE;
DROP TABLE IF EXISTS detalle_pedido CASCADE;
DROP TABLE IF EXISTS pedidos        CASCADE;
DROP TABLE IF EXISTS productos      CASCADE;
DROP TABLE IF EXISTS clientes       CASCADE;
DROP TABLE IF EXISTS categorias     CASCADE;
"""

DDL_CREATE = """
CREATE TABLE categorias (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    es_activo   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clientes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    email       VARCHAR(100) UNIQUE,
    telefono    VARCHAR(20),
    direccion   TEXT,
    ciudad      VARCHAR(80),
    es_activo   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE productos (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_categoria BIGINT REFERENCES categorias(id),
    nombre       VARCHAR(200) NOT NULL,
    descripcion  TEXT,
    precio       NUMERIC(10,2) NOT NULL,
    stock        INTEGER DEFAULT 0,
    sku          VARCHAR(50) UNIQUE,
    es_activo    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE pedidos (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente  BIGINT REFERENCES clientes(id),
    fecha       TIMESTAMP DEFAULT NOW(),
    estado      VARCHAR(30) DEFAULT 'pendiente',
    total       NUMERIC(10,2) DEFAULT 0,
    notas       TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE detalle_pedido (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pedido   BIGINT REFERENCES pedidos(id) ON DELETE CASCADE,
    id_producto BIGINT REFERENCES productos(id),
    cantidad    INTEGER NOT NULL,
    precio_unit NUMERIC(10,2) NOT NULL,
    subtotal    NUMERIC(10,2) GENERATED ALWAYS AS (cantidad * precio_unit) STORED
);

CREATE TABLE factura (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pedido        BIGINT REFERENCES pedidos(id),
    numero_factura   VARCHAR(20) UNIQUE NOT NULL,
    fecha_emision    TIMESTAMP DEFAULT NOW(),
    fecha_vencimiento TIMESTAMP,
    subtotal         NUMERIC(10,2) DEFAULT 0,
    impuesto         NUMERIC(10,2) DEFAULT 0,
    total            NUMERIC(10,2) DEFAULT 0,
    estado           VARCHAR(20) DEFAULT 'pendiente',
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE item_factura (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_factura  BIGINT REFERENCES factura(id) ON DELETE CASCADE,
    id_producto BIGINT REFERENCES productos(id),
    descripcion VARCHAR(255),
    cantidad    INTEGER NOT NULL,
    precio_unit NUMERIC(10,2) NOT NULL,
    subtotal    NUMERIC(10,2) GENERATED ALWAYS AS (cantidad * precio_unit) STORED
);

CREATE TABLE pagos_factura (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_factura   BIGINT REFERENCES factura(id) ON DELETE CASCADE,
    fecha_pago   TIMESTAMP DEFAULT NOW(),
    monto        NUMERIC(10,2) NOT NULL,
    metodo_pago  VARCHAR(50),
    referencia   VARCHAR(100),
    created_at   TIMESTAMP DEFAULT NOW()
);
"""

DATA_CATEGORIAS = [
    ("Electrónica",  "Dispositivos y accesorios electrónicos"),
    ("Ropa",         "Prendas de vestir para adultos y niños"),
    ("Hogar",        "Artículos para el hogar y decoración"),
    ("Alimentos",    "Productos alimenticios y bebidas"),
    ("Deportes",     "Equipos y ropa deportiva"),
]

DATA_CLIENTES = [
    ("Ana García",      "ana.garcia@email.com",  "8888-1111", "Av. Central 45",    "San José"),
    ("Luis Mora",       "luis.mora@email.com",   "8888-2222", "Calle 5 #12",       "Heredia"),
    ("María Rodríguez", "maria.rod@email.com",   "8888-3333", "Blvd. Norte 78",    "Alajuela"),
    ("Carlos Jiménez",  "carlos.j@email.com",    "8888-4444", "Urb. Los Pinos 3",  "Cartago"),
    ("Sofía López",     "sofia.lopez@email.com", "8888-5555", "Res. El Sol 22",    "Liberia"),
    ("Pedro Vargas",    "pedro.v@email.com",     "8888-6666", "Col. Las Flores 9", "San José"),
    ("Laura Salas",     "laura.salas@email.com", "8888-7777", "Av. Segunda 33",    "Heredia"),
    ("Diego Ureña",     "diego.u@email.com",     "8888-8888", "Calle 10 #6",       "Alajuela"),
    ("Valentina Cruz",  "vale.cruz@email.com",   "8888-9999", "Sector 4 Lote 18",  "San José"),
    ("Andrés Brenes",   "andres.b@email.com",    "8877-0000", "Cond. Vista Mar 1", "Puntarenas"),
]

# (idx_categoria 0-based, nombre, descripcion, precio, stock, sku)
DATA_PRODUCTOS = [
    (0, "Laptop Pro 15",      "Laptop Intel i7 16GB RAM",    899.99, 15, "ELEC-001"),
    (0, "Teclado Mecánico",   "Teclado RGB switches azules",  59.99, 50, "ELEC-002"),
    (0, "Monitor 27\" 4K",    "Monitor UHD IPS 144Hz",       349.99, 20, "ELEC-003"),
    (0, "Auriculares BT",     "Auriculares Bluetooth ANC",    79.99, 35, "ELEC-004"),
    (0, "Webcam HD 1080p",    "Webcam con micrófono",         45.99, 40, "ELEC-005"),
    (1, "Camiseta Algodón",   "Camiseta 100% algodón",        14.99,120, "ROPA-001"),
    (1, "Pantalón Denim",     "Jeans slim fit unisex",        39.99, 80, "ROPA-002"),
    (1, "Chaqueta Polar",     "Polar térmica talla M-XL",     54.99, 45, "ROPA-003"),
    (2, "Lámpara LED",        "Lámpara escritorio regulable", 29.99, 60, "HOGA-001"),
    (2, "Juego Sábanas",      "Sábanas 300 hilos queen",      49.99, 30, "HOGA-002"),
    (2, "Cafetera Eléctrica", "Cafetera programable 12 tazas",44.99, 25, "HOGA-003"),
    (3, "Café Molido 500g",   "Café arábiga tostado oscuro",   8.99,200, "ALIM-001"),
    (3, "Granola Premium",    "Granola artesanal sin azúcar", 12.99,150, "ALIM-002"),
    (3, "Jugo Natural 1L",    "Jugo de naranja natural",       3.99,300, "ALIM-003"),
    (4, "Colchoneta Yoga",    "Mat antideslizante 6mm",       24.99, 55, "DEPO-001"),
    (4, "Mancuernas 5kg par", "Mancuernas recubiertas goma",  34.99, 40, "DEPO-002"),
    (4, "Botella Deportiva",  "Botella 750ml acero inox",     18.99, 90, "DEPO-003"),
]

# (idx_cliente 0-based, estado, notas)
DATA_PEDIDOS = [
    (0, "entregado",  "Entrega en horario matutino"),
    (1, "enviado",    "Requiere firma al recibir"),
    (2, "procesando", None),
    (3, "entregado",  "Cliente frecuente"),
    (4, "pendiente",  "Pago contra entrega"),
    (5, "entregado",  None),
    (6, "enviado",    "Frágil, manejar con cuidado"),
    (7, "procesando", None),
    (8, "entregado",  "Pedido urgente"),
    (9, "pendiente",  None),
    (0, "enviado",    "Segunda compra del mes"),
    (2, "entregado",  None),
    (4, "cancelado",  "Cliente solicitó cancelación"),
    (1, "entregado",  None),
    (6, "procesando", "Verificar stock"),
]

# Pedidos que generan factura: (idx_pedido, numero_factura, estado_factura, dias_vencimiento)
# Solo pedidos entregados o enviados reciben factura
DATA_FACTURAS = [
    (0,  "FAC-2024-001", "pagada",   30),
    (1,  "FAC-2024-002", "pendiente", 30),
    (3,  "FAC-2024-003", "pagada",   30),
    (5,  "FAC-2024-004", "pagada",   30),
    (6,  "FAC-2024-005", "pendiente", 30),
    (8,  "FAC-2024-006", "pagada",   30),
    (10, "FAC-2024-007", "pendiente", 15),
    (11, "FAC-2024-008", "pagada",   30),
    (13, "FAC-2024-009", "pagada",   30),
]

# Métodos de pago disponibles
METODOS_PAGO = ["tarjeta_credito", "tarjeta_debito", "transferencia", "efectivo", "sinpe"]

# (idx_pedido 0-based, idx_producto 0-based, cantidad, precio_unit)
DATA_DETALLES = [
    (0,  0, 1, 899.99),
    (0,  1, 1,  59.99),
    (1,  2, 1, 349.99),
    (1,  3, 2,  79.99),
    (2,  5, 3,  14.99),
    (2,  6, 2,  39.99),
    (3,  4, 1,  45.99),
    (3, 14, 1,  24.99),
    (4, 11, 4,   8.99),
    (4, 12, 2,  12.99),
    (5, 10, 1,  44.99),
    (5,  8, 2,  29.99),
    (6,  7, 1,  54.99),
    (6, 15, 1,  34.99),
    (7,  0, 1, 899.99),
    (7, 16, 2,  18.99),
    (8, 13, 6,   3.99),
    (8, 11, 2,   8.99),
    (9,  2, 1, 349.99),
    (9,  1, 1,  59.99),
    (10,14, 2,  24.99),
    (10,16, 3,  18.99),
    (11, 5, 5,  14.99),
    (11, 6, 1,  39.99),
    (12, 9, 2,  49.99),
    (12,10, 1,  44.99),
    (13, 3, 1,  79.99),
    (13, 0, 2, 899.99),
    (14,15, 1,  34.99),
]


async def seed_ventas():
    print("Conectando a ventas_db...")
    conn = await asyncpg.connect(VENTAS_DSN)

    # Mostrar tablas existentes
    rows = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    if rows:
        print(f"  Tablas existentes: {[r['table_name'] for r in rows]}")
        print("  Eliminando tablas anteriores (DROP CASCADE)...")
    else:
        print("  BD vacía, creando desde cero...")

    await conn.execute(DDL_DROP)
    print("  Creando tablas nuevas...")
    await conn.execute(DDL_CREATE)

    # Categorías
    print("Insertando categorías...")
    cat_ids = []
    for nombre, desc in DATA_CATEGORIAS:
        r = await conn.fetchrow(
            "INSERT INTO categorias (nombre,descripcion) VALUES ($1,$2) RETURNING id",
            nombre, desc)
        cat_ids.append(r["id"])

    # Clientes
    print("Insertando clientes...")
    cli_ids = []
    for nombre, email, tel, dir_, ciudad in DATA_CLIENTES:
        r = await conn.fetchrow(
            "INSERT INTO clientes (nombre,email,telefono,direccion,ciudad) "
            "VALUES ($1,$2,$3,$4,$5) RETURNING id",
            nombre, email, tel, dir_, ciudad)
        cli_ids.append(r["id"])

    # Productos
    print("Insertando productos...")
    prod_ids = []
    for idx_cat, nombre, desc, precio, stock, sku in DATA_PRODUCTOS:
        r = await conn.fetchrow(
            "INSERT INTO productos (id_categoria,nombre,descripcion,precio,stock,sku) "
            "VALUES ($1,$2,$3,$4,$5,$6) RETURNING id",
            cat_ids[idx_cat], nombre, desc, precio, stock, sku)
        prod_ids.append(r["id"])

    # Pedidos
    print("Insertando pedidos...")
    ped_ids = []
    for idx_cli, estado, notas in DATA_PEDIDOS:
        r = await conn.fetchrow(
            "INSERT INTO pedidos (id_cliente,estado,notas) VALUES ($1,$2,$3) RETURNING id",
            cli_ids[idx_cli], estado, notas)
        ped_ids.append(r["id"])

    # Detalles
    print("Insertando detalles de pedido...")
    for idx_ped, idx_prod, cantidad, precio_unit in DATA_DETALLES:
        await conn.execute(
            "INSERT INTO detalle_pedido (id_pedido,id_producto,cantidad,precio_unit) "
            "VALUES ($1,$2,$3,$4)",
            ped_ids[idx_ped], prod_ids[idx_prod], cantidad, precio_unit)

    # Calcular totales de pedidos
    print("Calculando totales de pedidos...")
    await conn.execute("""
        UPDATE pedidos p
        SET total = (
            SELECT COALESCE(SUM(subtotal), 0)
            FROM detalle_pedido d WHERE d.id_pedido = p.id
        )
    """)

    # Facturas
    print("Insertando facturas...")
    fac_ids = {}  # idx_pedido -> factura_id
    for idx_ped, numero, estado, dias_venc in DATA_FACTURAS:
        r = await conn.fetchrow("""
            INSERT INTO factura
                (id_pedido, numero_factura, fecha_emision, fecha_vencimiento, estado)
            VALUES ($1, $2, NOW(), NOW() + ($3::int * interval '1 day'), $4)
            RETURNING id
        """, ped_ids[idx_ped], numero, dias_venc, estado)
        fac_ids[idx_ped] = r["id"]
    n_fac = await conn.fetchval("SELECT COUNT(*) FROM factura")
    print(f"  -> {n_fac} facturas insertadas, fac_ids keys={list(fac_ids.keys())}")

    # Items de factura
    print("Insertando items de factura...")
    n_items = 0
    for idx_ped, idx_prod, cantidad, precio_unit in DATA_DETALLES:
        if idx_ped not in fac_ids:
            continue
        prod_nombre = DATA_PRODUCTOS[idx_prod][1]
        await conn.execute("""
            INSERT INTO item_factura
                (id_factura, id_producto, descripcion, cantidad, precio_unit)
            VALUES ($1, $2, $3, $4, $5::numeric)
        """, fac_ids[idx_ped], prod_ids[idx_prod], prod_nombre,
             cantidad, Decimal(str(precio_unit)))
        n_items += 1
    n_items_db = await conn.fetchval("SELECT COUNT(*) FROM item_factura")
    print(f"  -> {n_items} items enviados, {n_items_db} en BD")

    # Calcular subtotal, impuesto (13%) y total en Python para evitar problemas de tipo
    print("Calculando totales de facturas...")
    for idx_ped, fac_id in fac_ids.items():
        subtotal = await conn.fetchval(
            "SELECT COALESCE(SUM(subtotal), 0) FROM item_factura WHERE id_factura=$1", fac_id)
        subtotal  = Decimal(str(subtotal))
        impuesto  = round(subtotal * Decimal("0.13"), 2)
        total     = subtotal + impuesto
        await conn.execute(
            "UPDATE factura SET subtotal=$1, impuesto=$2, total=$3 WHERE id=$4",
            subtotal, impuesto, total, fac_id)

    # Pagos (solo facturas con estado 'pagada')
    print("Insertando pagos...")
    metodos = METODOS_PAGO
    n_pagos = 0
    for i, (idx_ped, numero, estado, dias_venc) in enumerate(DATA_FACTURAS):
        if estado != "pagada":
            continue
        fac_id    = fac_ids[idx_ped]
        total_fac = await conn.fetchval("SELECT total FROM factura WHERE id=$1", fac_id)
        if total_fac is None:
            print(f"  AVISO: factura id={fac_id} tiene total=NULL, saltando pago")
            continue
        metodo    = metodos[i % len(metodos)]
        referencia = f"REF-{fac_id:04d}-{i+1:02d}"
        await conn.execute("""
            INSERT INTO pagos_factura (id_factura, monto, metodo_pago, referencia)
            VALUES ($1, $2, $3, $4)
        """, fac_id, Decimal(str(total_fac)), metodo, referencia)
        n_pagos += 1
    n_pagos_db = await conn.fetchval("SELECT COUNT(*) FROM pagos_factura")
    print(f"  -> {n_pagos} pagos enviados, {n_pagos_db} en BD")

    # Resumen
    print("\n=== ventas_db poblada ===")
    for tabla in ["categorias","clientes","productos","pedidos","detalle_pedido",
                  "factura","item_factura","pagos_factura"]:
        n = await conn.fetchval(f"SELECT COUNT(*) FROM {tabla}")
        print(f"  {tabla:<20s}: {n} registros")

    await conn.close()


async def register_sistema():
    print("\nRegistrando sistema en app_db...")
    conn = await asyncpg.connect(APPDB_DSN)

    existing = await conn.fetchrow(
        "SELECT id FROM sistema WHERE nombre_bd = 'ventas_db'")

    if existing:
        await conn.execute("""
            UPDATE sistema SET
                nombre          = 'Ventas DB',
                descripcion     = 'BD de ventas: clientes, productos, pedidos',
                host_bd         = 'localhost',
                puerto_bd       = 5432,
                nombre_bd       = 'ventas_db',
                usuario_bd      = 'app_user',
                "contraseña_bd" = 'superpassword',
                es_activo       = true,
                updated_at      = NOW()
            WHERE nombre_bd = 'ventas_db'
        """)
        sid = existing["id"]
        print(f"  Sistema actualizado (id={sid})")
    else:
        r = await conn.fetchrow("""
            INSERT INTO sistema
                (nombre, descripcion, host_bd, puerto_bd, nombre_bd,
                 usuario_bd, "contraseña_bd", es_activo, created_at, updated_at)
            VALUES
                ('Ventas DB','BD de ventas: clientes, productos, pedidos',
                 'localhost', 5432, 'ventas_db',
                 'app_user', 'superpassword', true, NOW(), NOW())
            RETURNING id
        """)
        sid = r["id"]
        print(f"  Sistema creado (id={sid})")

    await conn.close()
    return sid


async def main():
    await seed_ventas()
    sid = await register_sistema()
    print(f"\nListo. Selecciona 'Ventas DB' en el tester y presiona el boton diccionario (id={sid}).")


asyncio.run(main())
