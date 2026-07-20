# genera_comentarios_sistemas.py
# Lee el diccionario de app_db y genera un SQL de COMMENT ON COLUMN
# por cada sistema externo configurado.
# Ejecutar: python genera_comentarios_sistemas.py

import asyncio
import os
import sys
from pathlib import Path

# Agregar el backend al path para usar la config
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncpg

# ── Configuración de conexión a app_db ────────────────────────────────────────
APP_DB = {
    "host":     "localhost",
    "port":     5432,
    "database": "app_db",
    "user":     "app_user",
    "password": "superpassword",
}

OUT_DIR = Path(__file__).parent  # mismo directorio que este script


async def main():
    print("Conectando a app_db...")
    app_conn = await asyncpg.connect(**APP_DB)

    # Leer todos los sistemas activos
    sistemas = await app_conn.fetch("""
        SELECT id, nombre, nombre_bd, host_bd, puerto_bd, usuario_bd, "contraseña_bd"
        FROM sistema
        WHERE es_activo = true
        ORDER BY nombre
    """)

    if not sistemas:
        print("No hay sistemas activos en app_db.")
        await app_conn.close()
        return

    for sis in sistemas:
        sid        = sis["id"]
        nombre     = sis["nombre"]
        nombre_bd  = sis["nombre_bd"]
        host_bd    = sis["host_bd"]
        puerto_bd  = sis["puerto_bd"]
        usuario_bd = sis["usuario_bd"]
        password   = sis["contraseña_bd"]

        print(f"\n{'='*60}")
        print(f"Sistema: {nombre}  (DB: {nombre_bd})")

        # Leer diccionario para este sistema
        dic_rows = await app_conn.fetch("""
            SELECT campo, alias, descripcion
            FROM diccionario
            WHERE id_sistema = $1
              AND (alias IS NOT NULL OR descripcion IS NOT NULL)
            ORDER BY campo
        """, sid)

        if not dic_rows:
            print(f"  Sin entradas en diccionario — omitiendo.")
            continue

        # Construir mapa campo -> comentario
        campo_map = {}
        for row in dic_rows:
            campo = row["campo"]
            alias = (row["alias"] or "").strip()
            desc  = (row["descripcion"] or "").strip()
            if alias and desc:
                comentario = f"{alias} — {desc}"
            elif alias:
                comentario = alias
            else:
                comentario = desc
            campo_map[campo] = comentario

        # Conectar a la BD del sistema para leer sus tablas y columnas
        try:
            ext_conn = await asyncpg.connect(
                host=host_bd,
                port=puerto_bd,
                database=nombre_bd,
                user=usuario_bd,
                password=password,
            )
        except Exception as e:
            print(f"  ERROR al conectar: {e}")
            continue

        # Leer tablas y columnas del schema public
        cols = await ext_conn.fetch("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """)
        await ext_conn.close()

        if not cols:
            print(f"  Sin columnas en information_schema — omitiendo.")
            continue

        # Agrupar columnas por tabla
        tablas = {}
        for col in cols:
            t = col["table_name"]
            c = col["column_name"]
            tablas.setdefault(t, []).append(c)

        # Generar SQL
        lines = [
            f"-- ============================================================",
            f"-- COMENTARIOS DE COLUMNAS — {nombre} ({nombre_bd})",
            f"-- Generado por genera_comentarios_sistemas.py",
            f"-- ============================================================",
            "",
        ]

        matched = 0
        for tabla, columnas in sorted(tablas.items()):
            col_comments = []
            for col in columnas:
                if col in campo_map:
                    comentario = campo_map[col].replace("'", "''")  # escapar comillas
                    col_comments.append(
                        f'COMMENT ON COLUMN "{tabla}"."{col}" IS \'{comentario}\';'
                    )
                    matched += 1
            if col_comments:
                lines.append(f"-- {tabla}")
                lines.extend(col_comments)
                lines.append("")

        out_file = OUT_DIR / f"comentarios_sistema_{nombre_bd}.sql"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  {matched} comentario(s) generado(s) → {out_file.name}")

    await app_conn.close()
    print("\nListo.")


if __name__ == "__main__":
    asyncio.run(main())
