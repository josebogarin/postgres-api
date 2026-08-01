# -*- coding: utf-8 -*-
"""
fill_tbd_octavos.py - Asigna equipos a los partidos KO que estan en TBD pero
tienen api_fixture_id real, leyendo el sorteo desde API-Football. Sirve para
completar las idas de Libertadores (torneo 1) que quedaron sin equipos, de modo
que cada llave ida/vuelta se agrupe bien.

Uso:  python fill_tbd_octavos.py [torneo_id] [fase_tipo]      (DRY-RUN)
      python fill_tbd_octavos.py [torneo_id] [fase_tipo] --apply
Default: torneo_id=1  fase_tipo=ronda16
"""
import sys, os, json, urllib.request, urllib.error, psycopg2

args=[a for a in sys.argv[1:] if a!="--apply"]
APPLY="--apply" in sys.argv
TID=int(args[0]) if len(args)>=1 else 1
FASE=args[1] if len(args)>=2 else "ronda16"

# API key desde backend/.env
_ROOT=os.path.dirname(os.path.abspath(__file__))
KEY=None
try:
    for ln in open(os.path.join(_ROOT,"backend",".env"),encoding="utf-8"):
        if ln.strip().startswith("APIFOOTBALL_KEY"):
            KEY=ln.split("=",1)[1].strip().strip('"').strip("'"); break
except Exception as e:
    print("No pude leer backend/.env:",e)
if not KEY:
    print("APIFOOTBALL_KEY no encontrado en backend/.env"); sys.exit(1)

API="https://v3.football.api-sports.io"
HDR={"x-rapidapi-key":KEY,"x-rapidapi-host":"v3.football.api-sports.io"}

def api_fixture(fix_id):
    req=urllib.request.Request(f"{API}/fixtures?id={fix_id}",headers=HDR)
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode()).get("response",[])

conn=psycopg2.connect(host="localhost",port=5432,dbname="becbuc",user="app_user",password="superpassword")
cur=conn.cursor()

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo=%s",(TID,FASE))
r=cur.fetchone()
if not r: print(f"No hay fase {FASE} en torneo {TID}"); sys.exit(1)
fase_id=r[0]

# mapa api_team_id -> equipo_id
cur.execute("SELECT api_team_id,id,nombre FROM equipo WHERE api_team_id IS NOT NULL")
tmap={row[0]:(row[1],row[2]) for row in cur.fetchall()}

# partidos TBD con fixture
cur.execute("""SELECT p.id, p.api_fixture_id, el.nombre, ev.nombre
               FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                              JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s AND p.api_fixture_id IS NOT NULL
                 AND (LOWER(el.nombre) IN ('tbd','por definir') OR LOWER(ev.nombre) IN ('tbd','por definir'))
               ORDER BY p.id""",(fase_id,))
pend=cur.fetchall()
print(f"Fase {FASE} id={fase_id}: {len(pend)} partidos TBD con fixture\n")

plan=[]
for pid,fix,ln,vn in pend:
    try:
        resp=api_fixture(fix)
    except Exception as e:
        print(f"  p{pid} fix={fix}: error API {e}"); continue
    if not resp:
        print(f"  p{pid} fix={fix}: API sin datos"); continue
    t=resp[0]["teams"]
    h_api=t["home"]["id"]; a_api=t["away"]["id"]
    h_name=t["home"]["name"]; a_name=t["away"]["name"]
    h=tmap.get(h_api); a=tmap.get(a_api)
    ok = bool(h and a)
    print(f"  p{pid} fix={fix}: API {h_name}({h_api}) vs {a_name}({a_api}) -> "
          f"{'local='+str(h[0])+' visit='+str(a[0]) if ok else 'SIN MAPEO ('+('h?' if not h else '')+('a?' if not a else '')+')'}")
    if ok: plan.append((pid,h[0],a[0]))

if not APPLY:
    print("\n== DRY-RUN (agrega --apply) ==")
    cur.close(); conn.close(); sys.exit(0)

for pid,h,a in plan:
    cur.execute("UPDATE partido SET equipo_local_id=%s, equipo_visitante_id=%s WHERE id=%s",(h,a,pid))
conn.commit()
print(f"\n== COMMIT ok: {len(plan)} partidos actualizados ==")
cur.close(); conn.close()
