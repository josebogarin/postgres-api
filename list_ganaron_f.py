# -*- coding: utf-8 -*-
"""list_ganaron_f.py — lista (solo lectura) los apostadores que cobran el item F
(Etapa Paraguay = 6 pts) tras el fix: los que pusieron octavos ('8vos')."""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

TID = 2
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")

def p(*a): print(*a); sys.stdout.flush()

becbuc = psycopg2.connect(dbname="becbuc", **DB)
appdb  = psycopg2.connect(dbname="app_db", **DB)
bc = becbuc.cursor(cursor_factory=RealDictCursor)
ac = appdb.cursor(cursor_factory=RealDictCursor)

ac.execute("SELECT id, username FROM users")
umap = {r["id"]: r["username"] for r in ac.fetchall()}

bc.execute(f"""
    SELECT ag.apostador_id AS uid, ag.pred_etapa_paraguay AS pe,
           pg.pts_etapa_paraguay AS pts, pg.pts_total AS glob_total
    FROM apuesta_global ag
    JOIN puntaje_global pg
      ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
    WHERE ag.torneo_id={TID} AND COALESCE(pg.pts_etapa_paraguay,0)=6
    ORDER BY LOWER(COALESCE(NULL,''))  -- placeholder
""")
rows = bc.fetchall()
rows.sort(key=lambda r: (umap.get(r["uid"]) or "").lower())

p("=" * 60)
p(" GANARON 6 pts en item F (Etapa Paraguay) tras el fix")
p(" (pusieron octavos = '8vos', la fase real de eliminacion)")
p("=" * 60)
p(f"{'#':>2}  {'alias':<22} {'pred':<8} {'pts_F':>5}")
for i, r in enumerate(rows, 1):
    alias = umap.get(r["uid"]) or f"U{r['uid']}"
    p(f"{i:>2}  {alias:<22} {str(r['pe']):<8} {r['pts']:>5}")
p("-" * 60)
p(f"TOTAL: {len(rows)} apostadores cobran el item F (+6 pts c/u).")
p("=" * 60)

bc.close(); ac.close(); becbuc.close(); appdb.close()
