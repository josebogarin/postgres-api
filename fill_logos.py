# -*- coding: utf-8 -*-
"""
fill_logos.py - Importa el escudo (logo_url) desde API-Football para los equipos
de un torneo que no lo tengan. Usa api_team_id si esta mapeado; si no, busca por nombre.

Uso:  python fill_logos.py [torneo_id]            (DRY-RUN)
      python fill_logos.py [torneo_id] --apply
Default torneo_id=14.
"""
import sys, os, json, unicodedata, urllib.request, urllib.parse, psycopg2
args=[a for a in sys.argv[1:] if a!="--apply"]; APPLY="--apply" in sys.argv
TID=int(args[0]) if args else 14
_ROOT=os.path.dirname(os.path.abspath(__file__)); KEY=None
for ln in open(os.path.join(_ROOT,"backend",".env"),encoding="utf-8"):
    if ln.strip().startswith("APIFOOTBALL_KEY"): KEY=ln.split("=",1)[1].strip().strip('"').strip("'"); break
API="https://v3.football.api-sports.io"; HDR={"x-rapidapi-key":KEY,"x-rapidapi-host":"v3.football.api-sports.io"}
def apiget(path):
    with urllib.request.urlopen(urllib.request.Request(API+path,headers=HDR),timeout=30) as r:
        return json.loads(r.read().decode()).get("response",[])
def norm(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower().strip()

# alias: nombre en BD (normalizado) -> termino de busqueda en API-Football
ALIASES={"universidad central":"UCV"}

conn=psycopg2.connect(host="localhost",port=5432,dbname="becbuc",user="app_user",password="superpassword")
cur=conn.cursor()
cur.execute("""SELECT DISTINCT e.id,e.nombre,e.api_team_id,e.logo_url
               FROM equipo e JOIN partido p ON e.id IN (p.equipo_local_id,p.equipo_visitante_id)
               WHERE p.torneo_id=%s AND (e.logo_url IS NULL OR e.logo_url='')
                 AND e.nombre NOT ILIKE 'Gan.%%' AND LOWER(e.nombre) NOT IN ('tbd','por definir')
               ORDER BY e.nombre""",(TID,))
faltan=cur.fetchall()
print(f"Equipos del torneo {TID} sin escudo: {len(faltan)}\n")
plan=[]
for eid,nombre,ateam,logo in faltan:
    url=None; via=None; nn=norm(nombre)
    try:
        if ateam:
            r=apiget(f"/teams?id={ateam}")
            if r: url=r[0]["team"].get("logo"); via=f"id={ateam}"
        if not url and ALIASES.get(nn):
            r=apiget("/teams?search="+urllib.parse.quote(ALIASES[nn]))
            if r: url=r[0]["team"].get("logo"); via=f"alias '{ALIASES[nn]}'->'{r[0]['team']['name']}'"
        if not url:
            ws=nombre.split()
            terms=[nombre]
            if len(ws)>=2: terms.append(" ".join(ws[-2:]))   # ultimas 2 palabras
            if len(ws)>=2: terms.append(" ".join(ws[:2]))    # primeras 2 palabras
            for term in terms:
                if len(norm(term))<3: continue
                r=apiget("/teams?search="+urllib.parse.quote(term))
                if not r: continue
                best=next((t for t in r if norm(t["team"]["name"])==nn), None)
                if not best:
                    best=next((t for t in r if len(norm(t["team"]["name"]))>=6
                               and (nn in norm(t["team"]["name"]) or norm(t["team"]["name"]) in nn)), None)
                if best: url=best["team"].get("logo"); via=f"search '{term}'->'{best['team']['name']}'"; break
        if not url:
            # copiar de un duplicado en BD que ya tenga escudo
            cur.execute("SELECT nombre,logo_url FROM equipo WHERE logo_url IS NOT NULL AND logo_url<>''")
            for onm,olog in cur.fetchall():
                n2=norm(onm)
                if n2 and n2!="" and (n2==nn or (len(n2)>=6 and (n2 in nn or nn in n2))):
                    url=olog; via=f"copia de '{onm}'"; break
    except Exception as e:
        print(f"  {nombre}: error API {e}"); continue
    print(f"  {nombre} (id={eid}): {url or 'SIN LOGO'}   [{via or '-'}]")
    if url: plan.append((eid,url))

if not APPLY:
    print("\n== DRY-RUN (agrega --apply) =="); sys.exit(0)
for eid,url in plan:
    cur.execute("UPDATE equipo SET logo_url=%s WHERE id=%s",(url,eid))
conn.commit(); print(f"\n== COMMIT ok: {len(plan)} escudos importados ==")
cur.close(); conn.close()
