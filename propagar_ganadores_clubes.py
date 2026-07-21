# -*- coding: utf-8 -*-
"""
PROPAGACION REAL del bracket de clubes: cuando una llave KO esta finalizada (ambas
piernas), calcula el ganador (goles agregados; empate -> penales de la vuelta) y lo
mete en el slot de la ronda siguiente:
  16avos  -> reemplaza el placeholder "Gan. X/Y" del octavo (match por tokens).
  Octavos -> reemplaza "Gan. O{k}" en Cuartos (posicional).
  Cuartos -> reemplaza "Gan. C{k}" en Semis.
  Semis   -> reemplaza "Gan. S{k}" en Final.
Requiere el arbol creado (crear_arbol_ko_clubes.py). Idempotente.
Ejecutar:  python propagar_ganadores_clubes.py <torneo_id> [--apply]
"""
import sys, re, unicodedata
import psycopg2

TORNEO_ID = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
APPLY = "--apply" in sys.argv

def norm(x):
    if not x: return ""
    return unicodedata.normalize("NFKD", x).encode("ascii","ignore").decode().lower().strip()
TBD=("tbd","por definir")
def es_tbd(n): return n is None or norm(n) in TBD

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

def llaves_full(tipo):
    cur.execute("""SELECT p.id,p.equipo_local_id,p.equipo_visitante_id,el.nombre,ev.nombre,
                          p.goles_local,p.goles_visitante,p.penales_local,p.penales_visitante,p.estado
                   FROM partido p JOIN fase f ON f.id=p.fase_id
                   LEFT JOIN equipo el ON el.id=p.equipo_local_id
                   LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
                   WHERE f.torneo_id=%s AND f.tipo=%s ORDER BY p.id""",(TORNEO_ID,tipo))
    rows=[dict(zip(("id","lid","vid","ln","vn","gl","gv","pl","pv","est"),r)) for r in cur.fetchall()]
    grupos,orden={},[]
    for r in rows:
        ids=[i for i in ((r["lid"],r["ln"]),(r["vid"],r["vn"])) if i[0] and not es_tbd(i[1])]
        key=frozenset(i[0] for i in ids)
        if not key: continue
        if key not in grupos: grupos[key]=[]; orden.append(key)
        grupos[key].append(r)
    return [grupos[k] for k in orden]

def ganador(legs):
    """legs = lista de partidos de la llave. Devuelve (id,nombre) ganador o None si no decidida."""
    reales=set()
    for r in legs:
        for i,n in ((r["lid"],r["ln"]),(r["vid"],r["vn"])):
            if i and not es_tbd(n): reales.add((i,n))
    if len(reales)!=2: return None
    if not all(r["est"]=="finalizado" and r["gl"] is not None and r["gv"] is not None for r in legs):
        return None
    (a,an),(b,bn)=list(reales)
    agg={a:0,b:0}
    for r in legs:
        if r["lid"] in agg: agg[r["lid"]]+=r["gl"]
        if r["vid"] in agg: agg[r["vid"]]+=r["gv"]
    if agg[a]>agg[b]: return (a,an)
    if agg[b]>agg[a]: return (b,bn)
    # penales (de la pierna que los tenga, normalmente la vuelta)
    for r in legs:
        if r["pl"] is not None and r["pv"] is not None and r["pl"]!=r["pv"]:
            loc_gana = r["pl"]>r["pv"]
            return (r["lid"],r["ln"]) if loc_gana else (r["vid"],r["vn"])
    return None

def eq_id(nombre):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s LIMIT 1",(nombre,))
    r=cur.fetchone(); return r[0] if r else None

def reemplazar(fase_tipo, ph_nombre, winner_id):
    """En la fase_tipo, reemplaza el equipo placeholder (ph_nombre) por winner_id."""
    ph_id=eq_id(ph_nombre)
    if not ph_id: return 0
    cur.execute("""SELECT p.id, p.equipo_local_id, p.equipo_visitante_id FROM partido p
                   JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s AND f.tipo=%s
                   AND (p.equipo_local_id=%s OR p.equipo_visitante_id=%s)""",
                (TORNEO_ID, fase_tipo, ph_id, ph_id))
    n=0
    for pid,lid,vid in cur.fetchall():
        if lid==ph_id:
            if APPLY: cur.execute("UPDATE partido SET equipo_local_id=%s WHERE id=%s",(winner_id,pid))
        else:
            if APPLY: cur.execute("UPDATE partido SET equipo_visitante_id=%s WHERE id=%s",(winner_id,pid))
        n+=1
    return n

# tokens del placeholder "Gan. X/Y" (16avos -> octavos)
def toks(ph):
    t=re.split(r"[/ ]+", norm(ph).replace("gan.","").replace("gan ",""))
    return [x for x in t if len(x)>=3]

print(f"=== PROPAGACION torneo {TORNEO_ID} {'(APPLY)' if APPLY else '(dry-run)'} ===")

# 1) 16avos -> octavos (match por tokens con los 'Gan. X/Y')
r32=llaves_full("ronda32")
if r32:
    # placeholders de octavos
    cur.execute("""SELECT DISTINCT e.id,e.nombre FROM equipo e JOIN partido p
                   ON (p.equipo_local_id=e.id OR p.equipo_visitante_id=e.id)
                   JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s AND f.tipo='ronda16'
                   AND lower(e.nombre) LIKE 'gan%%'""",(TORNEO_ID,))
    phs=[(i,n) for i,n in cur.fetchall()]
    for legs in r32:
        w=ganador(legs)
        if not w: continue
        # equipos del cruce
        reales=set()
        for r in legs:
            for i,n in ((r["lid"],r["ln"]),(r["vid"],r["vn"])):
                if i and not es_tbd(n): reales.add(norm(n).split()[0])
        # buscar placeholder cuyos tokens matcheen
        for pid_e,pn in phs:
            pt=toks(pn)
            if any(any(t.startswith(rt) or rt.startswith(t) for rt in reales) for t in pt):
                n=reemplazar("ronda16", pn, w[0])
                print(f"  16avos {sorted(reales)} -> {w[1]}  reemplaza '{pn}' en octavos ({n} partido/s)")
                break

# 2) posicional: octavos->cuartos (O), cuartos->semis (C), semis->final (S)
for tipo, ab, sig in (("ronda16","O","cuartos"),("cuartos","C","semis"),("semis","S","final")):
    llaves=llaves_full(tipo)
    for k,legs in enumerate(llaves, start=1):
        w=ganador(legs)
        if not w: continue
        n=reemplazar(sig, f"Gan. {ab}{k}", w[0])
        if n: print(f"  {tipo} llave {k} -> {w[1]}  reemplaza 'Gan. {ab}{k}' en {sig} ({n})")

if APPLY:
    conn.commit(); print("== COMMIT ok ==")
else:
    print("== DRY-RUN (agrega --apply para escribir) ==")
cur.close(); conn.close()
