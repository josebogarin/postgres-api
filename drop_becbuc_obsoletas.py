# -*- coding: utf-8 -*-
"""
drop_becbuc_obsoletas.py — Limpieza de la base 'becbuc': elimina el esquema viejo
del prototipo (tablas 0 filas + vistas no usadas). NO toca app_db.

Seguridad: hace los DROP dentro de UNA transaccion, verifica que las vistas
ACTIVAS (v_copamundial_puntajes/_det) sigan existiendo; si no, hace ROLLBACK.
Correr SIEMPRE con backup fresco previo (lo hace el .bat).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools.db_env import becbuc_conn  # noqa: E402

VIEWS_DROP = [
    "v_auditoria_pronosticos", "v_auditoria_puntajes", "v_calendario",
    "v_dim_equipo", "v_dim_fase", "v_dim_partido", "v_dim_torneo",
    "v_hechos_apuestas", "v_mejores_terceros", "v_ranking_torneo",
    "v_resumen_partido", "v_standings_grupos",
]
TABLES_DROP = [
    "usuarios", "miembros_competencia", "apuestas", "apuestas_bonus",
    "instantanea_auditoria", "ranking", "posiciones_grupo", "eventos_partido",
    "debug_excel_import", "auditoria_pdf", "apostador_bonus",
]
KEEP_VIEWS = ["v_copamundial_puntajes", "v_copamundial_puntajes_det"]


def _counts(cur):
    cur.execute("""SELECT
        (SELECT count(*) FROM information_schema.tables
           WHERE table_schema='public' AND table_type='BASE TABLE'),
        (SELECT count(*) FROM information_schema.views WHERE table_schema='public')""")
    return cur.fetchone()


def main():
    conn = becbuc_conn()
    conn.autocommit = False
    cur = conn.cursor()

    t0, v0 = _counts(cur)
    print(f"ANTES: {t0} tablas, {v0} vistas")

    for v in VIEWS_DROP:
        cur.execute(f'DROP VIEW IF EXISTS "{v}" CASCADE')
    for t in TABLES_DROP:
        cur.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')

    # Verificar (dentro de la misma tx) que las vistas activas siguen
    cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema='public'")
    remaining_views = {r[0] for r in cur.fetchall()}
    missing = [v for v in KEEP_VIEWS if v not in remaining_views]
    if missing:
        conn.rollback()
        print(f"*** ABORTADO (rollback): se hubieran perdido vistas activas: {missing}")
        cur.close(); conn.close(); sys.exit(1)

    conn.commit()
    t1, v1 = _counts(cur)
    print(f"DESPUES: {t1} tablas, {v1} vistas  (borradas: {t0-t1} tablas, {v0-v1} vistas)")

    # Listado final
    cur.execute("""SELECT table_name FROM information_schema.tables
                   WHERE table_schema='public' AND table_type='BASE TABLE'
                   ORDER BY table_name""")
    print("Tablas restantes:", ", ".join(r[0] for r in cur.fetchall()))
    cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema='public' ORDER BY table_name")
    print("Vistas restantes:", ", ".join(r[0] for r in cur.fetchall()))
    print("OK limpieza aplicada.")

    cur.close(); conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("ERROR:", e); traceback.print_exc(); sys.exit(1)
