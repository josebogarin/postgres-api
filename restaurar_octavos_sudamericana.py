# -*- coding: utf-8 -*-
"""
restaurar_octavos_sudamericana.py - Restaura los octavos (ronda16) del torneo 14
al cuadro sembrado manual y RESUELVE los placeholders 'Gan. X/Y' con el ganador
real del R32 (criterio: diferencia de goles global; si empata, penales).

Fases:
  1. CONSERVAR llaves ya correctas (seed vs su placeholder).
  2. BORRAR partidos que no correspondan (los pisados por el avance estilo Mundial).
  3. RECREAR (ida+vuelta) las llaves sembradas que falten.
  4. RESOLVER cada placeholder 'Gan. A/B' con el ganador de esa llave del R32.

Uso:  python restaurar_octavos_sudamericana.py            (DRY-RUN)
      python restaurar_octavos_sudamericana.py --apply
"""
import sys, unicodedata, psycopg2

APPLY = "--apply" in sys.argv
TID = 14

SEEDS = [
    ("Recoleta",               "Rio Parapiti",         "Asuncion",       "Gan. Boca/O'Higgins"),
    ("Atletico Mineiro",       "Arena MRV",            "Belo Horizonte", "Gan. S.Cristal/Bragantino"),
    ("Botafogo",               "Nilton Santos",        "Rio de Janeiro", "Gan. Lanus/Cienciano"),
    ("Olimpia",                "Defensores del Chaco", "Asuncion",       "Gan. I.Medellin/Vasco"),
    ("River Plate",            "Monumental",           "Buenos Aires",   "Gan. Santa Fe/Caracas"),
    ("Montevideo City Torque", "Centenario",           "Montevideo",     "Gan. Nacional/Tigre"),
    ("Macara",                 "Bellavista",           "Ambato",         "Gan. U.Central/Santos"),
    ("Sao Paulo",              "Morumbi",              "Sao Paulo",      "Gan. Bolivar/Gremio"),
]

# placeholder nombre -> (fragmento equipoA, fragmento equipoB) para ubicar la llave R32
PLACEHOLDER_FRAGS = {
    "Gan. Boca/O'Higgins":       ("boca", "higgins"),
    "Gan. S.Cristal/Bragantino": ("cristal", "bragantino"),
    "Gan. Lanus/Cienciano":      ("lanus", "cienciano"),
    "Gan. I.Medellin/Vasco":     ("medellin", "vasco"),
    "Gan. Santa Fe/Caracas":     ("santa fe", "caracas"),
    "Gan. Nacional/Tigre":       ("nacional", "tigre"),
    "Gan. U.Central/Santos":     ("central", "santos"),
    "Gan. Bolivar/Gremio":       ("bolivar", "gremio"),
}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode().lower()
    return s

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

def eq_id(nombre):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s OR nombre_es=%s ORDER BY id LIMIT 1",(nombre,nombre))
    r=cur.fetchone(); return r[0] if r else None

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'", (TID,))
r=cur.fetchone()
if not r:
    print("No existe fase ronda16 para torneo 14. Abortando."); sys.exit(1)
fase_id=r[0]
print(f"Fase octavos id={fase_id}")

# ---------- Fase 1-3: estructura ----------
intended = {frozenset((s[0], s[3])) for s in SEEDS}
cur.execute("""SELECT p.id, el.nombre, ev.nombre
               FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                              JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s ORDER BY p.id""", (fase_id,))
rows=cur.fetchall()
keep=[r for r in rows if frozenset((r[1],r[2])) in intended]
garbage=[r for r in rows if frozenset((r[1],r[2])) not in intended]

print(f"\n--- CONSERVAR ({len(keep)}) ---")
for pid,loc,vis in keep: print(f"  p{pid}: {loc} vs {vis}")
print(f"\n--- BORRAR ({len(garbage)}) ---")
for pid,loc,vis in garbage: print(f"  p{pid}: {loc} vs {vis}")

kept_pairs={frozenset((loc,vis)) for _,loc,vis in keep}
faltan=[s for s in SEEDS if frozenset((s[0],s[3])) not in kept_pairs]
print(f"\n--- RECREAR llaves faltantes ({len(faltan)}) ---")
for s in faltan: print(f"  {s[0]} vs {s[3]}")

