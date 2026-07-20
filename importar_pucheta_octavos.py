#!/usr/bin/env python3
"""
importar_pucheta_octavos.py
Importa las apuestas de PUCHETA para R16 (octavos de final, P089-P096).

EJECUTAR:
    cd "C:\proyecto FAST API"
    backend\.venv\Scripts\python.exe importar_pucheta_octavos.py

O doble clic en: importar_pucheta_octavos.bat
"""

import sys, os, asyncio

# Agregar backend al path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'backend'))

# ── Datos extraídos del Excel (P089-P096) ────────────────────────────────────
APUESTAS_PUCHETA = [
    # num_fifa, pred_local, pred_visitante, pred_j, pred_k, pred_l, pred_m, pred_n, tanda_l, tanda_v, clasifica_nombre
    (89,  1, 1, 3, 0, 1, 1, 39, 5, 3, 'PARAGUAY'),
    (90,  1, 2, 2, 0, 1, 1,  0, 4, 4, None),
    (91,  2, 1, 2, 0, 2, 1, 16, 5, 4, None),
    (92,  2, 2, 3, 0, 2, 1, 22, 3, 5, 'INGLATERRA'),
    (93,  2, 3, 2, 0, 2, 1, 17, 5, 4, None),
    (94,  1, 3, 3, 1, 1, 1, 28, 4, 5, None),
    (95,  2, 1, 3, 1, 1, 1, 19, 5, 3, None),
    (96,  2, 2, 2, 1, 1, 1, 35, 4, 5, None),
]

# ── Mapeo de nombres de equipo → buscar equipo_id en BD ──────────────────────
NOMBRE_MAP = {
    'PARAGUAY':   ['Paraguay', 'PARAGUAY'],
    'MARRUECOS':  ['Morocco', 'Marruecos', 'MARRUECOS'],
    'NORUEGA':    ['Norway',  'Noruega',   'NORUEGA'],
    'INGLATERRA': ['England', 'Inglaterra','INGLATERRA'],
    'ESPAÑA':     ['Spain',   'España',    'ESPANA', 'ESPAÑA'],
    'BELGICA':    ['Belgium', 'Belgica',   'BÉLGICA', 'BELGICA'],
    'EGIPTO':     ['Egypt',   'Egipto',    'EGIPTO'],
    'COLOMBIA':   ['Colombia','COLOMBIA'],
}


