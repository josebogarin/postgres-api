#!/usr/bin/env python3
"""
test_propagacion_bracket.py
===========================
Simulacion completa del bracket KO de BECBUC Copa del Mundo 2026.

Llena resultados aleatorios fase por fase (incluyendo empates con tanda de
penales) y verifica que la propagacion de ganadores/perdedores sea correcta
hasta la final y el tercer puesto.

La propagacion se hace directamente en BD (sin llamar avanzar-bracket API)
para evitar el recalculo de mejores terceros que ya no aplica en KO.

ATENCION: sobreescribe los resultados KO en la BD. Solo usar para testing.
"""

import random
import sys
import psycopg2
import requests

# Fix encoding para PowerShell 5.1 (cp1252 no soporta checkmarks/emojis)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── CONFIG ──────────────────────────────────────────────────────────────────
DB_HOST    = "localhost"
DB_PORT    = 5432
DB_NAME    = "becbuc"
DB_USER    = "app_user"
API_BASE   = "http://localhost:8000"
ADMIN_USER = "jose"
ADMIN_PASS = "catalina"
TORNEO_ID  = 2

FASES = ["ronda32", "ronda16", "cuartos", "semis", "tercer_puesto", "final"]
FASE_LABEL = {
    "ronda32":       "Ronda de 32  (P73-P88)",
    "ronda16":       "Octavos      (P89-P96)",
    "cuartos":       "Cuartos      (P97-P100)",
    "semis":         "Semis        (P101-P102)",
    "tercer_puesto": "Tercer Puesto(P103)",
    "final":         "Final        (P104)",
}

TIPO_NUM_RANGE = {
    "ronda32":       list(range(73, 89)),
    "ronda16":       list(range(89, 97)),
    "cuartos":       list(range(97, 101)),
    "semis":         [101, 102],
    "tercer_puesto": [103],
    "final":         [104],
}

# Igual que en ko_scoring.py
KO_FEEDERS = {
    89:  (("W", 74), ("W", 77)),
    90:  (("W", 73), ("W", 75)),
    91:  (("W", 76), ("W", 78)),
    92:  (("W", 79), ("W", 80)),
    93:  (("W", 83), ("W", 84)),
    94:  (("W", 81), ("W", 82)),
    95:  (("W", 86), ("W", 88)),
    96:  (("W", 85), ("W", 87)),
    97:  (("W", 89), ("W", 90)),
    98:  (("W", 93), ("W", 94)),
    99:  (("W", 91), ("W", 92)),
    100: (("W", 95), ("W", 96)),
    101: (("W", 97), ("W", 98)),
    102: (("W", 99), ("W", 100)),
    103: (("L", 101), ("L", 102)),
    104: (("W", 101), ("W", 102)),
}

PCT_EMPATE_PENALES = 0.30


# ── API ──────────────────────────────────────────────────────────────────────
def get_token():
    r = requests.post(f"{API_BASE}/api/v1/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS},
                      timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def api_post(token, path, timeout=120):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API_BASE}{path}", headers=headers, timeout=timeout)
    return r.json()


# ── RESULTADO ALEATORIO ──────────────────────────────────────────────────────
def rand_result_ko():
    if random.random() < PCT_EMPATE_PENALES:
        g = random.randint(0, 2)
        pen_l = random.randint(3, 7)
        pen_v = random.randint(3, 7)
        while pen_l == pen_v:
            pen_v = random.randint(3, 7)
        return g, g, pen_l, pen_v
    else:
        gl = random.randint(0, 4)
        gv = random.randint(0, 4)
        while gl == gv:
            gv = random.randint(0, 4)
        return gl, gv, None, None


def winner_id_from(gl, gv, pen_l, pen_v, local_id, visita_id):
    if gl > gv:
        return local_id
    if gv > gl:
        return visita_id
    return local_id if (pen_l or 0) > (pen_v or 0) else visita_id


def loser_id_from(gl, gv, pen_l, pen_v, local_id, visita_id):
    w = winner_id_from(gl, gv, pen_l, pen_v, local_id, visita_id)
    return visita_id if w == local_id else local_id


