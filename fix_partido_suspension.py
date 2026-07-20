"""
fix_partido_suspension.py
Resetea el partido Francia vs Iraq (suspendido) para que pueda reanudarse y sincronizarse.
Conexion directa via psycopg2 (no API, no Docker exec).
"""

import psycopg2
import psycopg2.extras
from datetime import datetime

DB = dict(host="localhost", port=5432, user="app_user", password="superpassword", dbname="becbuc")
TORNEO_ID = 2

LOG_LINES = []

def log(msg):
    print(msg)
    LOG_LINES.append(msg)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log(f"=== fix_partido_suspension.py === {ts}")
    log("")

    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ------------------------------------------------------------------ #
    # 1. Buscar el partido Francia vs Iraq
    # ------------------------------------------------------------------ #
    log(">> Buscando partido Francia vs Iraq (torneo_id=2)...")

    cur.execute("""
        SELECT
            p.id,
            p.fase_id,
            f.nombre AS fase_nombre,
            el.nombre AS equipo_local,
            ev.nombre AS equipo_visitante,
            p.goles_local,
            p.goles_visitante,
            p.estado,
            p.fecha,
            p.penales_local,
            p.penales_visitante,
            p.minuto_primer_gol,
            p.equipo_clasificado_id,
            p.amarillas,
            p.rojas,
            p.decisiones_var,
            p.penales_partido,
            p.api_fixture_id
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = :tid
          AND (
               el.nombre ILIKE '%franc%' OR el.nombre ILIKE '%irak%' OR el.nombre ILIKE '%iraq%'
            OR ev.nombre ILIKE '%franc%' OR ev.nombre ILIKE '%irak%' OR ev.nombre ILIKE '%iraq%'
          )
        ORDER BY p.fecha
    """.replace(":tid", str(TORNEO_ID)))

    rows = cur.fetchall()

    if not rows:
        log("ERROR: No se encontro ningun partido con equipos que coincidan con 'franc' / 'irak' / 'iraq'.")
        log("Buscando todos los partidos del torneo para ayudar a diagnosticar...")
        cur.execute("""
            SELECT p.id, el.nombre AS local, ev.nombre AS visitante, p.estado, p.goles_local, p.goles_visitante
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE f.torneo_id = %s
            ORDER BY p.fecha
            LIMIT 40
        """, (TORNEO_ID,))
        todos = cur.fetchall()
        log(f"Primeros {len(todos)} partidos en torneo {TORNEO_ID}:")
        for r in todos:
            log(f"  id={r['id']}  {r['local']} vs {r['visitante']}  estado={r['estado']}  {r['goles_local']}-{r['goles_visitante']}")
        conn.close()
        return

    log(f"Partidos encontrados: {len(rows)}")
    log("")

    for p in rows:
        log(f"  ID          : {p['id']}")
        log(f"  Fase        : {p['fase_nombre']} (fase_id={p['fase_id']})")
        log(f"  Partido     : {p['equipo_local']} vs {p['equipo_visitante']}")
        log(f"  Fecha       : {p['fecha']}")
        log(f"  Estado      : {p['estado']}")
        log(f"  Marcador    : {p['goles_local']} - {p['goles_visitante']}")
        log(f"  Penales     : {p['penales_local']} - {p['penales_visitante']}")
        log(f"  Minuto gol  : {p['minuto_primer_gol']}")
        log(f"  Clasificado : {p['equipo_clasificado_id']}")
        log(f"  Amarillas   : {p['amarillas']}")
        log(f"  Rojas       : {p['rojas']}")
        log(f"  VAR         : {p['decisiones_var']}")
        log(f"  Pen. partido: {p['penales_partido']}")
        log(f"  api_fixture : {p['api_fixture_id']}")
        log("")

    # Tomar el primero (deberia ser unico)
    partido = rows[0]
    partido_id = partido['id']

    # ------------------------------------------------------------------ #
    # 2. Contar filas de puntaje_detalle afectadas
    # ------------------------------------------------------------------ #
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM puntaje_detalle
        WHERE torneo_id = %s AND partido_id = %s
    """, (TORNEO_ID, partido_id))
    pd_count = cur.fetchone()['cnt']
    log(f">> puntaje_detalle: {pd_count} filas para este partido (seran eliminadas)")
    log("")

    # ------------------------------------------------------------------ #
    # 3. Aplicar el reset (sin confirmacion interactiva)
    # ------------------------------------------------------------------ #
    log(">> Aplicando reset del partido...")

    cur.execute("""
        UPDATE partido SET
            estado                = 'programado',
            goles_local           = NULL,
            goles_visitante       = NULL,
            penales_local         = NULL,
            penales_visitante     = NULL,
            equipo_clasificado_id = NULL,
            minuto_primer_gol     = NULL,
            amarillas             = NULL,
            rojas                 = NULL,
            decisiones_var        = NULL,
            penales_partido       = NULL,
            minuto_actual         = NULL
        WHERE id = %s
    """, (partido_id,))

    rows_updated = cur.rowcount
    log(f"   partido UPDATE: {rows_updated} fila(s) afectada(s)")

    cur.execute("""
        DELETE FROM puntaje_detalle
        WHERE torneo_id = %s AND partido_id = %s
    """, (TORNEO_ID, partido_id))

    rows_deleted = cur.rowcount
    log(f"   puntaje_detalle DELETE: {rows_deleted} fila(s) eliminadas")

    conn.commit()
    log("")
    log(">> COMMIT OK")

    # ------------------------------------------------------------------ #
    # 4. Verificar resultado
    # ------------------------------------------------------------------ #
    cur.execute("""
        SELECT p.id, p.estado, p.goles_local, p.goles_visitante,
               p.penales_local, p.penales_visitante, p.equipo_clasificado_id,
               p.minuto_primer_gol, p.amarillas, p.rojas, p.decisiones_var
        FROM partido p
        WHERE p.id = %s
    """, (partido_id,))
    updated = cur.fetchone()

    log(">> Estado final del partido:")
    for k, v in updated.items():
        log(f"   {k}: {v}")

    cur.execute("""
        SELECT COUNT(*) AS cnt FROM puntaje_detalle
        WHERE torneo_id = %s AND partido_id = %s
    """, (TORNEO_ID, partido_id))
    pd_after = cur.fetchone()['cnt']
    log(f"   puntaje_detalle restantes: {pd_after}")

    log("")
    log("=== RESET COMPLETADO ===")
    log("Proximos pasos:")
    log("  1. Cuando el partido termine, ejecutar POST /sync-resultados/2 desde el portal")
    log("     (o usar el boton 'Sync desde API-Football' en Herramientas)")
    log("  2. Verificar que api_fixture_id este correcto en la BD para que el sync funcione")
    log("  3. Recalcular puntajes: POST /calcular-puntajes/2")

    conn.close()

if __name__ == "__main__":
    main()
