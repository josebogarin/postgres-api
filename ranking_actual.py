# -*- coding: utf-8 -*-
"""
ranking_actual.py
Muestra el ranking ACTUAL (top 20) leyendo directo de la BD, igual que el portal:
  puntos_total = SUM(puntaje_detalle items) + globales(puntaje_global) + P de grupos(apostador_clasificados)
Solo lectura.
"""
import sys
try:
    import psycopg2, psycopg2.extras
except ImportError:
    import os; os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
TID = 2
cb = psycopg2.connect(BEC); ca = psycopg2.connect(APP)
cur = cb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cua = ca.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1) puntos de partidos (suma de items en puntaje_detalle)
cur.execute("""
    SELECT pd.apostador_id,
           SUM(COALESCE(pd.pts_resultado,0)+COALESCE(pd.pts_marcador,0)+COALESCE(pd.pts_amarillas,0)
              +COALESCE(pd.pts_rojas,0)+COALESCE(pd.pts_var,0)+COALESCE(pd.pts_penales_partido,0)
              +COALESCE(pd.pts_minuto,0)+COALESCE(pd.pts_penales_tanda,0)+COALESCE(pd.pts_equipo,0))::int AS pts_part
    FROM puntaje_detalle pd JOIN partido p ON p.id=pd.partido_id JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=%s
    GROUP BY pd.apostador_id
""", (TID,))
part = {r['apostador_id']: r['pts_part'] for r in cur.fetchall()}

# 2) globales (probar nombre de columna total)
glob = {}
for col in ('pts_total','puntos_total'):
    try:
        cur.execute(f"SELECT apostador_id, COALESCE({col},0) AS g FROM puntaje_global WHERE torneo_id=%s", (TID,))
        glob = {r['apostador_id']: r['g'] for r in cur.fetchall()}
        break
    except Exception:
        cb.rollback()

# 3) P de grupos (clasificados acertados)
grp = {}
try:
    cur.execute("""
        SELECT apostador_id, COALESCE(SUM(aciertos),0)::int AS g
        FROM apostador_clasificados WHERE torneo_id=%s AND fase_tipo='grupo' GROUP BY apostador_id
    """, (TID,))
    grp = {r['apostador_id']: r['g'] for r in cur.fetchall()}
except Exception:
    cb.rollback()

# usernames
cua.execute("SELECT id, username FROM users")
un = {r['id']: r['username'] for r in cua.fetchall()}

filas = []
for uid in set(list(part)+list(glob)+list(grp)):
    pp = part.get(uid,0); gg = glob.get(uid,0); gp = grp.get(uid,0)
    filas.append((un.get(uid, f'U{uid}'), pp+gg+gp, pp, gg, gp))
filas.sort(key=lambda x:-x[1])

print("="*66)
print("RANKING ACTUAL (top 20)  [suma directa de puntaje_detalle + globales + P grupos]")
print("="*66)
print("(P-clasif grupos = item P de grupos: equipos que clasifican a 16avos, 1 pt c/u)")
print(f"{'#':>3}  {'APOSTADOR':<22}{'TOTAL':>7}{'partidos':>10}{'glob':>6}{'P-clasif':>10}")
for i,(u,t,pp,gg,gp) in enumerate(filas[:20],1):
    print(f"{i:>3}  {u:<22}{t:>7}{pp:>10}{gg:>6}{gp:>10}")
cb.close(); ca.close()