def result_str(gl, gv, pen_l, pen_v, local, visita):
    if gl is None or gv is None:
        return "Sin resultado"
    if gl == gv and pen_l is not None:
        w = local if pen_l > pen_v else visita
        return f"{gl}-{gv} (pen {pen_l}-{pen_v}) -> {w}"
    w = local if gl > gv else visita
    return f"{gl}-{gv} -> {w}"


# ── PROPAGACION DIRECTA EN BD ────────────────────────────────────────────────
def build_num2pid(cur, torneo_id):
    """Construye {numero_fifa: partido_id} para todos los partidos KO."""
    cur.execute("""
        SELECT f.tipo, p.id
        FROM partido p
        JOIN fase f ON p.fase_id = f.id
        WHERE f.torneo_id = %s AND f.tipo <> 'grupo'
        ORDER BY f.orden, p.id
    """, (torneo_id,))
    rows = cur.fetchall()
    por_tipo = {}
    for tipo, pid in rows:
        por_tipo.setdefault(tipo, []).append(pid)

    num2pid = {}
    pid2num = {}
    for tipo, nums in TIPO_NUM_RANGE.items():
        for num, pid in zip(nums, por_tipo.get(tipo, [])):
            num2pid[num] = pid
            pid2num[pid] = num
    return num2pid, pid2num


