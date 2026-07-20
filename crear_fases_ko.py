"""
crear_fases_ko.py
=================
Crea las 6 fases KO (ronda32, ronda16, cuartos, semis, tercer_puesto, final)
y los 32 partidos TBD vs TBD en la BD becbuc para torneo_id=2.
Prerequisito: 72 partidos de grupos finalizados.
Luego llama al API para avanzar-bracket y calcular-puntajes.
"""

import asyncio
import asyncpg
import urllib.request
import json
from datetime import date, datetime

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2
BASE = "http://localhost:8000"

# Numero_fifa range por tipo
TIPO_NUMS = {
    "ronda32":       list(range(73, 89)),   # 16 partidos
    "ronda16":       list(range(89, 97)),   #  8 partidos
    "cuartos":       list(range(97, 101)),  #  4 partidos
    "semis":         [101, 102],
    "tercer_puesto": [103],
    "final":         [104],
}

# Nombres descriptivos y fechas aproximadas (Copa del Mundo 2026)
TIPO_INFO = {
    "ronda32":       ("Ronda de 32",         "2026-07-01"),
    "ronda16":       ("Ronda de 16 (8vos)",  "2026-07-08"),
    "cuartos":       ("Cuartos de Final",    "2026-07-15"),
    "semis":         ("Semifinales",         "2026-07-22"),
    "tercer_puesto": ("Tercer Puesto",       "2026-07-26"),
    "final":         ("Gran Final",          "2026-07-27"),
}

ORDEN_BASE = 20  # Los grupos usan 1-12; KO desde 20+


async def main():
    conn = await asyncpg.connect(DB_DSN)

    print("=" * 60)
    print("CREAR FASES KO - Torneo", TORNEO_ID)
    print("=" * 60)

    # 1. Verificar grupos
    total_grupos = await conn.fetchval("""
        SELECT COUNT(*) FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = $1 AND f.tipo = 'grupo'
    """, TORNEO_ID)
    fin_grupos = await conn.fetchval("""
        SELECT COUNT(*) FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = $1 AND f.tipo = 'grupo' AND p.estado = 'finalizado'
    """, TORNEO_ID)
    print(f"\nGrupos: {fin_grupos}/{total_grupos} finalizados")

    # 2. Verificar si ya hay fases KO
    ko_count = await conn.fetchval("""
        SELECT COUNT(*) FROM fase WHERE torneo_id = $1 AND tipo <> 'grupo'
    """, TORNEO_ID)
    if ko_count > 0:
        print(f"AVISO: Ya existen {ko_count} fases KO.")
        print("Saltando creacion de fases (ya existen).")
        # Verificar partidos KO
        part_ko = await conn.fetchval("""
            SELECT COUNT(*) FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = $1 AND f.tipo <> 'grupo'
        """, TORNEO_ID)
        print(f"Partidos KO existentes: {part_ko}")
    else:
        # 3. Obtener TBD equipo_id
        tbd_id = await conn.fetchval(
            "SELECT id FROM equipo WHERE UPPER(nombre) = 'TBD' OR nombre ILIKE '%por definir%' OR nombre ILIKE '%a definir%' LIMIT 1"
        )
        if not tbd_id:
            # Crear equipo TBD
            tbd_id = await conn.fetchval("""
                INSERT INTO equipo (nombre, nombre_es, codigo_iso)
                VALUES ('TBD', 'Por Definir', '--')
                RETURNING id
            """)
            print(f"Equipo TBD creado con id={tbd_id}")
        else:
            print(f"Equipo TBD encontrado: id={tbd_id}")

        # 4. Obtener competicion_id del torneo
        torneo = await conn.fetchrow(
            "SELECT id, nombre, competicion_id FROM torneo WHERE id = $1", TORNEO_ID
        )
        if not torneo:
            print("ERROR: Torneo no encontrado.")
            await conn.close()
            return
        print(f"Torneo: {torneo['nombre']} (competicion_id={torneo['competicion_id']})")

        # 5. Crear fases KO
        print("\nCreando fases KO...")
        fase_ids = {}
        for i, (tipo, (nombre, fecha_str)) in enumerate(TIPO_INFO.items()):
            orden = ORDEN_BASE + i
            existing = await conn.fetchval(
                "SELECT id FROM fase WHERE torneo_id=$1 AND tipo=$2 LIMIT 1",
                TORNEO_ID, tipo
            )
            if existing:
                fase_ids[tipo] = existing
                print(f"  {tipo:<15}: ya existe (id={existing})")
            else:
                fase_id = await conn.fetchval("""
                    INSERT INTO fase (torneo_id, nombre, tipo, orden)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, TORNEO_ID, nombre, tipo, orden)
                fase_ids[tipo] = fase_id
                print(f"  {tipo:<15}: CREADA id={fase_id}")

        # 6. Crear partidos TBD
        print("\nCreando partidos KO (TBD vs TBD)...")
        total_creados = 0
        for tipo, nums in TIPO_NUMS.items():
            fase_id = fase_ids[tipo]
            fecha_str = TIPO_INFO[tipo][1]
            for num in nums:
                # Verificar si ya existe
                existing = await conn.fetchval(
                    "SELECT id FROM partido WHERE numero_fifa=$1 AND fase_id=$2",
                    num, fase_id
                )
                if existing:
                    print(f"  P{num:<3} ya existe (id={existing})")
                    continue
                # Crear partido
                pid = await conn.fetchval("""
                    INSERT INTO partido
                        (fase_id, equipo_local_id, equipo_visitante_id,
                         numero_fifa, estado, fecha)
                    VALUES ($1, $2, $3, $4, 'programado', $5)
                    RETURNING id
                """, fase_id, tbd_id, tbd_id, num, fecha_str)
                total_creados += 1
        print(f"  Total partidos creados: {total_creados}")

    # 7. Llamar al API para avanzar bracket y calcular puntajes
    print("\nLlamando al API...")
    try:
        req = urllib.request.Request(
            f"{BASE}/api/v1/auth/login",
            data=json.dumps({"username": "jose", "password": "catalina"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        token = json.loads(urllib.request.urlopen(req, timeout=10).read())["access_token"]
        hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        def api_post(path):
            r = urllib.request.Request(f"{BASE}{path}", data=b"", headers=hdrs, method="POST")
            return json.loads(urllib.request.urlopen(r, timeout=30).read())

        print("  -> Avanzar bracket...")
        ab = api_post(f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}")
        print(f"     {ab}")

        print("  -> Calcular puntajes...")
        pts = api_post(f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}")
        pl = pts.get("plenos", pts.get("partidos_procesados", "?"))
        print(f"     Puntajes OK ({pl} plenos/partidos)")

    except Exception as e:
        print(f"  WARN API: {e}")
        print("  Ejecutar avanzar-bracket y calcular-puntajes manualmente desde el portal.")

    await conn.close()
    print("\nListo. Ejecutar validar_bracket_oficial.py para verificar el resultado.")


if __name__ == "__main__":
    asyncio.run(main())
