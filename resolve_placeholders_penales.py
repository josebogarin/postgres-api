# -*- coding: utf-8 -*-
"""
resolve_placeholders_penales.py - Resuelve los octavos que quedaron con placeholder
'Gan. A/B' porque su llave del R32 se definio por PENALES. Trae la tanda desde
API-Football (score.penalty), la guarda en la vuelta, calcula el ganador
(diferencia de goles global; si empata, penales) y reemplaza el placeholder en
los octavos por el equipo ganador.

Uso:  python resolve_placeholders_penales.py [torneo_id]           (DRY-RUN)
      python resolve_placeholders_penales.py [torneo_id] --apply
Default torneo_id=14 (Sudamericana).
"""
import sys, os, json, unicodedata, urllib.request, psycopg2

args=[a for a in sys.argv[1:] if a!="--apply"]
APPLY="--apply" in sys.argv
nums=[a for a in args if a.isdigit()]
TID=int(nums[0]) if nums else 14
# overrides manuales:  "Nacional/Tigre=Tigre:5-4"  (ganador:score ganador-perdedor)
OVR={}
for a in args:
    if "=" in a:
        k,v=a.split("=",1); OVR[k.strip().lower()]=v.strip()

_ROOT=os.path.dirname(os.path.abspath(__file__))
KEY=None
for ln in open(os.path.join(_ROOT,"backend",".env"),encoding="utf-8"):
    if ln.strip().startswith("APIFOOTBALL_KEY"): KEY=ln.split("=",1)[1].strip().strip('"').strip("'"); break
API="https://v3.football.api-sports.io"; HDR={"x-rapidapi-key":KEY,"x-rapidapi-host":"v3.football.api-sports.io"}
def api_fix(fid):
    with urllib.request.urlopen(urllib.request.Request(f"{API}/fixtures?id={fid}",headers=HDR),timeout=30) as r:
        return json.loads(r.read().decode()).get("response",[])
def norm(s):
    return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()

conn=psycopg2.connect(host="localhost",port=5432,dbname="becbuc",user="app_user",password="superpassword")
cur=conn.cursor()
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'",(TID,)); oct_fase=cur.fetchone()[0]
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32'",(TID,)); r32_fase=cur.fetchone()[0]

# placeholders 'Gan. A/B' aun presentes en octavos
cur.execute("""SELECT DISTINCT e.id, e.nombre FROM partido p
               JOIN equipo e ON e.id IN (p.equipo_local_id,p.equipo_visitante_id)
               WHERE p.fase_id=%s AND e.nombre ILIKE 'Gan.%%/%%'""",(oct_fase,))
phs=cur.fetchall()
print(f"Placeholders sin resolver en octavos: {[n for _,n in phs]}\n")

# llaves R32
cur.execute("""SELECT p.id,p.equipo_local_id,el.nombre,p.equipo_visitante_id,ev.nombre,
                      p.goles_local,p.goles_visitante,p.penales_local,p.penales_visitante,
                      p.api_fixture_id,p.fecha
               FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                              JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s ORDER BY p.fecha,p.id""",(r32_fase,))
legs=cur.fetchall()
ties={}
for L in legs: ties.setdefault(frozenset((L[1],L[3])),[]).append(L)