def propagar_fase(cur, torneo_id, fase_tipo, num2pid, pid2num):
    """Propaga ganadores/perdedores a los partidos de la siguiente fase.
    Implementa exactamente la logica de ko_scoring.avanzar_fase_ko()
    pero directamente via psycopg2, sin pasar por la API."""

    # Cargar resultados de todos los KO finalizados
    cur.execute("""
        SELECT p.id, p.equipo_local_id, p.equipo_visitante_id,
               p.goles_local, p.goles_visitante,
               p.penales_local, p.penales_visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = %s AND f.tipo <> 'grupo' AND p.estado = 'finalizado'
    """, (torneo_id,))
    res_por_num = {}
    for row in cur.fetchall():
        pid = row[0]
        num = pid2num.get(pid)
        if num is not None:
            res_por_num[num] = {
                "equipo_local_id":    row[1],
                "equipo_visitante_id": row[2],
                "goles_local":        row[3],
                "goles_visitante":    row[4],
                "penales_local":      row[5],
                "penales_visitante":  row[6],
            }

    # Determinar la fase SIGUIENTE
    idx = FASES.index(fase_tipo)
    if idx >= len(FASES) - 1:
        return  # no hay siguiente
    sig_tipo = FASES[idx + 1]
    nums_sig = TIPO_NUM_RANGE[sig_tipo]

    propagados = 0
    for num in nums_sig:
        feeders = KO_FEEDERS.get(num)
        if not feeders:
            continue
        (sl_tipo, sl_num), (sv_tipo, sv_num) = feeders

        pl = res_por_num.get(sl_num)
        pv = res_por_num.get(sv_num)
        lid = vid = None

        if pl:
            gl, gv = pl["goles_local"], pl["goles_visitante"]
            pen_l, pen_v = pl["penales_local"], pl["penales_visitante"]
            lid_p, vid_p = pl["equipo_local_id"], pl["equipo_visitante_id"]
            if sl_tipo == "W":
                lid = winner_id_from(gl, gv, pen_l, pen_v, lid_p, vid_p)
            else:
                lid = loser_id_from(gl, gv, pen_l, pen_v, lid_p, vid_p)

        if pv:
            gl, gv = pv["goles_local"], pv["goles_visitante"]
            pen_l, pen_v = pv["penales_local"], pv["penales_visitante"]
            lid_p, vid_p = pv["equipo_local_id"], pv["equipo_visitante_id"]
            if sv_tipo == "W":
                vid = winner_id_from(gl, gv, pen_l, pen_v, lid_p, vid_p)
            else:
                vid = loser_id_from(gl, gv, pen_l, pen_v, lid_p, vid_p)

        pid = num2pid.get(num)
        if pid and lid and vid:
            cur.execute("""
                UPDATE partido
                SET equipo_local_id = %s,
                    equipo_visitante_id = %s,
                    estado = 'programado',
                    goles_local = NULL, goles_visitante = NULL,
                    penales_local = NULL, penales_visitante = NULL
                WHERE id = %s
            """, (lid, vid, pid))
            propagados += 1

    return propagados


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    sep  = "=" * 62
    sep2 = "-" * 62

    print(sep)
    print(" TEST PROPAGACION BRACKET - BECBUC Copa del Mundo 2026")
    print(sep)
    print(f" Empate+penales: ~{int(PCT_EMPATE_PENALES*100)}% de los partidos")
    print(f" Propagacion: directa en BD (sin avanzar-bracket API)")
    print()

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                                dbname=DB_NAME, user=DB_USER)
        conn.autocommit = False
        cur = conn.cursor()
        print("OK BD conectada")
    except Exception as e:
        print(f"ERROR BD: {e}")
        sys.exit(1)

    try:
        token = get_token()
        print(f"OK Login ({ADMIN_USER})")
    except Exception as e:
        print(f"ERROR Login: {e}")
        sys.exit(1)

    # Construir mapeo numero_fifa <-> partido_id
    num2pid, pid2num = build_num2pid(cur, TORNEO_ID)
    print(f"OK Mapa KO: {len(num2pid)} partidos\n")

    resumen = {}

    for fase_tipo in FASES:
        print(sep)
        print(f" {FASE_LABEL[fase_tipo]}")
        print(sep2)

        # Cargar partidos de esta fase
        cur.execute("""
            SELECT p.id, p.numero_fifa,
                   COALESCE(el.nombre, 'TBD') AS local,  el.id AS local_id,
                   COALESCE(ev.nombre, 'TBD') AS visita, ev.id AS visita_id,
                   p.estado
            FROM partido p
            JOIN fase f ON p.fase_id = f.id
            LEFT JOIN equipo el ON p.equipo_local_id  = el.id
            LEFT JOIN equipo ev ON p.equipo_visitante_id = ev.id
            WHERE f.torneo_id = %s AND f.tipo = %s
            ORDER BY p.numero_fifa
        """, (TORNEO_ID, fase_tipo))
        matches = cur.fetchall()

        if not matches:
            print("  AVISO: Sin partidos en BD para esta fase")
            break

        # Si todos ya están finalizados, saltar (ya fueron procesados)
        ya_finalizados = all(m[6] == 'finalizado' for m in matches)
        if ya_finalizados:
            print(f"  (ya finalizados, saltando asignacion de scores)")
            # Igual propagamos para asegurarnos
            prop = propagar_fase(cur, TORNEO_ID, fase_tipo, num2pid, pid2num)
            conn.commit()
            if prop is not None and prop > 0:
                print(f"  OK Re-propagacion: {prop} partidos actualizados")
            continue

        # Verificar equipos definidos
        tbd = [m for m in matches if m[2] == "TBD" or m[4] == "TBD"]
        if tbd:
            print(f"  ERROR: {len(tbd)}/{len(matches)} partidos con equipos TBD:")
            for m in tbd:
                print(f"    P{m[1]}: {m[2]} vs {m[4]}")
            print("  -> La propagacion de la fase anterior no funciono.")
            break

        fase_res = []

        for pid, num, local, local_id, visita, visita_id, estado in matches:
            gl, gv, pen_l, pen_v = rand_result_ko()
            w_id = winner_id_from(gl, gv, pen_l, pen_v, local_id, visita_id)

            cur.execute("""
                UPDATE partido SET
                    goles_local           = %s,
                    goles_visitante       = %s,
                    penales_local         = %s,
                    penales_visitante     = %s,
                    equipo_clasificado_id = %s,
                    estado                = 'finalizado',
                    amarillas             = %s,
                    decisiones_var        = %s,
                    penales_partido       = 0
                WHERE id = %s
            """, (gl, gv, pen_l, pen_v, w_id,
                  random.randint(0, 4), random.randint(0, 2), pid))

            rs  = result_str(gl, gv, pen_l, pen_v, local, visita)
            tag = "PEN" if gl == gv else "GOL"
            print(f"  [{tag}] P{num:>3}: {local:<22} vs {visita:<22}  {rs}")
            fase_res.append((local, gl, gv, pen_l, pen_v, visita))

        conn.commit()
        resumen[fase_tipo] = fase_res
        print(f"\n  OK {len(matches)} resultados guardados en BD")
        print(f"  OK Todos los partidos tienen estado=finalizado")

        # Propagar ganadores directamente en BD
        prop = propagar_fase(cur, TORNEO_ID, fase_tipo, num2pid, pid2num)
        conn.commit()

        idx = FASES.index(fase_tipo)
        if idx < len(FASES) - 1:
            sig_tipo = FASES[idx + 1]
            print(f"\n  -> Propagacion a {FASE_LABEL[sig_tipo]}: {prop} partidos actualizados")

            cur.execute("""
                SELECT p.numero_fifa,
                       COALESCE(el.nombre, '??? TBD') AS local,
                       COALESCE(ev.nombre, '??? TBD') AS visita
                FROM partido p
                JOIN fase f ON p.fase_id = f.id
                LEFT JOIN equipo el ON p.equipo_local_id  = el.id
                LEFT JOIN equipo ev ON p.equipo_visitante_id = ev.id
                WHERE f.torneo_id = %s AND f.tipo = %s
                ORDER BY p.numero_fifa
            """, (TORNEO_ID, sig_tipo))
            sigs = cur.fetchall()

            ok_count = 0
            for snum, sloc, svis in sigs:
                tbd_flag = "TBD" in sloc or "TBD" in svis
                icon = "  ERR" if tbd_flag else "   OK"
                print(f"{icon} P{snum:>3}: {sloc:<24} vs {svis}")
                if not tbd_flag:
                    ok_count += 1
            if sigs:
                pct = ok_count * 100 // len(sigs)
                print(f"  -> {ok_count}/{len(sigs)} definidos ({pct}%)")
                if ok_count < len(sigs):
                    print("  ATENCIÓN: hay partidos TBD, revisar KO_FEEDERS")

        print()

    # ── Calcular puntajes via API ─────────────────────────────────────────────
    print(sep)
    print(" CALCULAR PUNTAJES")
    print(sep2)
    try:
        r = api_post(token, f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}")
        procesados = r.get("procesados", r.get("total", str(r)))
        print(f"  OK Puntajes calculados: {procesados} registros")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Resumen de resultados ─────────────────────────────────────────────────
    print()
    print(sep)
    print(" RESUMEN")
    print(sep)
    for fase_tipo, resultados in resumen.items():
        print(f"\n  {FASE_LABEL[fase_tipo]}")
        for local, gl, gv, pen_l, pen_v, visita in resultados:
            rs = result_str(gl, gv, pen_l, pen_v, local, visita)
            print(f"    {local:<22} vs {visita:<22}  {rs}")

    # ── Final y tercer puesto desde BD ────────────────────────────────────────
    print()
    print(sep)
    cur.execute("""
        SELECT f.tipo, p.numero_fifa,
               COALESCE(el.nombre,'?') AS local,   p.goles_local,
               COALESCE(ev.nombre,'?') AS visita,  p.goles_visitante,
               p.penales_local, p.penales_visitante,
               COALESCE(ec.nombre,'?') AS campeon
        FROM partido p
        JOIN fase f ON p.fase_id = f.id
        LEFT JOIN equipo el ON p.equipo_local_id       = el.id
        LEFT JOIN equipo ev ON p.equipo_visitante_id   = ev.id
        LEFT JOIN equipo ec ON p.equipo_clasificado_id = ec.id
        WHERE f.torneo_id = %s AND f.tipo IN ('tercer_puesto','final')
        ORDER BY p.numero_fifa
    """, (TORNEO_ID,))
    for row in cur.fetchall():
        tipo, num, local, gl, visita, gv, pen_l, pen_v, campeon = row
        rs  = result_str(gl, gv, pen_l, pen_v, local, visita)
        etq = "FINAL         " if tipo == "final" else "TERCER PUESTO "
        print(f" {etq} P{num}: {local} vs {visita}")
        print(f"               Resultado: {rs}")
        print(f"               Campeon BD: {campeon}")
        print()

    cur.close()
    conn.close()
    print(sep)
    print(" TEST COMPLETADO")
    print(sep)


if __name__ == "__main__":
    main()
