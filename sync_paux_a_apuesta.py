"""
Script consolidado - pronosticos_aux:
1. numero_partido_fifa (P001->1)
2. idequipolocal / idequipovisitante (lookup equipo del torneo_id=2 + dict ES->EN)
3. UPDATE apuesta: pred_local, pred_visitante, pred_amarillas, pred_rojas,
                   pred_var, pred_penales_partido, pred_minuto_gol
   Join: apuesta.numero_fifa = pronosticos_aux.numero_partido_fifa
         + nombre_apostador match
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2, traceback, unicodedata, re

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = _osp.path.join(_BASE, 'resultado_sync_paux.txt')

# Traduccion ES -> EN para nombres de equipos Copa Mundial
DICT_ES_EN = {
    "arabia saudita": "saudi arabia",
    "argelia": "algeria",
    "belgica": "belgium",
    "bosnia herzegovina": "bosnia and herzegovina",
    "bosnia y herzegovina": "bosnia and herzegovina",
    "brasil": "brazil",
    "cabo verde": "cape verde islands",
    "congo": "congo dr",
    "congo dr": "congo dr",
    "curazao": "curacao",
    "curacoa": "curacao",
    "francia": "france",
    "irak": "iraq",
    "jordania": "jordan",
    "catar": "qatar",
    "chequia": "czech republic",
    "costa marfil": "ivory coast",
    "costa de marfil": "ivory coast",
    "dinamarca": "denmark",
    "espana": "spain",
    "estados unidos": "usa",
    "hungria": "hungary",
    "iran": "iran",
    "marruecos": "morocco",
    "noruega": "norway",
    "paises bajos": "netherlands",
    "holanda": "netherlands",
    "portugal": "portugal",
    "rumania": "romania",
    "senegal": "senegal",
    "turquia": "turkey",
    "turkiye": "turkey",
    "alemania": "germany",
    "corea del sur": "south korea",
    "corea del norte": "north korea",
    "suiza": "switzerland",
    "suecia": "sweden",
    "escocia": "scotland",
    "gales": "wales",
    "irlanda": "ireland",
    "irlanda del norte": "northern ireland",
    "austria": "austria",
    "belgica": "belgium",
    "japon": "japan",
    "camerun": "cameroon",
    "ghana": "ghana",
    "tunez": "tunisia",
    "egipto": "egypt",
    "nigeria": "nigeria",
    "angola": "angola",
    "tanzania": "tanzania",
    "mozambique": "mozambique",
    "sudafrica": "south africa",
    "nueva zelanda": "new zealand",
    "nueva zelandia": "new zealand",
    "haiti": "haiti",
    "curacao": "curacao",
    "trinidad y tobago": "trinidad and tobago",
    "trinidad tobago": "trinidad and tobago",
    "guinea ecuatorial": "equatorial guinea",
    "republica checa": "czech republic",
    "eslovakia": "slovakia",
    "eslovenia": "slovenia",
    "croacia": "croatia",
    "rumania": "romania",
    "serbia": "serbia",
    "ucrania": "ukraine",
    "grecia": "greece",
    "turquia": "turkey",
    "nigeria": "nigeria",
    "marruecos": "morocco",
    "mali": "mali",
    "burkina faso": "burkina faso",
    "costa rica": "costa rica",
    "el salvador": "el salvador",
    "panama": "panama",
    "guadalupe": "guadeloupe",
    "martinica": "martinique",
    "jamaica": "jamaica",
    "cuba": "cuba",
    "guatemala": "guatemala",
    "honduras": "honduras",
    "nicaragua": "nicaragua",
    "republica dominicana": "dominican republic",
    "republica dominicana": "dominican republic",
    "venezuela": "venezuela",
    "colombia": "colombia",
    "peru": "peru",
    "chile": "chile",
    "ecuador": "ecuador",
    "bolivia": "bolivia",
    "argentina": "argentina",
    "uruguay": "uruguay",
    "china": "china",
    "india": "india",
    "tailandia": "thailand",
    "indonesia": "indonesia",
    "vietnam": "vietnam",
    "filipinas": "philippines",
    "malasia": "malaysia",
    "corea": "south korea",
    "belgica": "belgium",
    "holanda": "netherlands",
    "suiza": "switzerland",
    "turquia": "turkey",
    "paises bajos": "netherlands",
}

lines = []

def normalizar(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_equipo_map(cur):
    """Construye mapa normalizado -> equipo_id de equipos en torneo_id=2."""
    cur.execute("""
        SELECT DISTINCT e.id, e.nombre, e.nombre_es, e.codigo_iso
        FROM equipo e
        JOIN participacion p ON p.equipo_id = e.id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2;
    """)
    rows = cur.fetchall()
    if not rows:
        cur.execute("SELECT id, nombre, nombre_es, codigo_iso FROM equipo;")
        rows = cur.fetchall()
        lines.append("AVISO: sin participaciones — usando todos equipos")

    mapa = {}
    for eid, nombre, nombre_es, iso in rows:
        for n in [nombre, nombre_es, iso]:
            if n:
                k = normalizar(n)
                if k:
                    mapa[k] = eid
                # Tambien probar con dict ES->EN
                en = DICT_ES_EN.get(k)
                if en:
                    mapa[en] = eid  # por si el CSV usa el ingles del dict

    lines.append(f"Mapa equipos: {len(mapa)} entradas para {len(rows)} equipos")
    # Mostrar nombres crudos de BD para debug
    lines.append("Nombres crudos en equipo (nombre | nombre_es):")
    for eid, nombre, nombre_es, iso in rows:
        lines.append(f"  id={eid:4d}  {str(nombre):30s}  {str(nombre_es)}")
    return mapa

def run():
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor()

    # ─── PASO 1: numero_partido_fifa ───────────────────────────────
    cur.execute("ALTER TABLE pronosticos_aux ADD COLUMN IF NOT EXISTS numero_partido_fifa INTEGER;")
    cur.execute("""
        UPDATE pronosticos_aux
        SET numero_partido_fifa = CAST(SUBSTRING(id_partido FROM 2) AS INTEGER)
        WHERE numero_partido_fifa IS NULL;
    """)
    lines.append(f"PASO 1 numero_partido_fifa: {cur.rowcount} filas pobladas")

    # ─── PASO 2: idequipolocal / idequipovisitante ─────────────────
    cur.execute("ALTER TABLE pronosticos_aux ADD COLUMN IF NOT EXISTS idequipolocal INTEGER;")
    cur.execute("ALTER TABLE pronosticos_aux ADD COLUMN IF NOT EXISTS idequipovisitante INTEGER;")

    equipo_map = build_equipo_map(cur)

    cur.execute("SELECT DISTINCT equipo_local, equipo_visitante FROM pronosticos_aux;")
    pares = cur.fetchall()

    no_match_local = set()
    no_match_visita = set()
    ok_local = ok_visita = 0

    for local, visita in pares:
        norm_l = normalizar(local)
        norm_v = normalizar(visita)

        # Buscar directo o via traduccion
        eid_l = equipo_map.get(norm_l) or equipo_map.get(DICT_ES_EN.get(norm_l, ""))
        eid_v = equipo_map.get(norm_v) or equipo_map.get(DICT_ES_EN.get(norm_v, ""))

        if eid_l:
            cur.execute("""
                UPDATE pronosticos_aux SET idequipolocal = %s
                WHERE LOWER(equipo_local) = LOWER(%s);
            """, (eid_l, local))
            ok_local += cur.rowcount
        else:
            no_match_local.add(local)

        if eid_v:
            cur.execute("""
                UPDATE pronosticos_aux SET idequipovisitante = %s
                WHERE LOWER(equipo_visitante) = LOWER(%s);
            """, (eid_v, visita))
            ok_visita += cur.rowcount
        else:
            no_match_visita.add(visita)

    lines.append(f"PASO 2 local   : {ok_local} filas con idequipolocal")
    lines.append(f"PASO 2 visita  : {ok_visita} filas con idequipovisitante")
    if no_match_local:
        lines.append(f"SIN MATCH local  ({len(no_match_local)}): {sorted(no_match_local)}")
    if no_match_visita:
        lines.append(f"SIN MATCH visita ({len(no_match_visita)}): {sorted(no_match_visita)}")

    # ─── PASO 3: diagnosticar apuesta.numero_fifa ──────────────────
    cur.execute("""
        SELECT COUNT(*), COUNT(a.numero_fifa)
        FROM apuesta a
        JOIN partido pt ON pt.id = a.partido_id
        JOIN fase f ON f.id = pt.fase_id
        WHERE f.torneo_id = 2;
    """)
    total_ap, con_num = cur.fetchone()
    lines.append(f"Apuestas torneo 2: total={total_ap}, con numero_fifa={con_num}")

    # ─── PASO 4: UPDATE apuesta ────────────────────────────────────
    # En PostgreSQL UPDATE...FROM no permite referenciar la tabla target
    # en los JOINs del FROM — hay que usar coma y mover condiciones al WHERE.
    if con_num and con_num > 0:
        lines.append("Estrategia A: join por numero_fifa")
        sql = """
            UPDATE apuesta a
            SET
                pred_local           = pa.goles_local,
                pred_visitante       = pa.goles_visitante,
                pred_amarillas       = pa.amarillas,
                pred_rojas           = pa.rojas,
                pred_var             = pa.var,
                pred_penales_partido = pa.penales,
                pred_minuto_gol      = pa.primer_gol
            FROM pronosticos_aux pa,
                 partido pt,
                 fase f
            WHERE pt.id  = a.partido_id
              AND f.id   = pt.fase_id
              AND f.torneo_id = 2
              AND a.numero_fifa = pa.numero_partido_fifa
              AND LOWER(a.nombre_apostador) = LOWER(pa.nombre);
        """
    else:
        lines.append("Estrategia B: join por idequipolocal/idequipovisitante")
        sql = """
            UPDATE apuesta a
            SET
                pred_local           = pa.goles_local,
                pred_visitante       = pa.goles_visitante,
                pred_amarillas       = pa.amarillas,
                pred_rojas           = pa.rojas,
                pred_var             = pa.var,
                pred_penales_partido = pa.penales,
                pred_minuto_gol      = pa.primer_gol
            FROM pronosticos_aux pa,
                 partido pt,
                 fase f
            WHERE pt.equipo_local_id    = pa.idequipolocal
              AND pt.equipo_visitante_id = pa.idequipovisitante
              AND f.id   = pt.fase_id
              AND f.torneo_id = 2
              AND a.partido_id = pt.id
              AND LOWER(a.nombre_apostador) = LOWER(pa.nombre)
              AND pa.idequipolocal IS NOT NULL
              AND pa.idequipovisitante IS NOT NULL;
        """

    cur.execute(sql)
    n = cur.rowcount
    lines.append(f"PASO 4 UPDATE apuesta: {n} filas actualizadas")

    # Verificacion
    cur.execute("""
        SELECT a.nombre_apostador, a.numero_fifa, a.pred_local, a.pred_visitante, a.pred_amarillas
        FROM apuesta a
        JOIN partido pt ON pt.id = a.partido_id
        JOIN fase f ON f.id = pt.fase_id
        WHERE f.torneo_id = 2
          AND a.pred_local IS NOT NULL
        ORDER BY a.nombre_apostador, a.numero_fifa
        LIMIT 8;
    """)
    rows = cur.fetchall()
    lines.append(f"Muestra apuesta actualizada ({len(rows)} filas):")
    for r in rows:
        lines.append(f"  apostador={r[0][:20]:20s}  num={r[1]}  pred={r[2]}-{r[3]}  amar={r[4]}")

    cur.close()
    conn.close()

try:
    run()
except Exception as e:
    lines.append(f"ERROR: {e}")
    lines.append(traceback.format_exc())

try:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK — {OUT}")
except Exception:
    with open(r"C:\resultado_sync_fallback.txt", "w") as f:
        f.write("\n".join(lines) + "\n")

for l in lines:
    print(l)