# ---------- Fase 4: resolver ganadores del R32 ----------
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32'", (TID,))
r32_fase = cur.fetchone()
tie_winner = {}   # frozenset(fragA,fragB) -> (winner_id, winner_nombre, detalle)
if r32_fase:
    cur.execute("""SELECT p.id, p.equipo_local_id, el.nombre, p.equipo_visitante_id, ev.nombre,
                          p.goles_local, p.goles_visitante, p.penales_local, p.penales_visitante,
                          p.estado, p.fecha
                   FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                                  JOIN equipo ev ON ev.id=p.equipo_visitante_id
                   WHERE p.fase_id=%s ORDER BY p.fecha, p.id""", (r32_fase[0],))
    legs=cur.fetchall()
    # agrupar por par de equipos
    ties={}
    for L in legs:
        pid,lid,ln,vid,vn,gl,gv,pl,pv,est,fecha=L
        key=frozenset((lid,vid))
        ties.setdefault(key,[]).append(L)
    for fr,(fa,fb) in PLACEHOLDER_FRAGS.items():
        # buscar la llave cuyos 2 equipos matcheen fa y fb
        found=None
        for key,ls in ties.items():
            names=[norm(ls[0][2]), norm(ls[0][4])]
            if any(fa in n for n in names) and any(fb in n for n in names):
                found=(key,ls); break
        if not found:
            tie_winner[fr]=(None,None,"llave R32 no encontrada"); continue
        key,ls=found
        # acumular goles por equipo
        agg={}
        pen_leg=None
        allfin=all(x[9]=='finalizado' for x in ls)
        for x in ls:
            _,lid,ln,vid,vn,gl,gv,pl,pv,est,fecha=x
            agg[lid]=agg.get(lid,0)+(gl or 0)
            agg[vid]=agg.get(vid,0)+(gv or 0)
            if pl is not None and pv is not None:
                pen_leg=x
        ids=list(agg.keys())
        if len(ids)!=2 or not allfin:
            tie_winner[fr]=(None,None,f"incompleta (allfin={allfin})"); continue
        a,b=ids
        if agg[a]>agg[b]: win=a
        elif agg[b]>agg[a]: win=b
        else:
            if pen_leg:
                _,lid,ln,vid,vn,gl,gv,pl,pv,est,fecha=pen_leg
                win = lid if (pl or 0)>(pv or 0) else vid
            else:
                tie_winner[fr]=(None,None,f"empate global {agg[a]}-{agg[b]} SIN penales"); continue
        cur.execute("SELECT nombre FROM equipo WHERE id=%s",(win,))
        wn=cur.fetchone()[0]
        det=f"global { {ln if lid==a else vn: agg[a]} }".replace("{","").replace("}","")
        tie_winner[fr]=(win, wn, f"agg {agg[a]}-{agg[b]}")

print("\n--- RESOLUCION placeholders (ganadores R32) ---")
for fr in PLACEHOLDER_FRAGS:
    wid,wn,det=tie_winner.get(fr,(None,None,"n/a"))
    print(f"  {fr:<32} -> {wn or 'INDETERMINADO'}  ({det})")

if not APPLY:
    print("\n== DRY-RUN (agrega --apply para escribir) ==")
    cur.close(); conn.close(); sys.exit(0)

# ---------- APPLY ----------
if garbage:
    ids=tuple(p[0] for p in garbage); in_sql="("+",".join(str(i) for i in ids)+")"
    cur.execute(f"DELETE FROM puntaje_detalle WHERE partido_id IN {in_sql}")
    cur.execute(f"DELETE FROM apuesta WHERE partido_id IN {in_sql}")
    cur.execute(f"DELETE FROM partido WHERE id IN {in_sql}")
    print(f"\nBorrados {len(garbage)} partidos.")

def mk(local_id, visit_id, sede, ciudad):
    cur.execute("""INSERT INTO partido (fase_id, torneo_id, equipo_local_id, equipo_visitante_id,
                   estado, sede, ciudad) VALUES (%s,%s,%s,%s,'programado',%s,%s)""",
                (fase_id, TID, local_id, visit_id, sede, ciudad))

for nombre,vsede,vcd,rival in faltan:
    sid=eq_id(nombre); rid=eq_id(rival)
    if not sid or not rid:
        print(f"  OJO falta equipo {nombre}({sid})/{rival}({rid}); omito"); continue
    mk(rid, sid, "A definir", "A definir")
    mk(sid, rid, vsede, vcd)
    print(f"  creada llave: {nombre} vs {rival}")

# resolver: reemplazar placeholder por ganador en TODOS los octavos
for fr,(wid,wn,det) in tie_winner.items():
    if not wid: 
        print(f"  sin resolver (queda placeholder): {fr} [{det}]"); continue
    ph_id=eq_id(fr)
    if not ph_id: continue
    cur.execute("UPDATE partido SET equipo_local_id=%s WHERE fase_id=%s AND equipo_local_id=%s",
                (wid,fase_id,ph_id))
    cur.execute("UPDATE partido SET equipo_visitante_id=%s WHERE fase_id=%s AND equipo_visitante_id=%s",
                (wid,fase_id,ph_id))
    print(f"  resuelto: {fr} -> {wn}")

conn.commit()
print("\n== COMMIT ok ==")
cur.close(); conn.close()
