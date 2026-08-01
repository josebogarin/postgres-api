# -*- coding: utf-8 -*-
"""
corregir_llave_ganador.py - Corrige el ganador YA resuelto de una llave de clubes
(reemplaza el equipo equivocado por el correcto en los octavos, y ajusta la tanda
de penales de la vuelta del R32).

Uso:  python corregir_llave_ganador.py <torneo_id> "EquipoMal>EquipoCorrecto:W-L" [--apply]
Ej:   python corregir_llave_ganador.py 14 "Bolivar>Gremio:3-2"
"""
import sys, unicodedata, psycopg2
args=[a for a in sys.argv[1:] if a!="--apply"]
APPLY="--apply" in sys.argv
TID=int(args[0]); SPEC=args[1]
def norm(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower().strip()

lhs,_,score=SPEC.partition(":")
mal,_,bien=lhs.partition(">")
pw,pl=(score.split("-")+["",""])[:2]
try: pw,pl=int(pw),int(pl)
except: pw=pl=None

conn=psycopg2.connect(host="localhost",port=5432,dbname="becbuc",user="app_user",password="superpassword")
cur=conn.cursor()
def eqid(n):
    nn=norm(n)
    cur.execute("SELECT id,nombre,nombre_es FROM equipo")
    rows=cur.fetchall()
    for eid,nm,nes in rows:
        if norm(nm)==nn or norm(nes or "")==nn: return (eid,nm)
    cand=[(eid,nm) for eid,nm,nes in rows if nn and (nn in norm(nm) or (nes and nn in norm(nes)))]
    return cand[0] if cand else (None,None)
mal_id,mal_nm=eqid(mal); bien_id,bien_nm=eqid(bien)
print(f"Reemplazar en octavos: {mal_nm}(id={mal_id}) -> {bien_nm}(id={bien_id})")
if not mal_id or not bien_id: print("Falta equipo, abortando."); sys.exit(1)

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'",(TID,)); oct_f=cur.fetchone()[0]
cur.execute("""SELECT p.id, el.nombre, ev.nombre FROM partido p
               JOIN equipo el ON el.id=p.equipo_local_id JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s AND (%s IN (p.equipo_local_id,p.equipo_visitante_id))""",(oct_f,mal_id))
octs=cur.fetchall()
print("Octavos afectados:")
for pid,ln,vn in octs: print(f"  p{pid}: {ln} vs {vn}")

# R32 vuelta de la llave (bien vs mal): setear tanda para que 'bien' gane
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32'",(TID,)); r32=cur.fetchone()[0]
cur.execute("""SELECT id,equipo_local_id,equipo_visitante_id,fecha,penales_local,penales_visitante
               FROM partido WHERE fase_id=%s AND equipo_local_id IN (%s,%s) AND equipo_visitante_id IN (%s,%s)
               ORDER BY fecha""",(r32,mal_id,bien_id,mal_id,bien_id))
legs=cur.fetchall()
vue=legs[-1] if legs else None
if vue and pw is not None:
    if vue[1]==bien_id: nl,nv=pw,pl
    else: nl,nv=pl,pw
    print(f"Vuelta R32 p{vue[0]}: tanda -> {nl}-{nv} (gana {bien_nm})")
else:
    nl=nv=None; print("Sin vuelta R32 o sin score; solo se cambia el octavo.")

if not APPLY:
    print("\n== DRY-RUN (agrega --apply) =="); sys.exit(0)

cur.execute("UPDATE partido SET equipo_local_id=%s WHERE fase_id=%s AND equipo_local_id=%s",(bien_id,oct_f,mal_id))
cur.execute("UPDATE partido SET equipo_visitante_id=%s WHERE fase_id=%s AND equipo_visitante_id=%s",(bien_id,oct_f,mal_id))
if vue and nl is not None:
    cur.execute("UPDATE partido SET penales_local=%s,penales_visitante=%s WHERE id=%s",(nl,nv,vue[0]))
conn.commit(); print("\n== COMMIT ok ==")
cur.close(); conn.close()
