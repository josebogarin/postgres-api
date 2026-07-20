# -*- coding: utf-8 -*-
"""analisis_datos.py -- SOLO LECTURA. Extrae datos para el analisis del sistema de puntajes."""
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

API_BASE="http://localhost:8000/api/v1"; TID=2
CONN="host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
conn=psycopg2.connect(CONN); conn.autocommit=True
cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# --- Ranking completo via API ---
tok=requests.post(f"{API_BASE}/auth/login",json={"username":"jose","password":"catalina"},timeout=30).json().get("access_token","")
hdr={"Authorization":f"Bearer {tok}"}
rj=requests.get(f"{API_BASE}/bets/ranking/{TID}",headers=hdr,timeout=60).json()
rows=rj.get("ranking",[]) if isinstance(rj,dict) else rj
print("=== RANKING COMPLETO (todos) ===")
print("pos;alias;total;partidos;globales")
vals=[]
for i,ap in enumerate(rows,1):
    nm=ap.get('apostador') or ap.get('username') or '?'
    tot=ap.get('puntos_total',0); part=ap.get('puntos_partidos_total',0); glob=ap.get('pts_globales',0)
    vals.append(tot)
    print(f"{i};{nm};{tot};{part};{glob}")

if vals:
    n=len(vals); mx=max(vals); mn=min(vals); avg=sum(vals)/n
    srt=sorted(vals,reverse=True)
    mediana=srt[n//2]
    print(f"\n=== SPREAD ===")
    print(f"N={n}  1ro={mx}  ultimo={mn}  promedio={avg:.0f}  mediana={mediana}")
    print(f"gap 1ro-ultimo={mx-mn}  gap 1ro-2do={srt[0]-srt[1]}  gap 1ro-mediana={mx-mediana}")
    # gap por tramos
    print(f"top1={srt[0]} top5={srt[4] if n>4 else '-'} top10={srt[9] if n>9 else '-'} p25={srt[int(n*0.75)]} p50={mediana}")

# --- Suma por categoria de partido (puntaje_detalle) ---
print("\n=== PUNTOS TOTALES POR ITEM DE PARTIDO (suma de los 44) ===")
cur.execute("""SELECT
  SUM(pts_resultado) H_resultado, SUM(pts_marcador) I_marcador,
  SUM(pts_amarillas) J_amarillas, SUM(pts_rojas) K_rojas, SUM(pts_var) L_var,
  SUM(pts_penales_partido) M_pen_juego, SUM(pts_minuto) N_minuto,
  SUM(pts_penales_tanda) O_tanda, SUM(pts_equipo) P_clasifica
  FROM puntaje_detalle WHERE torneo_id=%s""",(TID,))
r=cur.fetchone()
for k,v in r.items(): print(f"  {k}: {v}")

# --- Suma por fase ---
print("\n=== PUNTOS POR FASE (suma de todos) ===")
cur.execute("""SELECT f.tipo, COUNT(DISTINCT p.id) partidos,
    SUM(pd.pts_resultado+pd.pts_marcador+pd.pts_amarillas+pd.pts_rojas+pd.pts_var+
        pd.pts_penales_partido+pd.pts_minuto+pd.pts_penales_tanda+pd.pts_equipo) total
  FROM puntaje_detalle pd JOIN partido p ON p.id=pd.partido_id JOIN fase f ON f.id=p.fase_id
  WHERE pd.torneo_id=%s GROUP BY f.tipo ORDER BY total DESC NULLS LAST""",(TID,))
for x in cur.fetchall(): print(f"  {x['tipo']:<16} partidos={x['partidos']:<4} total={x['total']}")

# --- Globales: suma por item ---
print("\n=== GLOBALES: suma total por item + cuantos sumaron ===")
cur.execute("""SELECT
  SUM(pts_campeon) A, SUM(pts_finalistas) B, SUM(pts_goleador) C, SUM(pts_peor_equipo) D,
  SUM(pts_mayor_goleada) E, SUM(pts_etapa_paraguay) F, SUM(pts_goles_paraguay) G
  FROM puntaje_global WHERE torneo_id=%s""",(TID,))
for k,v in cur.fetchone().items(): print(f"  {k}: {v}")

# --- Cuantos plenos/aciertos por apostador (distribucion) ---
print("\n=== DISTRIBUCION PLENOS (marcador exacto) por apostador ===")
cur.execute("""SELECT COUNT(*) FILTER (WHERE pts_marcador>0) plenos,
                      COUNT(*) FILTER (WHERE pts_resultado>0 AND pts_marcador=0) aciertos
               FROM puntaje_detalle WHERE torneo_id=%s AND apostador_id=(
                 SELECT apostador_id FROM puntaje_detalle WHERE torneo_id=%s
                 GROUP BY apostador_id ORDER BY SUM(pts_marcador) DESC LIMIT 1)""",(TID,TID))
print("  (referencia lider) ", dict(cur.fetchone()))

# valor promedio de un pleno vs acierto por fase (tabla oficial)
print("\n=== VALOR DE 1 ACIERTO/PLENO POR FASE (tabla oficial H/I) ===")
print("  grupos H=4 I=8 | 16avos 6/12 | octavos 8/16 | cuartos 10/20 | semis 12/24 | 3P 14/28 | final 20/40")

conn.close(); print("\n=== FIN ANALISIS DATOS ===")
