"""
Diagnostica y corrige el tercer partido de Paraguay.
Conecta directamente a PostgreSQL (sin necesitar uvicorn).
Output: fix_paraguay_log.txt
"""
import asyncio, subprocess, json, sys
from datetime import datetime

LOG = open("fix_paraguay_log.txt", "w", encoding="utf-8")

def log(msg=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()

def psql(sql, db="becbuc"):
    """Ejecuta SQL en Docker y retorna las filas."""
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

TORNEO_ID = 2

async def main():
    log("=== DIAGNOSTICO Y FIX PARAGUAY ===\n")

    # 1. Buscar equipo Paraguay
    log("[1] Buscando equipo Paraguay en BD...")
    rows, err = psql("""
        SELECT id, nombre, nombre_es FROM equipo
        WHERE nombre ILIKE '%paraguay%' OR nombre_es ILIKE '%paraguay%'
        LIMIT 5
    """)
    if not rows:
        log(f"  ERROR: no se encontró Paraguay. stderr: {err}")
        LOG.close(); input("Enter..."); return

    for r in rows:
        log(f"  {r}")
    py_id = rows[0].split("|")[0].strip()
    py_nombre = rows[0].split("|")[1].strip()
    log(f"  -> Paraguay ID={py_id} ({py_nombre})")

    # 2. Ver TODOS los partidos de Paraguay en el torneo
    log(f"\n[2] Partidos de Paraguay (id={py_id}) en torneo {TORNEO_ID}...")
    rows, _ = psql(f"""
        SELECT p.id, p.numero_fifa, f.nombre AS fase, f.tipo,
               e_l.nombre AS local, p.goles_local,
               e_v.nombre AS visitante, p.goles_visitante,
               p.estado, p.datos_confirmados,
               p.amarillas, p.rojas, p.penales_tanda_local, p.penales_tanda_visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        JOIN equipo e_l ON e_l.id = p.equipo_local_id
        JOIN equipo e_v ON e_v.id = p.equipo_visitante_id
        WHERE p.torneo_id={TORNEO_ID}
          AND (p.equipo_local_id={py_id} OR p.equipo_visitante_id={py_id})
          AND f.tipo='grupo'
        ORDER BY p.numero_fifa ASC
    """)
    if not rows:
        log("  No se encontraron partidos de grupo para Paraguay!")
    for r in rows:
        cols = r.split("|")
        pid, num, fase, tipo = cols[0], cols[1], cols[2], cols[3]
        local, gl, vis, gv = cols[4], cols[5], cols[6], cols[7]
        estado, confirmado = cols[8], cols[9]
        amar, rojas = cols[10], cols[11]
        log(f"  Partido P{num} (id={pid}): {local} {gl}-{gv} {vis}")
        log(f"    estado={estado} | confirmado={confirmado} | amarillas={amar} | rojas={rojas}")

    # 3. Ver participacion actual de Paraguay
    log(f"\n[3] Participacion actual de Paraguay en grupos...")
    rows, _ = psql(f"""
        SELECT pa.id, f.nombre AS fase, pa.pj, pa.pg, pa.pe, pa.pp,
               pa.gf, pa.gc, pa.pts, pa.posicion,
               COALESCE(pa.fair_play_pts,0) AS fp
        FROM participacion pa
        JOIN fase f ON f.id = pa.fase_id
        WHERE pa.equipo_id={py_id} AND pa.fase_id IN (
            SELECT id FROM fase WHERE torneo_id={TORNEO_ID} AND tipo='grupo'
        )
    """)
    for r in rows:
        cols = r.split("|")
        log(f"  {cols[1]}: PJ={cols[2]} PG={cols[3]} PE={cols[4]} PP={cols[5]} "
            f"GF={cols[6]} GC={cols[7]} Pts={cols[8]} Pos={cols[9]} FP={cols[10]}")

    # 4. Calcular standings desde cero para el grupo de Paraguay
    log(f"\n[4] Recalculando standings del grupo de Paraguay desde partidos finalizados...")

    # Obtener la fase_id del grupo de Paraguay
    rows_fase, _ = psql(f"""
        SELECT DISTINCT p.fase_id, f.nombre
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE (p.equipo_local_id={py_id} OR p.equipo_visitante_id={py_id})
          AND p.torneo_id={TORNEO_ID}
          AND f.tipo='grupo'
        LIMIT 1
    """)
    if not rows_fase:
        log("  No se encontró la fase del grupo de Paraguay!")
        LOG.close(); input("Enter..."); return

    fase_id = rows_fase[0].split("|")[0].strip()
    fase_nombre = rows_fase[0].split("|")[1].strip()
    log(f"  Grupo de Paraguay: {fase_nombre} (fase_id={fase_id})")

    # Ver todos los partidos del grupo
    rows, _ = psql(f"""
        SELECT e_l.id, e_l.nombre, p.goles_local, p.goles_visitante, e_v.id, e_v.nombre,
               p.estado, p.datos_confirmados, p.id AS partido_id
        FROM partido p
        JOIN equipo e_l ON e_l.id = p.equipo_local_id
        JOIN equipo e_v ON e_v.id = p.equipo_visitante_id
        WHERE p.fase_id={fase_id}
        ORDER BY p.numero_fifa ASC
    """)
    log(f"\n  Todos los partidos del {fase_nombre}:")
    standings = {}
    for r in rows:
        cols = r.split("|")
        lid, lnom, gl, gv, vid, vnom, estado, confirmado, pid = cols
        gl = int(gl) if gl.strip().lstrip('-').isdigit() else None
        gv = int(gv) if gv.strip().lstrip('-').isdigit() else None
        log(f"    P{pid}: {lnom} {gl}-{gv} {vnom} [{estado}] confirmado={confirmado}")

        for eid, enom in [(lid, lnom), (vid, vnom)]:
            if eid not in standings:
                standings[eid] = {"id": eid, "nombre": enom, "pj": 0, "pg": 0, "pe": 0,
                                  "pp": 0, "gf": 0, "gc": 0, "gd": 0, "pts": 0}

        if estado.strip() == 'finalizado' and gl is not None and gv is not None:
            loc = standings[lid]; vis = standings[vid]
            loc["pj"] += 1; vis["pj"] += 1
            loc["gf"] += gl; vis["gf"] += gv
            loc["gc"] += gv; vis["gc"] += gl
            loc["gd"] += gl - gv; vis["gd"] += gv - gl
            if gl > gv:
                loc["pg"] += 1; loc["pts"] += 3; vis["pp"] += 1
            elif gl == gv:
                loc["pe"] += 1; loc["pts"] += 1; vis["pe"] += 1; vis["pts"] += 1
            else:
                vis["pg"] += 1; vis["pts"] += 3; loc["pp"] += 1

    log(f"\n  Standings calculados desde partidos finalizados:")
    sorted_teams = sorted(standings.values(), key=lambda e: (-e["pts"], -e["gd"], -e["gf"]))
    for i, eq in enumerate(sorted_teams):
        marker = " <-- PARAGUAY" if str(eq["id"]).strip() == str(py_id).strip() else ""
        log(f"    {i+1}. {eq['nombre']}: PJ={eq['pj']} Pts={eq['pts']} DG={eq['gd']:+d} GF={eq['gf']}{marker}")

    # 5. Actualizar participacion con los valores correctos
    log(f"\n[5] Actualizando participacion con standings correctos...")
    for i, eq in enumerate(sorted_teams):
        eid = eq["id"]
        upd_sql = (f"UPDATE participacion SET pj={eq['pj']}, pg={eq['pg']}, pe={eq['pe']}, "
                   f"pp={eq['pp']}, gf={eq['gf']}, gc={eq['gc']}, pts={eq['pts']}, "
                   f"posicion={i+1} WHERE fase_id={fase_id} AND equipo_id={eid}")
        _, err = psql(upd_sql)
        if err and 'ERROR' in err:
            log(f"  ERROR updating {eq['nombre']}: {err}")
        else:
            log(f"  ✓ {eq['nombre']}: PJ={eq['pj']} Pts={eq['pts']} pos={i+1}")

    # 6. Verificar si hay partidos con datos_confirmados=True que impiden sync
    log(f"\n[6] Verificando datos_confirmados en partidos de Paraguay...")
    rows, _ = psql(f"""
        SELECT p.id, p.numero_fifa, p.estado, p.datos_confirmados,
               p.goles_local, p.goles_visitante
        FROM partido p
        WHERE (p.equipo_local_id={py_id} OR p.equipo_visitante_id={py_id})
          AND p.torneo_id={TORNEO_ID}
          AND f.tipo='grupo'
        ORDER BY p.numero_fifa ASC
    """)
    # Simpler query without join
    rows, _ = psql(f"""
        SELECT p.id, p.numero_fifa, p.estado, p.datos_confirmados,
               COALESCE(p.goles_local::text,'NULL'), COALESCE(p.goles_visitante::text,'NULL')
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE (p.equipo_local_id={py_id} OR p.equipo_visitante_id={py_id})
          AND p.torneo_id={TORNEO_ID}
          AND f.tipo='grupo'
        ORDER BY p.numero_fifa ASC
    """)
    for r in rows:
        cols = r.split("|")
        pid, num, estado, confirmado, gl, gv = cols
        if confirmado.strip() == 'f':
            log(f"  P{num}: datos_confirmados=FALSE → sync puede actualizar este partido")
        else:
            if estado.strip() != 'finalizado' or gl.strip() == 'NULL':
                log(f"  P{num}: datos_confirmados=TRUE pero estado={estado.strip()}, goles={gl.strip()}-{gv.strip()}")
                log(f"         -> PROBLEMA: partido no finalizado pero está confirmado!")
                log(f"         -> Desconfirmando para permitir sync...")
                _, err = psql(f"UPDATE partido SET datos_confirmados=FALSE WHERE id={pid.strip()}")
                if not err or 'ERROR' not in err:
                    log(f"         -> ✓ Desconfirmado P{num}")
                else:
                    log(f"         -> ERROR: {err}")
            else:
                log(f"  P{num}: datos_confirmados=TRUE, estado={estado.strip()}, goles={gl.strip()}-{gv.strip()} OK")

    log(f"\n=== RESUMEN ===")
    log(f"Paraguay en {fase_nombre}: standings actualizados en participacion")
    py_standing = next((e for e in sorted_teams if str(e['id']).strip() == str(py_id).strip()), None)
    if py_standing:
        log(f"Paraguay: PJ={py_standing['pj']} Pts={py_standing['pts']} DG={py_standing['gd']:+d} GF={py_standing['gf']}")
    log(f"\nPRÓXIMOS PASOS RECOMENDADOS:")
    log(f"  1. Si el 3er partido no aparece como finalizado:")
    log(f"     → Finalizar manualmente via portal: Herramientas → Finalizar Partido")
    log(f"     → O esperar que sync_auto.py lo capture (si tiene api_fixture_id)")
    log(f"  2. Luego recalcular puntajes: POST /calcular-puntajes/2")
    log(f"  3. Luego avanzar bracket: POST /avanzar-bracket/2")
    LOG.close()

if __name__ == "__main__":
    asyncio.run(main())
    input("\nPresioná Enter para cerrar...")
