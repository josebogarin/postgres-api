# -*- coding: utf-8 -*-
"""
TEST de propagacion de bracket para torneos de CLUBES (Libertadores/Sudamericana).
Simulacion EN MEMORIA (NO escribe en la BD): lee los equipos reales de las fases KO,
arma el cuadro por posicion (octavos -> cuartos -> semis -> final), juega ida/vuelta
aleatorio, propaga el ganador (goles agregados; empate -> penales) y muestra el camino
hasta el campeon. Verifica la LOGICA de encadenamiento.
Ejecutar:  python simular_propagacion_clubes.py <torneo_id>     (1=Libertadores, 14=Sudamericana)
"""
import sys, random, re, unicodedata
import psycopg2

TORNEO_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1
random.seed()

def norm(x):
    if not x: return ""
    return unicodedata.normalize("NFKD", x).encode("ascii","ignore").decode().lower().strip()

TBD = ("tbd", "por definir")
def es_tbd(n): return n is None or norm(n) in TBD
def es_gan(n): return n is not None and norm(n).startswith("gan")

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

def llaves_de(tipo):
    """Devuelve las llaves (parejas de equipos reales) de una fase, agrupando ida+vuelta
    por par de equipos reales presentes."""
    cur.execute("""
        SELECT p.id, p.equipo_local_id, p.equipo_visitante_id, el.nombre, ev.nombre
        FROM partido p
        JOIN fase f ON f.id=p.fase_id
        LEFT JOIN equipo el ON el.id=p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
        WHERE f.torneo_id=%s AND f.tipo=%s ORDER BY p.id
    """, (TORNEO_ID, tipo))
    rows = [{"id":a,"lid":b,"vid":c,"ln":d,"vn":e} for (a,b,c,d,e) in cur.fetchall()]
    grupos, orden = {}, []
    for r in rows:
        ids = []
        if r["lid"] and not es_tbd(r["ln"]): ids.append((r["lid"], r["ln"]))
        if r["vid"] and not es_tbd(r["vn"]): ids.append((r["vid"], r["vn"]))
        key = frozenset(i[0] for i in ids)
        if not key: continue
        if key not in grupos: grupos[key]=[]; orden.append(key)
        for i in ids: grupos[key].append(i)
    out=[]
    for k in orden:
        seen={}
        for (i,n) in grupos[k]: seen[i]=n
        eqs=list(seen.items())  # [(id,nombre), ...] 1 o 2
        out.append(eqs)
    return out

def jugar(a, b):
    """a,b = (id,nombre). Devuelve ganador (id,nombre) con marcador simulado."""
    gi_a, gi_b = random.randint(0,3), random.randint(0,3)  # ida
    gv_a, gv_b = random.randint(0,3), random.randint(0,3)  # vuelta (a de visitante)
    tot_a = gi_a + gv_b
    tot_b = gi_b + gv_a
    if tot_a > tot_b: w = a; d = f"{tot_a}-{tot_b}"
    elif tot_b > tot_a: w = b; d = f"{tot_b}-{tot_a} (global)"
    else:
        # penales
        pa, pb = random.randint(3,5), random.randint(3,5)
        while pa==pb: pb=random.randint(3,5)
        w = a if pa>pb else b; d = f"global {tot_a}-{tot_b}, pen {max(pa,pb)}-{min(pa,pb)}"
    return w, d

print(f"=== SIMULACION PROPAGACION torneo {TORNEO_ID} ===\n")

# --- 16avos -> octavos (solo Sudamericana; resuelve los 'Gan. X/Y') ---
oct_llaves = llaves_de("ronda16")   # octavos
r32 = llaves_de("ronda32")          # 16avos (si hay)
gan16 = {}  # token del cruce -> equipo ganador
if r32:
    print("-- 16avos --")
    for eqs in r32:
        if len(eqs) < 2:
            print(f"  (incompleta) {[n for _,n in eqs]}"); continue
        w, d = jugar(eqs[0], eqs[1])
        print(f"  {eqs[0][1]} vs {eqs[1][1]}  ->  pasa {w[1]}  [{d}]")
        # token para linkear con 'Gan. X/Y': junto los normalizados de los 2 equipos
        gan16[frozenset((norm(eqs[0][1]).split()[0], norm(eqs[1][1]).split()[0]))] = w
    print()

def resolver_rival(nombre_placeholder):
    """'Gan. I.Medellin/Vasco' -> busca en gan16 por tokens."""
    toks = re.split(r"[/ ]+", norm(nombre_placeholder).replace("gan.", "").replace("gan ", ""))
    toks = [t for t in toks if len(t) >= 3]
    best=None
    for key, w in gan16.items():
        if any(any(t.startswith(k) or k.startswith(t) for k in key) for t in toks):
            best=w; break
    return best

# --- armar octavos con equipos resueltos ---
print("-- Octavos (resolviendo rivales de 16avos) --")
octavos=[]
for eqs in oct_llaves:
    reales=[e for e in eqs if not es_gan(e[1])]
    placeholders=[e for e in eqs if es_gan(e[1])]
    if len(reales)==2:
        a,b = reales[0], reales[1]
    elif len(reales)==1 and placeholders:
        a = reales[0]
        rv = resolver_rival(placeholders[0][1])
        b = rv if rv else (placeholders[0][0], placeholders[0][1]+"?")
    elif len(reales)==2:
        a,b=reales
    else:
        a,b = (eqs[0] if eqs else (0,"?")), (eqs[1] if len(eqs)>1 else (0,"?"))
    octavos.append((a,b))
    print(f"  {a[1]}  vs  {b[1]}")
print()

def ronda(nombre, llaves):
    print(f"-- {nombre} --")
    ganadores=[]
    for a,b in llaves:
        w,d = jugar(a,b)
        print(f"  {a[1]} vs {b[1]}  ->  pasa {w[1]}  [{d}]")
        ganadores.append(w)
    print()
    return ganadores

# --- propagacion posicional octavos -> ... -> final ---
gan_oct = ronda("Octavos", octavos)
def emparejar(gs): return [(gs[i], gs[i+1]) for i in range(0, len(gs)-1, 2)]

fase_actual = gan_oct
for nombre in ["Cuartos", "Semifinal", "Final"]:
    llaves = emparejar(fase_actual)
    if not llaves: break
    fase_actual = ronda(nombre, llaves)

if len(fase_actual)==1:
    print(f"*** CAMPEON: {fase_actual[0][1]} ***")
else:
    print(f"(!) termino con {len(fase_actual)} equipos, revisar cantidad de llaves")

cur.close(); conn.close()
