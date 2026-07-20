# -*- coding: utf-8 -*-
"""
verificar_item_p.py
Verifica que el item P (equipo que pasa/clasifica) haya quedado calculado.
Por cada fase KO muestra: partidos totales, cuantos tienen equipo_clasificado_id
cargado, y el total de pts_equipo otorgado (+ apostadores con P>0).
Para grupos muestra el P de clasificados (apostador_clasificados / pts_grupos_p).
Solo lectura.
"""
import psycopg2, psycopg2.extras
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TID = 2
conn = psycopg2.connect(CONN); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

FASES = [('ronda32','16avos'),('ronda16','octavos'),('cuartos','cuartos'),('semis','semis')]

print("="*70)
print("VERIFICACION ITEM P (equipo que pasa) por fase")
print("="*70)
for tipo, etq in FASES:
    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(p.equipo_clasificado_id) AS con_clasif,
               COUNT(*) FILTER (WHERE p.estado='finalizado') AS finalizados
        FROM partido p JOIN fase f ON f.id=p.fase_id
        WHERE f.torneo_id=%s AND lower(f.tipo)=%s
    """, (TID, tipo))
    pr = cur.fetchone()
    cur.execute("""
        SELECT COALESCE(SUM(pd.pts_equipo),0) AS suma_p,
               COUNT(DISTINCT pd.apostador_id) FILTER (WHERE pd.pts_equipo>0) AS aps_con_p
        FROM puntaje_detalle pd
        JOIN partido p ON p.id=pd.partido_id
        JOIN fase f ON f.id=p.fase_id
        WHERE f.torneo_id=%s AND lower(f.tipo)=%s
    """, (TID, tipo))
    sc = cur.fetchone()
    print(f"\n[{etq}]  partidos={pr['total']} finalizados={pr['finalizados']} "
          f"con equipo_clasificado_id={pr['con_clasif']}")
    print(f"        pts_equipo total={sc['suma_p']}  apostadores con P>0={sc['aps_con_p']}")
    if pr['finalizados'] and pr['con_clasif'] < pr['finalizados']:
        print(f"        ! OJO: {pr['finalizados']-pr['con_clasif']} partido(s) finalizado(s) SIN equipo_clasificado_id -> P=0 ahi")

# Grupos: P por clasificados
cur.execute("""
    SELECT COALESCE(SUM(pts),0) AS suma, COUNT(*) FILTER (WHERE pts>0) AS aps
    FROM (
        SELECT apostador_id, COALESCE(SUM(aciertos),0) AS pts
        FROM apostador_clasificados
        WHERE torneo_id=%s AND fase_tipo='grupo'
        GROUP BY apostador_id
    ) t
""", (TID,))
try:
    g = cur.fetchone()
    print(f"\n[grupos]  P clasificados (apostador_clasificados): filas con datos "
          f"-> apostadores={g['aps']}")
except Exception as e:
    print(f"\n[grupos]  no se pudo leer apostador_clasificados: {e}")

# Muestra los equipos que pasan segun BD (KO)
print("\n" + "-"*70)
print("Equipo que pasa (equipo_clasificado_id) por partido KO en BD:")
cur.execute("""
    SELECT p.numero_fifa, el.nombre AS local, ev.nombre AS visit,
           p.goles_local, p.goles_visitante, ec.nombre AS pasa, p.estado
    FROM partido p JOIN fase f ON f.id=p.fase_id
    LEFT JOIN equipo el ON el.id=p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id=p.equipo_clasificado_id
    WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN 73 AND 102
    ORDER BY p.numero_fifa
""", (TID,))
for r in cur.fetchall():
    pasa = r['pasa'] or 'NULL (P=0)'
    print(f"  P{r['numero_fifa']:03d} {r['local']} {r['goles_local']}-{r['goles_visitante']} {r['visit']}"
          f"  -> pasa: {pasa}  [{r['estado']}]")
conn.close()
