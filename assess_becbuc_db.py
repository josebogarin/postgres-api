# -*- coding: utf-8 -*-
"""
assess_becbuc_db.py — INVENTARIO SOLO LECTURA de la base 'becbuc'.
Lista tablas (con filas + tamano), vistas, secuencias y tipos. NO modifica nada.
NO toca app_db. Usa tools/db_env.py (credenciales desde .env, portable).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools.db_env import becbuc_conn  # noqa: E402


def main():
    conn = becbuc_conn()
    cur = conn.cursor()

    # ── Tablas base ────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT c.relname, pg_total_relation_size(c.oid) AS bytes
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY c.relname
    """)
    tablas = cur.fetchall()

    print("=" * 70)
    print(" INVENTARIO BASE 'becbuc' (solo lectura)")
    print("=" * 70)
    print(f"\n=== TABLAS ({len(tablas)}) ===")
    print(f"  {'tabla':32} {'filas':>10} {'tamano':>10}")
    total_bytes = 0
    for name, b in tablas:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{name}"')
            n = cur.fetchone()[0]
        except Exception as e:
            n = f"ERR({e})"
        total_bytes += b or 0
        kb = (b or 0) / 1024
        print(f"  {name:32} {str(n):>10} {kb:>8.0f} KB")
    print(f"  {'TOTAL':32} {'':>10} {total_bytes/1024/1024:>8.1f} MB")

    # ── Vistas ─────────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT table_name FROM information_schema.views
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    vistas = [r[0] for r in cur.fetchall()]
    print(f"\n=== VISTAS ({len(vistas)}) ===")
    for v in vistas:
        print("  ", v)

    # ── Secuencias ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S' ORDER BY c.relname
    """)
    seqs = [r[0] for r in cur.fetchall()]
    print(f"\n=== SECUENCIAS ({len(seqs)}) ===")
    print("  " + ", ".join(seqs))

    # ── Foreign keys entre tablas (para no dropear algo referenciado) ──────────
    cur.execute("""
        SELECT conrelid::regclass::text AS tabla, confrelid::regclass::text AS referencia
        FROM pg_constraint WHERE contype = 'f'
        ORDER BY 1
    """)
    fks = cur.fetchall()
    print(f"\n=== FOREIGN KEYS ({len(fks)}) ===")
    for t, ref in fks:
        print(f"  {t}  ->  {ref}")

    # ── Columnas por tabla (para cruce con el codigo) ─────────────────────────
    print(f"\n=== COLUMNAS POR TABLA ===")
    for name, _ in tablas:
        cur.execute("""
            SELECT column_name, data_type,
                   is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (name,))
        cols = cur.fetchall()
        print(f"\n  [{name}]  ({len(cols)} columnas)")
        for cn, dt, nul, dflt in cols:
            d = f" default={dflt}" if dflt else ""
            print(f"    - {cn:32} {dt:18} {'NULL' if nul == 'YES' else 'NOT NULL'}{d}")

    cur.close(); conn.close()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("ERROR:", e); traceback.print_exc()