acciones=[]
for ph_id,ph_nombre in phs:
    body=ph_nombre.split("Gan.",1)[1].strip()
    toks=[norm(t) for t in body.split("/")]
    toks=[max(t.split(),key=len) if t.split() else t for t in toks]  # palabra mas larga
    tie=None
    for key,ls in ties.items():
        nm=[norm(ls[0][2]),norm(ls[0][4])]
        if all(any(tk in n for n in nm) for tk in toks): tie=ls; break
    if not tie:
        print(f"  {ph_nombre}: no encontre la llave R32"); continue
    vue=max(tie,key=lambda x:(x[10] or __import__('datetime').datetime.min))  # ultima fecha = vuelta
    agg={}
    for x in tie:
        agg[x[1]]=agg.get(x[1],0)+(x[5] or 0); agg[x[3]]=agg.get(x[3],0)+(x[6] or 0)
    a,b=list(agg.keys())
    pen_l,pen_v=vue[7],vue[8]
    fetched=None
    # ---- override manual (ganador + score) ----
    ov=OVR.get(body.lower()) or OVR.get(norm(body))
    if ov:
        wn_txt, _, sc = ov.partition(":")
        wn_txt_n=norm(wn_txt)
        # ubicar equipo ganador entre los 2 de la llave
        cur.execute("SELECT id,nombre FROM equipo WHERE id IN (%s,%s)",(a,b))
        eqs={norm(nm):eid for eid,nm in cur.fetchall()}
        win_ov=next((eid for k2,eid in eqs.items() if wn_txt_n in k2 or k2 in wn_txt_n),None)
        if win_ov:
            pw,pl=(sc.split("-")+["",""])[:2] if "-" in sc else ("","")
            try: pw=int(pw); pl=int(pl)
            except: pw=pl=None
            if pw is not None:
                # orientar a local/visitante de la vuelta
                if vue[1]==win_ov: pen_l,pen_v=pw,pl
                else: pen_l,pen_v=pl,pw
            cur.execute("SELECT nombre FROM equipo WHERE id=%s",(win_ov,)); wn=cur.fetchone()[0]
            print(f"  {ph_nombre}: MANUAL -> pasa {wn} (tanda {pen_l}-{pen_v})")
            acciones.append((ph_id,ph_nombre,win_ov,wn,vue[0],pen_l,pen_v,(pen_l,pen_v)))
            continue
    if agg[a]==agg[b] and (pen_l is None or pen_v is None):
        # traer tanda de la API
        try:
            resp=api_fix(vue[9])
            if resp:
                fx=resp[0]
                print(f"    API fix {vue[9]}: {fx['teams']['home']['name']} vs {fx['teams']['away']['name']}"
                      f" | status={fx['fixture']['status']['short']}"
                      f" | FT={fx['score'].get('fulltime')} ET={fx['score'].get('extratime')} PEN={fx['score'].get('penalty')}")
                sc=fx["score"].get("penalty") or {}
                pen_l,pen_v=sc.get("home"),sc.get("away"); fetched=(pen_l,pen_v)
            else:
                print(f"    API fix {vue[9]}: sin respuesta")
        except Exception as e:
            print(f"  {ph_nombre}: error API tanda: {e}")
    # ganador
    if agg[a]>agg[b]: win=a
    elif agg[b]>agg[a]: win=b
    elif pen_l is not None and pen_v is not None and pen_l!=pen_v:
        win = vue[1] if pen_l>pen_v else vue[3]
    else:
        print(f"  {ph_nombre}: global {agg[a]}-{agg[b]}, tanda={pen_l}-{pen_v} -> AUN INDEFINIDO"); continue
    cur.execute("SELECT nombre FROM equipo WHERE id=%s",(win,)); wn=cur.fetchone()[0]
    print(f"  {ph_nombre}: vuelta p{vue[0]} tanda {pen_l}-{pen_v}{' (API)' if fetched else ''} -> pasa {wn}")
    acciones.append((ph_id,ph_nombre,win,wn,vue[0],pen_l,pen_v,fetched))

if not APPLY:
    print("\n== DRY-RUN (agrega --apply) =="); cur.close(); conn.close(); sys.exit(0)

for ph_id,ph_nombre,win,wn,vue_pid,pen_l,pen_v,fetched in acciones:
    if fetched and pen_l is not None and pen_v is not None:
        cur.execute("UPDATE partido SET penales_local=%s, penales_visitante=%s WHERE id=%s",(pen_l,pen_v,vue_pid))
    cur.execute("UPDATE partido SET equipo_local_id=%s WHERE fase_id=%s AND equipo_local_id=%s",(win,oct_fase,ph_id))
    cur.execute("UPDATE partido SET equipo_visitante_id=%s WHERE fase_id=%s AND equipo_visitante_id=%s",(win,oct_fase,ph_id))
    print(f"  resuelto {ph_nombre} -> {wn}")
conn.commit(); print("\n== COMMIT ok =="); cur.close(); conn.close()
