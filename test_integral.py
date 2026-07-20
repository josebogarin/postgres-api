"""
test_integral.py v3 — Test integral BECBUC, Copa del Mundo.

Flujo completo:
  1. Auto-detecta el torneo Copa del Mundo
  2. Resetea el torneo (resultados + apuestas + puntajes)
  3. Simula resultados aleatorios fase por fase + avanza bracket
  4. Inserta apuestas de prueba deterministas para cada apostador
  5. Calcula puntajes via API
  6. Muestra ranking y verifica scoring vs reglamento
  7. Exporta Excel de auditoría

Estrategias de apuesta:
  apostador1 → marcador exacto siempre       → esperado: máx puntaje
  apostador2 → resultado correcto, marcador +1 → esperado: solo H
  andres     → siempre se equivoca           → esperado: 0 pts
  jose       → random seed=42                → esperado: mixto

Ejecutar:
    cd "C:\\proyecto FAST API"
    backend\\.venv\\Scripts\\python.exe test_integral.py
"""

import json, sys, os, random, subprocess
from datetime import datetime

BASE_URL   = "http://localhost:8000"
TORNEO_ID  = None   # auto-detectado
ADMIN_USER = "admin"
ADMIN_PASS = "faute"

APOSTADOR_CREDS = {
    "apostador1": "faute1964",
    "apostador2": "faute1964",
    "jose":       "catalina",
}

REPORT_FILE  = r"C:\proyecto FAST API\test_integral_report.md"
EXCEL_OUTPUT = r"C:\proyecto FAST API\test_auditoria_output.xlsx"

report_lines = []

def log(msg=""):
    print(msg)
    report_lines.append(str(msg))

def sep(c="─", n=70): log(c * n)

# ── HTTP helper ───────────────────────────────────────────────────────────────
import urllib.request, urllib.error

def _req(method, url, data=None, token=None, binary=False):
    body    = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read() if binary else json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {e.read().decode(errors='replace')[:400]}")

def get(p, tok=None):          return _req("GET",  f"{BASE_URL}{p}", token=tok)
def post(p, d=None, tok=None): return _req("POST", f"{BASE_URL}{p}", data=d, token=tok)
def get_bin(p, tok=None):      return _req("GET",  f"{BASE_URL}{p}", token=tok, binary=True)

# ── psql helpers ──────────────────────────────────────────────────────────────

def psql(sql, db="becbuc"):
    """Query con resultado (rows), via stdin."""
    cmd = ["docker", "exec", "-i", "core-postgres",
           "psql", "-U", "app_user", "-d", db,
           "--tuples-only", "--no-align", "-F", "|"]
    # encoding="utf-8" obligatorio: sin esto, en Windows el SQL se codifica con
    # cp1252 y psql (UTF-8) rechaza caracteres como "é"/"ñ" (ej. "Mbappé").
    r = subprocess.run(cmd, input=sql, capture_output=True,
                       encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"psql error: {r.stderr.strip()[:300]}")
    # Detectar ERROR: psql sale con code 0 aun con errores SQL y los manda a stderr.
    for stream in (r.stdout, r.stderr):
        for line in (stream or "").splitlines():
            if line.startswith("ERROR:"):
                raise RuntimeError(f"psql SQL error: {line}")
    return [row.split("|") for row in r.stdout.strip().splitlines() if row.strip()]

def psql_exec(sql, db="becbuc"):
    """Execute sin retorno, via stdin. Detecta errores SQL."""
    cmd = ["docker", "exec", "-i", "core-postgres",
           "psql", "-U", "app_user", "-d", db, "--no-align"]
    # encoding="utf-8": ver nota en psql(). Sin esto los INSERT con tildes fallan.
    r = subprocess.run(cmd, input=sql, capture_output=True,
                       encoding="utf-8", timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"psql error: {r.stderr.strip()[:300]}")
    # psql escribe errores SQL en stderr y sale con code 0: revisar ambos streams.
    for stream in (r.stdout, r.stderr):
        for line in (stream or "").splitlines():
            if line.startswith("ERROR:"):
                raise RuntimeError(f"psql SQL error: {line}")
    return r.stdout.strip()

# ── Login ─────────────────────────────────────────────────────────────────────

def login(user, pwd):
    r = post("/api/v1/auth/login", {"username": user, "password": pwd})
    t = r.get("access_token")
    if not t: raise RuntimeError(f"Login falló: {r}")
    return t

# ── 1. Auto-detectar torneo Copa del Mundo ────────────────────────────────────

def find_torneo():
    """Busca el torneo Copa del Mundo 2026. Muestra todos si no encuentra."""
    rows = psql("""
        SELECT t.id, t.nombre, COALESCE(c.codigo,'') AS codigo
        FROM torneo t
        JOIN competicion c ON c.id = t.competicion_id
        WHERE t.nombre    ILIKE '%mundial%'
           OR t.nombre    ILIKE '%copa del mundo%'
           OR t.nombre    ILIKE '%world cup%'
           OR t.nombre    ILIKE '%fifa%'
           OR c.nombre    ILIKE '%mundial%'
           OR c.nombre    ILIKE '%world cup%'
           OR c.codigo    ILIKE '%copa_mundo%'
        ORDER BY t.id
        LIMIT 1
    """)
    if rows:
        return int(rows[0][0]), rows[0][1].strip(), rows[0][2].strip()

    all_t = psql("SELECT id, nombre FROM torneo ORDER BY id")
    print("\nTorneos disponibles:")
    for r in all_t:
        print(f"  ID={r[0].strip()}  {r[1].strip()}")
    print("\n→ No se encontró torneo de Copa del Mundo.")
    print("  Editá TORNEO_ID manualmente en este script.")
    sys.exit(1)

