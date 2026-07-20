# -*- coding: utf-8 -*-
"""
fix_sistema_columns.py
Restaura las columnas de conexion en app_db.sistema que la modernizacion del core
elimino. El modelo ORM Sistema (selectinload(User.sistemas) en cada carga de usuario)
las exige -> sin ellas uvicorn no arranca (UndefinedColumnError: sistema.host_bd).

ADD COLUMN IF NOT EXISTS = idempotente, no toca filas existentes.
Salida: fix_sistema_columns.txt
"""
import sys, os

try:
    import psycopg2
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet')
    import psycopg2

CONN_APP = "host=localhost port=5432 dbname=app_db user=app_user password=superpassword"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_sistema_columns.txt")

# (columna, DDL de tipo + default)  — coincide EXACTO con app/models/sistema.py + TimestampMixin
ALTERS = [
    ("host_bd",        'VARCHAR(255) NOT NULL DEFAULT \'localhost\''),
    ("puerto_bd",      'INTEGER NOT NULL DEFAULT 5432'),
    ("nombre_bd",      'VARCHAR(100) NOT NULL DEFAULT \'becbuc\''),
    ("usuario_bd",     'VARCHAR(100) NOT NULL DEFAULT \'app_user\''),
    ('"contraseña_bd"', 'VARCHAR(255) NOT NULL DEFAULT \'\''),
    ("es_activo",      'BOOLEAN NOT NULL DEFAULT TRUE'),
    ("created_at",     'TIMESTAMP NOT NULL DEFAULT now()'),
    ("updated_at",     'TIMESTAMP NOT NULL DEFAULT now()'),
]

lines = []
def log(s=""):
    print(s); lines.append(str(s))

try:
    conn = psycopg2.connect(CONN_APP)
    conn.autocommit = True
except Exception as e:
    log(f"ERROR conexion app_db: {e}")
    log("Docker corriendo? -> docker start core-postgres")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    sys.exit(1)

cur = conn.cursor()
log("Aplicando ALTER TABLE sistema ADD COLUMN IF NOT EXISTS ...")
for col, ddl in ALTERS:
    sql = f"ALTER TABLE sistema ADD COLUMN IF NOT EXISTS {col} {ddl};"
    try:
        cur.execute(sql)
        log(f"  OK  {col}")
    except Exception as e:
        log(f"  ERR {col}: {e}")

# Verificar esquema final
log("\nColumnas actuales de sistema:")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name='sistema' ORDER BY ordinal_position
""")
for r in cur.fetchall():
    log(f"  {r[0]:<28} {r[1]:<18} null={r[2]}")

conn.close()
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
log("\nListo. Reinicia uvicorn.")