async def main():
    try:
        import asyncpg
    except ImportError:
        print("❌ asyncpg no instalado. Instalando...")
        os.system(f'"{sys.executable}" -m pip install asyncpg --quiet')
        import asyncpg

    # ── Conectar a PostgreSQL ──────────────────────────────────────────────────
    PG_BECBUC = 'postgresql://app_user:app_password@localhost:5432/becbuc'
    PG_APP_DB = 'postgresql://app_user:app_password@localhost:5432/app_db'

    print("Conectando a PostgreSQL...")
    try:
        conn_b = await asyncpg.connect(PG_BECBUC)
        conn_a = await asyncpg.connect(PG_APP_DB)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("   Verificar que Docker esté corriendo: docker ps")
        return

    try:
        # ── Buscar PUCHETA en app_db ───────────────────────────────────────────
        rows_u = await conn_a.fetch(
            "SELECT id, username FROM users WHERE LOWER(username) LIKE '%pucheta%'"
        )
        if not rows_u:
            # Intentar búsqueda más amplia
            rows_u = await conn_a.fetch(
                "SELECT id, username FROM users WHERE LOWER(username) LIKE '%puch%'"
            )
        if not rows_u:
            print("❌ No se encontró usuario 'pucheta' en app_db.users")
            print("   Usuarios disponibles:")
            all_u = await conn_a.fetch("SELECT id, username FROM users ORDER BY username")
            for u in all_u:
                print(f"     id={u['id']} username={u['username']}")
            return

        if len(rows_u) > 1:
            print("⚠️  Múltiples usuarios con 'pucheta':")
            for u in rows_u:
                print(f"   id={u['id']} username={u['username']}")
            pucheta_id = rows_u[0]['id']
            print(f"   Usando el primero: id={pucheta_id} username={rows_u[0]['username']}")
        else:
            pucheta_id = rows_u[0]['id']
            print(f"✅ PUCHETA encontrada: id={pucheta_id}, username={rows_u[0]['username']}")

        # ── Buscar partido_ids para P089-P096 ──────────────────────────────────
        print("\nBuscando partidos P089-P096...")
        partido_map = {}  # num_fifa -> partido_id
        for row in await conn_b.fetch(
            "SELECT id, numero_fifa, equipo_local_id, equipo_visitante_id FROM partido WHERE numero_fifa BETWEEN 89 AND 96 ORDER BY numero_fifa"
        ):
            partido_map[row['numero_fifa']] = {
                'id': row['id'],
                'eq_local_id': row['equipo_local_id'],
                'eq_vis_id':   row['equipo_visitante_id'],
            }
            print(f"   P{row['numero_fifa']:03d} → partido_id={row['id']}")

        if not partido_map:
            print("❌ No se encontraron partidos con numero_fifa 89-96")
            return

        # ── Mapear nombres de clasificado → equipo_id ──────────────────────────
        equipos_rows = await conn_b.fetch("SELECT id, nombre, nombre_es FROM equipo")
        equipo_lookup = {}  # nombre_upper -> id
        for eq in equipos_rows:
            for n in [eq['nombre'], eq['nombre_es']]:
                if n:
                    equipo_lookup[n.upper().strip()] = eq['id']

        def resolve_equipo(nombre_excel):
            if not nombre_excel:
                return None
            key = nombre_excel.upper().strip()
            # Directo
            if key in equipo_lookup:
                return equipo_lookup[key]
            # Via NOMBRE_MAP
            for alts in NOMBRE_MAP.values():
                if key in [a.upper() for a in alts]:
                    for a in alts:
                        if a.upper() in equipo_lookup:
                            return equipo_lookup[a.upper()]
            print(f"   ⚠️  No se pudo resolver equipo: '{nombre_excel}'")
            return None

        # ── Insertar / actualizar apuestas ─────────────────────────────────────
        print(f"\nImportando apuestas de PUCHETA (apostador_id={pucheta_id})...")
        ok = 0
        errors = 0

        for (num_fifa, pred_l, pred_v, pred_j, pred_k, pred_lv, pred_m, pred_n,
             tanda_l, tanda_v, clasifica_nombre) in APUESTAS_PUCHETA:

            if num_fifa not in partido_map:
                print(f"   ⚠️  P{num_fifa:03d}: partido no encontrado en BD, saltando")
                errors += 1
                continue

            part = partido_map[num_fifa]
            partido_id = part['id']

            # Resolver equipo_clasifica
            pred_equipo_clasifica = None
            if clasifica_nombre:
                pred_equipo_clasifica = resolve_equipo(clasifica_nombre)
                if pred_equipo_clasifica is None:
                    # Fallback: usar local o visitante según nombre
                    key = clasifica_nombre.upper()
                    # No es crítico, dejar NULL
                    print(f"   P{num_fifa:03d}: pred_equipo_clasifica no resuelto ({clasifica_nombre}), se guarda NULL")

            # Tanda: si es 0 o None tratar como NULL (99 = sin tanda en Excel, acá ya filtrado)
            tl = tanda_l if tanda_l and tanda_l != 99 else None
            tv = tanda_v if tanda_v and tanda_v != 99 else None
            pn = pred_n if pred_n and pred_n > 0 else None  # 0 = sin predicción

            try:
                await conn_b.execute("""
                    INSERT INTO apuesta (
                        apostador_id, partido_id,
                        pred_local, pred_visitante,
                        pred_amarillas, pred_rojas, pred_var,
                        pred_penales_partido, pred_minuto_gol,
                        pred_penales_local_tanda, pred_penales_visitante_tanda,
                        pred_equipo_clasifica,
                        puntos, puntos_bonus
                    ) VALUES (
                        $1, $2,
                        $3, $4,
                        $5, $6, $7,
                        $8, $9,
                        $10, $11,
                        $12,
                        0, 0
                    )
                    ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                        pred_local                   = EXCLUDED.pred_local,
                        pred_visitante               = EXCLUDED.pred_visitante,
                        pred_amarillas               = EXCLUDED.pred_amarillas,
                        pred_rojas                   = EXCLUDED.pred_rojas,
                        pred_var                     = EXCLUDED.pred_var,
                        pred_penales_partido         = EXCLUDED.pred_penales_partido,
                        pred_minuto_gol              = EXCLUDED.pred_minuto_gol,
                        pred_penales_local_tanda     = EXCLUDED.pred_penales_local_tanda,
                        pred_penales_visitante_tanda = EXCLUDED.pred_penales_visitante_tanda,
                        pred_equipo_clasifica        = EXCLUDED.pred_equipo_clasifica
                """,
                    pucheta_id, partido_id,
                    pred_l, pred_v,
                    pred_j, pred_k, pred_lv,
                    pred_m, pn,
                    tl, tv,
                    pred_equipo_clasifica
                )
                print(f"   ✅ P{num_fifa:03d}: {pred_l}-{pred_v} | J={pred_j} K={pred_k} L={pred_lv} M={pred_m} N={pn} | Tanda {tl}/{tv} | Clasifica_id={pred_equipo_clasifica}")
                ok += 1
            except Exception as e:
                print(f"   ❌ P{num_fifa:03d}: Error al insertar: {e}")
                errors += 1

        print(f"\n{'='*50}")
        print(f"✅ Importación completada: {ok} OK, {errors} errores")
        if ok > 0:
            print("   Correr POST /calcular-puntajes/2 desde portal para actualizar puntajes.")

    finally:
        await conn_b.close()
        await conn_a.close()


if __name__ == '__main__':
    asyncio.run(main())