# ── 2. Estado del sistema ─────────────────────────────────────────────────────

def check_system(tok):
    sep("═")
    log("# TEST INTEGRAL BECBUC — Copa del Mundo")
    log(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sep("═")
    log(f"\n## 1. Torneo: ID={TORNEO_ID}\n")
    try:
        mon = get(f"/api/v1/bets/monitor-dashboard/{TORNEO_ID}", tok)
        tor = mon.get("torneo", {})
        log(f"  Nombre   : {tor.get('nombre','—')}")
        fases = mon.get("fases", [])
        log(f"  Fases    : {len(fases)}")
    except Exception as e:
        log(f"  ⚠️  monitor-dashboard: {e}")

# ── 3. Obtener fases del torneo ───────────────────────────────────────────────

def get_fases():
    """Devuelve fases ordenadas con su tipo."""
    rows = psql(f"""
        SELECT id, nombre, tipo, orden
        FROM fase
        WHERE torneo_id = {TORNEO_ID}
        ORDER BY orden
    """)
    return [{"id": int(r[0]), "nombre": r[1].strip(),
             "tipo": r[2].strip(), "orden": int(r[3])} for r in rows]

# ── 4. Reset total del torneo ─────────────────────────────────────────────────

def reset_torneo():
    """Borra apuestas/puntajes y resetea resultados de partidos."""
    log("  Borrando apuestas y puntajes...")
    psql_exec(f"""
        DELETE FROM apuesta WHERE partido_id IN
            (SELECT id FROM partido WHERE torneo_id = {TORNEO_ID});
        DELETE FROM puntaje_detalle  WHERE torneo_id = {TORNEO_ID};
        DELETE FROM puntaje_global   WHERE torneo_id = {TORNEO_ID};
        DELETE FROM apuesta_global   WHERE torneo_id = {TORNEO_ID};
    """)

    log("  Reseteando resultados de partidos...")
    # Grupos: limpiar goles + estado
    psql_exec(f"""
        UPDATE partido SET
            goles_local = NULL,
            goles_visitante = NULL,
            penales_local = NULL,
            penales_visitante = NULL,
            amarillas = NULL,
            decisiones_var = NULL,
            minuto_primer_gol = NULL,
            rojas = NULL,
            equipo_clasificado_id = NULL,
            estado = 'pendiente'
        WHERE torneo_id = {TORNEO_ID}
          AND fase_id IN (SELECT id FROM fase WHERE torneo_id = {TORNEO_ID} AND tipo = 'grupo');
    """)
    # KO: limpiar goles + estado (solo fases que no son grupo).
    # NOTA: equipo_local_id/equipo_visitante_id son NOT NULL → no se pueden poner
    # en NULL. El bracket se repuebla con avanzar-bracket durante la simulación,
    # por lo que basta con limpiar resultados y volver a 'pendiente'.
    psql_exec(f"""
        UPDATE partido SET
            goles_local = NULL,
            goles_visitante = NULL,
            penales_local = NULL,
            penales_visitante = NULL,
            amarillas = NULL,
            decisiones_var = NULL,
            minuto_primer_gol = NULL,
            rojas = NULL,
            equipo_clasificado_id = NULL,
            estado = 'pendiente'
        WHERE torneo_id = {TORNEO_ID}
          AND fase_id IN (SELECT id FROM fase WHERE torneo_id = {TORNEO_ID} AND tipo != 'grupo');
    """)
    log("  ✓ Torneo reseteado")

# ── 5. Simular resultados de una fase ─────────────────────────────────────────

TIPO_KO = {"ronda16", "octavos", "cuartos", "semis", "tercero", "final",
           "playoffs", "ko", "playoff"}

def simular_fase(fase):
    """Genera resultados aleatorios para todos los partidos de la fase con equipos asignados."""
    fid  = fase["id"]
    tipo = fase["tipo"]
    es_ko = tipo in TIPO_KO

    # Obtener partidos con equipos asignados (grupos siempre tienen; KO depende de avanzar-bracket)
    if es_ko:
        rows = psql(f"""
            SELECT id, equipo_local_id, equipo_visitante_id
            FROM partido
            WHERE fase_id = {fid}
              AND equipo_local_id IS NOT NULL
              AND equipo_visitante_id IS NOT NULL
              AND estado != 'finalizado'
        """)
    else:
        rows = psql(f"""
            SELECT id, equipo_local_id, equipo_visitante_id
            FROM partido
            WHERE fase_id = {fid}
              AND estado != 'finalizado'
        """)

    if not rows:
        return 0

    simulados = 0
    for row in rows:
        pid = int(row[0])
        gl  = random.randint(0, 3)
        gv  = random.randint(0, 3)

        # KO: no puede terminar empatado en tiempo reglamentario → forzar ganador
        if es_ko and gl == gv:
            # Simular penales en lugar de tiempo extra
            pl = random.randint(3, 6)
            pv = random.randint(3, 6)
            while pl == pv:
                pv = random.randint(3, 6)
            pen_local  = pl
            pen_visit  = pv
            clasificado = f"equipo_local_id" if pl > pv else f"equipo_visitante_id"
            psql_exec(f"""
                UPDATE partido SET
                    goles_local = {gl}, goles_visitante = {gv},
                    penales_local = {pen_local}, penales_visitante = {pen_visit},
                    amarillas = {random.randint(0, 6)},
                    decisiones_var = {random.randint(0, 3)},
                    minuto_primer_gol = {random.randint(1, 90) if gl + gv > 0 else 'NULL'},
                    equipo_clasificado_id = {clasificado},
                    estado = 'finalizado'
                WHERE id = {pid}
            """)
        else:
            clasificado = "equipo_local_id" if gl > gv else ("equipo_visitante_id" if gv > gl else "NULL")
            psql_exec(f"""
                UPDATE partido SET
                    goles_local = {gl}, goles_visitante = {gv},
                    penales_local = NULL, penales_visitante = NULL,
                    amarillas = {random.randint(0, 6)},
                    decisiones_var = {random.randint(0, 3)},
                    minuto_primer_gol = {random.randint(1, 90) if gl + gv > 0 else 'NULL'},
                    equipo_clasificado_id = {clasificado},
                    estado = 'finalizado'
                WHERE id = {pid}
            """)
        simulados += 1
    return simulados

# ── 6. Simular torneo completo ────────────────────────────────────────────────

def simular_torneo_completo(tok):
    log("\n## 2. Simulación de resultados\n")
    fases = get_fases()
    log(f"  Fases encontradas: {len(fases)}")

    total_simulados = 0
    for fase in fases:
        tipo = fase["tipo"]
        nombre = fase["nombre"]

        n = simular_fase(fase)
        total_simulados += n

        if n > 0:
            log(f"  ✓ [{tipo:>10}] {nombre:<30} → {n} partidos simulados")

        # Avanzar bracket después de cada fase para poblar la siguiente
        try:
            rb = post(f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}", tok=tok)
            actualizados = rb.get("actualizados", 0)
            if actualizados > 0:
                log(f"    → bracket avanzado: {actualizados} posiciones KO pobladas")
        except Exception:
            pass  # Normal si ya está avanzado o no hay más fases KO

    log(f"\n  ✓ Total partidos simulados: {total_simulados}")
    return total_simulados

# ── 7. Obtener todos los partidos finalizados ─────────────────────────────────

def get_partidos_finalizados():
    rows = psql(f"""
        SELECT p.id, p.goles_local, p.goles_visitante,
               f.tipo, f.nombre,
               COALESCE(el.nombre_es, el.nombre, '?') AS local_nom,
               COALESCE(ev.nombre_es, ev.nombre, '?') AS visit_nom,
               COALESCE(p.amarillas, 0),
               COALESCE(p.decisiones_var, 0),
               p.minuto_primer_gol,
               COALESCE(p.penales_local, -1),
               COALESCE(p.penales_visitante, -1)
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.torneo_id = {TORNEO_ID}
          AND p.estado = 'finalizado'
          AND p.goles_local IS NOT NULL
        ORDER BY f.orden, p.id
    """)
    partidos = []
    for r in rows:
        try:
            pen_l = int(r[10]) if r[10].strip() != "-1" else None
            pen_v = int(r[11]) if r[11].strip() != "-1" else None
            partidos.append({
                "id":          int(r[0]),
                "goles_local": int(r[1]),
                "goles_vis":   int(r[2]),
                "fase_tipo":   r[3].strip(),
                "fase_nombre": r[4].strip(),
                "local":       r[5].strip()[:15],
                "visitante":   r[6].strip()[:15],
                "amarillas":   int(r[7]),
                "var":         int(r[8]),
                "minuto_gol":  int(r[9]) if r[9].strip() not in ("", "NULL") else None,
                "pen_local":   pen_l,
                "pen_visitante": pen_v,
            })
        except Exception:
            pass
    return partidos

# ── 8. Apostadores ────────────────────────────────────────────────────────────

def get_apostadores_ids():
    rows = psql("""
        SELECT u.id, u.username
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles ro ON ro.id = ur.role_id
        WHERE ro.name = 'apostador' AND u.is_active = TRUE
        ORDER BY u.username
    """, db="app_db")
    return {r[1].strip(): int(r[0]) for r in rows}

# ── 9. Generar pronóstico por estrategia ──────────────────────────────────────

def generar_pronostico(ap_name, partido, idx):
    gl = partido["goles_local"]
    gv = partido["goles_vis"]

    if ap_name == "apostador1":
        # Marcador exacto siempre
        return gl, gv
    elif ap_name == "apostador2":
        # Resultado correcto, marcador ligeramente distinto
        if gl > gv:   return gl + 1, gv        # local gana, +1 gol
        elif gl == gv: return gl + 1, gv + 1   # empate, +1 a ambos
        else:          return gl, gv + 1        # visitante gana, +1 visitante
    elif ap_name == "andres":
        # Siempre se equivoca
        if gl > gv:   return 0, max(1, gl)
        elif gl == gv: return gl + 1, gv
        else:          return max(1, gv), 0
    else:  # jose → random
        random.seed(idx * 17 + partido["id"])
        return random.randint(0, 4), random.randint(0, 4)

# ── 10. Insertar apuestas ─────────────────────────────────────────────────────

def insertar_apuestas(apostadores, partidos):
    log(f"\n  Insertando apuestas: {len(apostadores)} apostadores × {len(partidos)} partidos...")
    valores = []
    total = 0

    for idx, (ap_name, ap_id) in enumerate(apostadores.items()):
        for p in partidos:
            pred_l, pred_v = generar_pronostico(ap_name, p, idx)
            # Pronós de penales (para KO con tanda)
            if p["pen_local"] is not None:
                # Apostador1: acierta tanda exacta; otros: random
                if ap_name == "apostador1":
                    pp_l, pp_v = p["pen_local"], p["pen_visitante"]
                else:
                    random.seed(ap_id + p["id"])
                    pp_l = random.randint(3, 6)
                    pp_v = random.randint(3, 6)
                    while pp_l == pp_v:
                        pp_v = random.randint(3, 6)
                pen_sql = f"{pp_l}, {pp_v}"
            else:
                pen_sql = "NULL, NULL"

            valores.append(
                f"({ap_id}, {p['id']}, {pred_l}, {pred_v}, "
                f"NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', "
                f"{pen_sql})"
            )
            total += 1

    # Insertar en lotes de 200 para evitar límites de stdin
    batch = 200
    for i in range(0, len(valores), batch):
        chunk = valores[i:i+batch]
        vals_str = ",\n".join(chunk)
        psql_exec(f"""
            INSERT INTO apuesta
              (apostador_id, partido_id,
               pred_local, pred_visitante, created_at, updated_at,
               pred_penales_local_tanda, pred_penales_visitante_tanda)
            VALUES {vals_str}
            ON CONFLICT (apostador_id, partido_id) DO UPDATE
              SET pred_local = EXCLUDED.pred_local,
                  pred_visitante = EXCLUDED.pred_visitante,
                  pred_penales_local_tanda = EXCLUDED.pred_penales_local_tanda,
                  pred_penales_visitante_tanda = EXCLUDED.pred_penales_visitante_tanda,
                  updated_at = NOW() AT TIME ZONE 'UTC'
        """)

    # Verificar
    cnt = psql(f"""
        SELECT COUNT(*) FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        WHERE p.torneo_id = {TORNEO_ID}
    """)
    n_real = int(cnt[0][0]) if cnt else 0
    if n_real == total:
        log(f"  ✓ {n_real} apuestas insertadas en BD")
    else:
        log(f"  ⚠️  DISCREPANCIA: esperados {total}, BD tiene {n_real}")
    return total

# ── 11. Resultados reales para globales ───────────────────────────────────────

def get_resultados_globales():
    """Extrae los resultados reales para los items A-G del reglamento."""
    res = {}

    # A/B — Campeón y finalistas (partido final)
    rows = psql(f"""
        SELECT p.equipo_local_id, p.equipo_visitante_id, p.equipo_clasificado_id
        FROM partido p JOIN fase f ON f.id = p.fase_id
        WHERE p.torneo_id = {TORNEO_ID} AND f.tipo = 'final'
          AND p.estado = 'finalizado' LIMIT 1
    """)
    if rows:
        loc_id = rows[0][0].strip(); vis_id = rows[0][1].strip()
        camp_id = rows[0][2].strip() if rows[0][2].strip() not in ("", "NULL") else loc_id
        res["campeon_id"]     = int(camp_id)
        res["finalista1_id"]  = int(loc_id)
        res["finalista2_id"]  = int(vis_id)
    else:
        res["campeon_id"] = res["finalista1_id"] = res["finalista2_id"] = None

    # D — Peor equipo (más derrotas en grupos, menos goles a favor)
    rows = psql(f"""
        SELECT eq_id, SUM(derrotas) AS total_derrotas, SUM(gf) AS goles_fav
        FROM (
            SELECT equipo_local_id AS eq_id,
                   CASE WHEN goles_local < goles_visitante THEN 1 ELSE 0 END AS derrotas,
                   goles_local AS gf
            FROM partido p JOIN fase f ON f.id = p.fase_id
            WHERE p.torneo_id = {TORNEO_ID} AND p.estado='finalizado' AND f.tipo='grupo'
            UNION ALL
            SELECT equipo_visitante_id,
                   CASE WHEN goles_visitante < goles_local THEN 1 ELSE 0 END,
                   goles_visitante
            FROM partido p JOIN fase f ON f.id = p.fase_id
            WHERE p.torneo_id = {TORNEO_ID} AND p.estado='finalizado' AND f.tipo='grupo'
        ) sub
        WHERE eq_id IS NOT NULL
        GROUP BY eq_id
        ORDER BY total_derrotas DESC, goles_fav ASC
        LIMIT 1
    """)
    res["peor_equipo_id"] = int(rows[0][0].strip()) if rows else None

    # E — Mayor goleada
    rows = psql(f"""
        SELECT goles_local, goles_visitante,
               ABS(goles_local - goles_visitante) AS diff
        FROM partido WHERE torneo_id = {TORNEO_ID} AND estado='finalizado'
        ORDER BY diff DESC, (goles_local + goles_visitante) DESC LIMIT 1
    """)
    if rows:
        gl, gv = int(rows[0][0]), int(rows[0][1])
        res["goleada_ganador"]  = max(gl, gv)
        res["goleada_perdedor"] = min(gl, gv)
    else:
        res["goleada_ganador"] = res["goleada_perdedor"] = None

    # F — Etapa más avanzada de Paraguay
    rows = psql(f"""
        SELECT f.tipo, f.orden
        FROM partido p JOIN fase f ON f.id = p.fase_id
        JOIN equipo eq ON (eq.id = p.equipo_local_id OR eq.id = p.equipo_visitante_id)
        WHERE p.torneo_id = {TORNEO_ID} AND p.estado='finalizado'
          AND (eq.nombre ILIKE '%paraguay%' OR eq.nombre_es ILIKE '%paraguay%')
        ORDER BY f.orden DESC LIMIT 1
    """)
    res["etapa_paraguay"] = rows[0][0].strip() if rows else "grupo"

    # G — Goles de Paraguay
    rows = psql(f"""
        SELECT COALESCE(SUM(goles), 0) FROM (
            SELECT p.goles_local AS goles
            FROM partido p
            JOIN equipo eq ON eq.id = p.equipo_local_id
            WHERE p.torneo_id = {TORNEO_ID} AND p.estado='finalizado'
              AND (eq.nombre ILIKE '%paraguay%' OR eq.nombre_es ILIKE '%paraguay%')
            UNION ALL
            SELECT p.goles_visitante
            FROM partido p
            JOIN equipo eq ON eq.id = p.equipo_visitante_id
            WHERE p.torneo_id = {TORNEO_ID} AND p.estado='finalizado'
              AND (eq.nombre ILIKE '%paraguay%' OR eq.nombre_es ILIKE '%paraguay%')
        ) g
    """)
    res["goles_paraguay"] = int(rows[0][0].strip()) if rows else 0

    # Equipos del torneo (para picks aleatorios incorrectos)
    eq_rows = psql(f"""
        SELECT DISTINCT COALESCE(p.equipo_local_id, p.equipo_visitante_id) AS eid
        FROM partido p WHERE p.torneo_id = {TORNEO_ID}
          AND p.equipo_local_id IS NOT NULL
    """)
    res["equipos_ids"] = [int(r[0]) for r in eq_rows if r[0].strip() not in ("", "NULL")]

    return res

# ── 12. Simular apuestas globales A-G ─────────────────────────────────────────

def simular_globales(apostadores):
    """Inserta apuestas globales A-G para cada apostador según su estrategia."""
    log("\n## 3b. Simulando apuestas globales A-G\n")

    reales = get_resultados_globales()
    equipos = reales["equipos_ids"]
    if not equipos:
        log("  ⚠️  Sin equipos en torneo — globales omitidas")
        return

    def equipo_distinto(excluir):
        """Elige un equipo ID diferente al excluido."""
        opciones = [e for e in equipos if e != excluir]
        return random.choice(opciones) if opciones else excluir

    valores = []
    for ap_name, ap_id in apostadores.items():
        camp  = reales.get("campeon_id")
        fin1  = reales.get("finalista1_id")
        fin2  = reales.get("finalista2_id")
        peor  = reales.get("peor_equipo_id")
        gg    = reales.get("goleada_ganador")
        gp_   = reales.get("goleada_perdedor")
        etapa = reales.get("etapa_paraguay", "grupo")
        goles = reales.get("goles_paraguay", 0)

        if ap_name == "apostador1":
            # Siempre correcto
            pred_camp = camp or random.choice(equipos)
            pred_fin1 = fin1 or pred_camp
            pred_fin2 = fin2 or equipo_distinto(pred_fin1)
            pred_gol  = "Lionel Messi"
            pred_peor = peor or random.choice(equipos)
            pred_gg   = gg or 3
            pred_gp   = gp_ if gp_ is not None else 0
            pred_eta  = etapa
            pred_gpy  = goles

        elif ap_name == "apostador2":
            # Acierta campeón, falla un finalista, resto random
            pred_camp = camp or random.choice(equipos)
            pred_fin1 = fin1 or pred_camp
            pred_fin2 = equipo_distinto(fin2 or pred_camp)  # falla fin2
            pred_gol  = "Cristiano Ronaldo"
            pred_peor = equipo_distinto(peor or random.choice(equipos))
            pred_gg   = (gg or 3) + 1
            pred_gp   = max(0, (gp_ if gp_ is not None else 0) - 1)
            pred_eta  = "grupo"
            pred_gpy  = max(0, goles - 2)

        elif ap_name == "andres":
            # Siempre equivocado
            pred_camp = equipo_distinto(camp or random.choice(equipos))
            pred_fin1 = equipo_distinto(fin1 or pred_camp)
            pred_fin2 = equipo_distinto(fin2 or pred_camp)
            pred_gol  = "Zlatan Ibrahimovic"
            pred_peor = equipo_distinto(peor or random.choice(equipos))
            pred_gg   = (gg or 3) + 3
            pred_gp   = (gp_ if gp_ is not None else 0) + 3
            pred_eta  = "final" if etapa == "grupo" else "grupo"
            pred_gpy  = goles + 5

        else:  # jose — random
            random.seed(ap_id * 13)
            pred_camp = random.choice(equipos)
            pred_fin1 = random.choice(equipos)
            pred_fin2 = equipo_distinto(pred_fin1)
            pred_gol  = random.choice(["Mbappé", "Vinicius Jr", "Haaland", "Bellingham"])
            pred_peor = random.choice(equipos)
            pred_gg   = random.randint(2, 6)
            pred_gp   = random.randint(0, 3)
            pred_eta  = random.choice(["grupo", "ronda16", "octavos", "cuartos", "semis"])
            pred_gpy  = random.randint(0, 10)

        null = "NULL"
        def eid(v): return str(v) if v else null

        valores.append(
            f"({TORNEO_ID}, {ap_id}, {eid(pred_camp)}, {eid(pred_fin1)}, {eid(pred_fin2)}, "
            f"'{pred_gol}', {eid(pred_peor)}, "
            f"{pred_gg}, {pred_gp}, '{pred_eta}', {pred_gpy})"
        )
        log(f"  {ap_name:<14} → camp={eid(pred_camp)}  fin1={eid(pred_fin1)}/fin2={eid(pred_fin2)}"
            f"  peor={eid(pred_peor)}  goleada={pred_gg}-{pred_gp}  py_eta={pred_eta} py_goles={pred_gpy}")

    vals_str = ",\n".join(valores)
    psql_exec(f"""
        INSERT INTO apuesta_global
          (torneo_id, apostador_id,
           pred_campeon_id, pred_finalista1_id, pred_finalista2_id,
           pred_goleador, pred_peor_equipo_id,
           pred_goleada_ganador, pred_goleada_perdedor,
           pred_etapa_paraguay, pred_goles_paraguay)
        VALUES {vals_str}
        ON CONFLICT (torneo_id, apostador_id) DO UPDATE
          SET pred_campeon_id       = EXCLUDED.pred_campeon_id,
              pred_finalista1_id    = EXCLUDED.pred_finalista1_id,
              pred_finalista2_id    = EXCLUDED.pred_finalista2_id,
              pred_goleador         = EXCLUDED.pred_goleador,
              pred_peor_equipo_id   = EXCLUDED.pred_peor_equipo_id,
              pred_goleada_ganador  = EXCLUDED.pred_goleada_ganador,
              pred_goleada_perdedor = EXCLUDED.pred_goleada_perdedor,
              pred_etapa_paraguay   = EXCLUDED.pred_etapa_paraguay,
              pred_goles_paraguay   = EXCLUDED.pred_goles_paraguay
    """)
    log(f"  ✓ {len(apostadores)} apuestas globales insertadas")

# ── 13. Calcular puntajes ─────────────────────────────────────────────────────

def calcular_puntajes(tok):
    log("\n## 4. Cálculo de puntajes\n")
    r = post(f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}", tok=tok)
    pl = r.get("plenos", 0); ac = r.get("aciertos", 0); fa = r.get("fallos", 0)
    log(f"  engine   : {r.get('engine','?')}")
    log(f"  plenos   : {pl}")
    log(f"  aciertos : {ac}")
    log(f"  fallos   : {fa}")
    log(f"  total    : {pl + ac + fa} apuestas procesadas")

    if pl + ac + fa == 0:
        cnt_a = psql(f"""SELECT COUNT(*) FROM apuesta a
                         JOIN partido p ON p.id=a.partido_id
                         WHERE p.torneo_id={TORNEO_ID}""")
        cnt_p = psql(f"""SELECT COUNT(*) FROM partido
                         WHERE torneo_id={TORNEO_ID} AND estado='finalizado'""")
        cnt_d = psql(f"SELECT COUNT(*) FROM puntaje_detalle WHERE torneo_id={TORNEO_ID}")
        log(f"\n  ⚠️  SCORING DIO 0 — Diagnóstico:")
        log(f"     apuestas en BD        : {cnt_a[0][0] if cnt_a else '?'}")
        log(f"     partidos finalizados  : {cnt_p[0][0] if cnt_p else '?'}")
        log(f"     puntaje_detalle filas : {cnt_d[0][0] if cnt_d else '?'}")
        log(f"  → ¿Reiniciaste uvicorn después de editar calculator.py?")
    return r

# ── 12. Ranking ───────────────────────────────────────────────────────────────

def mostrar_ranking(tok):
    log("\n## 5. Ranking tras simulación\n")
    rk = get(f"/api/v1/bets/ranking/{TORNEO_ID}", tok)
    ranking = rk if isinstance(rk, list) else rk.get("ranking", [])
    log(f"  {'Pos':>3}  {'Apostador':<14} {'Total':>6} {'Partidos':>9} {'Globales':>9} {'Plenos':>7} {'Aciertos':>9}")
    log(f"  {'─'*3}  {'─'*14} {'─'*6} {'─'*9} {'─'*9} {'─'*7} {'─'*9}")
    for i, r in enumerate(ranking, 1):
        n  = (r.get("nombre") or r.get("email") or "?")[:14]
        pt = r.get("puntos_total", 0)
        pp = r.get("puntos_partidos_total", 0)
        pg = r.get("pts_globales", 0)
        pl = r.get("plenos", 0)
        ac = r.get("aciertos", 0)
        log(f"  {i:>3}  {n:<14} {pt:>6} {pp:>9} {pg:>9} {pl:>7} {ac:>9}")
    return ranking

# ── 13. Verificación scoring vs reglamento ────────────────────────────────────

def verificar_scoring(apostadores):
    log("\n## 6. Verificación scoring engine vs reglamento BEC BUC 2026\n")

    H_PTS = {"grupo":4, "ronda16":6, "octavos":8, "cuartos":10,
             "semis":12, "tercero":14, "final":20}
    I_PTS = {"grupo":8, "ronda16":12,"octavos":16,"cuartos":20,
             "semis":24, "tercero":28, "final":40}

    rows = psql(f"""
        SELECT pd.apostador_id, pd.partido_id,
               pd.pts_resultado, pd.pts_marcador,
               pd.pts_amarillas, pd.pts_var,
               a.pred_local, a.pred_visitante,
               p.goles_local, p.goles_visitante,
               f.tipo AS fase_tipo
        FROM puntaje_detalle pd
        JOIN apuesta a ON a.apostador_id = pd.apostador_id AND a.partido_id = pd.partido_id
        JOIN partido p ON p.id = pd.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE pd.torneo_id = {TORNEO_ID}
        ORDER BY pd.apostador_id, pd.partido_id
        LIMIT 200
    """)

    if not rows:
        log("  ⚠️  puntaje_detalle vacío — el scoring no corrió correctamente.")
        return

    # Resumen por apostador
    log("  ### Puntaje total por apostador (suma de puntaje_detalle)\n")
    for ap_name, ap_id in apostadores.items():
        ap_rows = [r for r in rows if int(r[0]) == ap_id]
        pts = sum(int(r[2] or 0) + int(r[3] or 0) + int(r[4] or 0) + int(r[5] or 0)
                  for r in ap_rows)
        log(f"    {ap_name:<14}: {pts:>6} pts  ({len(ap_rows)} partidos en muestra)")

    # Verificar apostador1 (debe tener H+I en todos)
    log("\n  ### Detalle apostador1 (primeros 8 partidos)\n")
    ap1_id = apostadores.get("apostador1")
    if ap1_id:
        ap1_rows = [r for r in rows if int(r[0]) == ap1_id][:8]
        log(f"  {'PID':>5}  {'Pred':>7}  {'Real':>7}  {'FaseTipo':>10}  "
            f"{'H':>4}  {'I':>4}  {'J':>4}  {'L':>4}  OK?")
        for r in ap1_rows:
            pid     = int(r[1])
            pts_h   = int(r[2] or 0)
            pts_i   = int(r[3] or 0)
            pts_j   = int(r[4] or 0)
            pts_l   = int(r[5] or 0)
            pl, pv  = int(r[6]), int(r[7])
            gl, gv  = int(r[8]), int(r[9])
            ft      = r[10].strip()
            h_exp   = H_PTS.get(ft, 4)
            ok_h    = "✓" if pts_h == h_exp else f"⚠️(exp {h_exp})"
            log(f"  {pid:>5}  {pl}-{pv:<5}  {gl}-{gv:<5}  {ft:>10}  "
                f"{pts_h:>4}  {pts_i:>4}  {pts_j:>4}  {pts_l:>4}  {ok_h}")

    # Verificar andres (debe tener 0 en H e I)
    log("\n  ### Detalle andres (debe ser 0 en H e I)\n")
    andres_id = apostadores.get("andres")
    if andres_id:
        andres_rows = [r for r in rows if int(r[0]) == andres_id][:5]
        for r in andres_rows:
            pts_h = int(r[2] or 0)
            pts_i = int(r[3] or 0)
            pl, pv = int(r[6]), int(r[7])
            gl, gv = int(r[8]), int(r[9])
            ft = r[10].strip()
            ok = "✓" if pts_h == 0 and pts_i == 0 else f"⚠️ H={pts_h} I={pts_i}"
            log(f"    partido #{r[1].strip():>4}  pred={pl}-{pv}  real={gl}-{gv}  [{ft}]  {ok}")

# ── 14. Excel ─────────────────────────────────────────────────────────────────

def generar_excel(tok):
    log("\n## 7. Exportar Excel de auditoría\n")
    try:
        r = post(f"/api/v1/bets/auditoria/{TORNEO_ID}", tok=tok)
        log(f"  ✓ Excel generado: {r.get('apostadores',0)} apostadores · {r.get('partidos',0)} partidos")
        filename = r.get("filename") or r.get("archivo") or ""
        audit_id = r.get("id") or r.get("snapshot_id")
        log(f"  Archivo servidor: {filename}")

        if audit_id:
            try:
                data = get_bin(f"/api/v1/bets/auditoria/download/{audit_id}", tok=tok)
                with open(EXCEL_OUTPUT, "wb") as f:
                    f.write(data)
                log(f"  ✓ Descargado: {EXCEL_OUTPUT} ({len(data)/1024:.1f} KB)")
                return EXCEL_OUTPUT
            except Exception as e:
                log(f"  ⚠️  Descarga via ID: {e}")

        static_path = rf"C:\proyecto FAST API\backend\static\{filename}"
        if filename and os.path.exists(static_path):
            import shutil; shutil.copy2(static_path, EXCEL_OUTPUT)
            log(f"  ✓ Copiado: {EXCEL_OUTPUT}")
            return EXCEL_OUTPUT

        log(f"  → Buscar manualmente: C:\\proyecto FAST API\\backend\\static\\{filename}")
        return None
    except Exception as e:
        log(f"  ✗ Error generando Excel: {e}")
        return None

# ── 15. Tabla de referencia reglamento ───────────────────────────────────────

def tabla_reglamento():
    sep("═")
    log("\n## TABLA DE PUNTAJES OFICIAL — Reglamento BEC BUC 2026\n")
    log(f"  {'Concepto':<25} {'GR':>4} {'16':>4} {'8v':>4} {'4t':>4} {'Se':>4} {'3P':>4} {'Fi':>4}")
    log(f"  {'-'*25} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*4}")
    tabla = [
        ("H - Resultado",         [4,  6,  8, 10, 12, 14, 20]),
        ("I - Marcador exacto",   [8, 12, 16, 20, 24, 28, 40]),
        ("J - Amarillas",         [1,  1,  1,  1,  1,  1,  1]),
        ("K - Rojas",             [1,  1,  1,  1,  1,  1,  1]),
        ("L - VAR",               [1,  1,  1,  1,  1,  1,  1]),
        ("N - Minuto gol",        [1,  1,  1,  1,  1,  1,  1]),
        ("O - Penales tanda",     ["—","2","2","2","2","2","2"]),
    ]
    for name, vals in tabla:
        log("  {:<25}".format(name) + "".join(f" {str(v):>4}" for v in vals))
    log("\n  Paraguay: DOBLE PUNTAJE en todos los conceptos de partido")
    log("\n  Globales A-G: max 112 pts (Campeón 20, Finalistas 20, Goleador 20,")
    log("                             Peor equipo 20, Mayor goleada 20, Py 6+6)")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    global TORNEO_ID
    random.seed(42)

    # Auto-detectar torneo
    tid, tnombre, tcodigo = find_torneo()
    TORNEO_ID = tid
    print(f"\n  Torneo detectado: [{tid}] {tnombre}  (codigo={tcodigo})")

    # Login
    log("\n" + "=" * 70)
    log(f"BECBUC — TEST INTEGRAL  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    log("\n[1/8] Login admin...")
    try:
        tok = login(ADMIN_USER, ADMIN_PASS)
        log("  ✓ Token obtenido")
    except Exception as e:
        log(f"  ✗ FATAL: {e}"); sys.exit(1)

    # Estado sistema
    check_system(tok)

    # Reset
    log("\n[2/8] Reseteando torneo...")
    try:
        reset_torneo()
    except Exception as e:
        log(f"  ✗ Error en reset: {e}"); sys.exit(1)

    # Simular resultados fase por fase
    log("\n[3/8] Simulando resultados de partidos...")
    try:
        total_sim = simular_torneo_completo(tok)
        if total_sim == 0:
            log("  ✗ No se simuló ningún partido. Verificar estructura del torneo.")
            sys.exit(1)
    except Exception as e:
        log(f"  ✗ Error simulando: {e}"); sys.exit(1)

    # Partidos finalizados
    log("\n[4/8] Verificando partidos finalizados...")
    try:
        partidos = get_partidos_finalizados()
        log(f"  ✓ {len(partidos)} partidos finalizados con goles")
        # Muestra por fase
        fases_vistas = {}
        for p in partidos:
            ft = p["fase_tipo"]
            fases_vistas[ft] = fases_vistas.get(ft, 0) + 1
        for ft, n in fases_vistas.items():
            log(f"     {ft:<12}: {n} partidos")
    except Exception as e:
        log(f"  ✗ Error: {e}"); sys.exit(1)

    if not partidos:
        log("  ✗ Sin partidos finalizados."); sys.exit(1)

    # Apostadores
    log("\n[5/8] Obteniendo apostadores...")
    try:
        apostadores = get_apostadores_ids()
        log(f"  ✓ {len(apostadores)} apostadores: {list(apostadores.keys())}")
    except Exception as e:
        log(f"  ✗ Error: {e}"); sys.exit(1)

    # Insertar apuestas de partido
    log("\n[6/9] Cargando apuestas de partido...")
    log("\n## 3. Estrategia de apuestas\n")
    log("  apostador1 → marcador exacto siempre  → esperado: máx puntaje (H+I)")
    log("  apostador2 → resultado OK, marcador+1 → esperado: solo H")
    log("  andres     → siempre equivocado        → esperado: 0 pts")
    log("  jose       → random seed=42            → esperado: mezcla")
    log()
    try:
        insertar_apuestas(apostadores, partidos)
    except Exception as e:
        log(f"  ✗ Error insertando apuestas: {e}"); sys.exit(1)

    # Simular apuestas globales A-G
    log("\n[7/9] Simulando apuestas globales A-G...")
    try:
        simular_globales(apostadores)
    except Exception as e:
        log(f"  ⚠️  globales: {e}")

    # Calcular puntajes (partidos + globales)
    log("\n[8/9] Calculando puntajes...")
    try:
        calcular_puntajes(tok)
    except Exception as e:
        log(f"  ✗ Error calculando puntajes: {e}"); sys.exit(1)

    # Ranking
    ranking = mostrar_ranking(tok)

    # Verificación vs reglamento
    try:
        verificar_scoring(apostadores)
    except Exception as e:
        log(f"  ⚠️  verificación BD: {e}")

    # Excel completo
    log("\n[9/9] Exportando Excel completo...")
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "generar_excel_becbuc",
            r"C:\proyecto FAST API\generar_excel_becbuc.py"
        )
        excel_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(excel_mod)
        excel_path = excel_mod.generar(TORNEO_ID, tok)
    except Exception as e:
        log(f"  ⚠️  Excel completo: {e}")
        log("  → Fallback: excel de auditoría API...")
        excel_path = generar_excel(tok)

    # Tabla reglamento referencia
    tabla_reglamento()

    # Conclusión
    sep("═")
    log("\n## CONCLUSIÓN\n")
    if ranking:
        lider = ranking[0]
        ultimo = ranking[-1]
        log(f"  Apostadores : {len(ranking)}")
        log(f"  Partidos    : {len(partidos)}")
        log(f"  Líder       : {lider.get('nombre','?')} — {lider.get('puntos_total',0)} pts")
        log(f"  Último      : {ultimo.get('nombre','?')} — {ultimo.get('puntos_total',0)} pts")
        if len(ranking) > 1:
            avg = sum(r.get("puntos_total",0) for r in ranking) / len(ranking)
            log(f"  Promedio    : {avg:.1f} pts")
        log(f"\n  ✓ Reporte: {REPORT_FILE}")
        if excel_path:
            log(f"  ✓ Excel  : {excel_path}")
        log(f"\n  Hojas del Excel:")
        log(f"    🏆 Ranking    — clasificación final con desglose")
        log(f"    📋 Resultados — fichas de resultado por fase")
        log(f"    🎯 Apuestas   — pronósticos × partido (verde=exacto, amarillo=resultado, rojo=fallo)")
        log(f"    📊 Puntajes   — detalle H,I,J,K,L,O × jugador × partido")
        log(f"    🌐 Globales   — apuestas bonus A-G vs resultado real")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n{'='*70}")
    print(f"✓ Reporte: {REPORT_FILE}")
    if excel_path:
        print(f"✓ Excel  : {excel_path}")
    print("="*70)


if __name__ == "__main__":
    main()
