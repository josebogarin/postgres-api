"""
diag_sudamericana.py - Vuelca el estado del bracket de Libertadores (torneo 1)
para ver que quedo despues del sync (octavos/Olimpia, R32, placeholders 'Gan.').
Solo lectura.
"""
import psycopg2

TID = 1
conn = psycopg2.connect(host='localhost', port=5432, dbname='becbuc',
                        user='app_user', password='superpassword')
cur = conn.cursor()

print("=== FASES torneo 14 ===")
cur.execute("""SELECT id,nombre,tipo,orden,COALESCE(bloqueada,false)
               FROM fase WHERE torneo_id=%s ORDER BY orden,id""", (TID,))
for r in cur.fetchall():
    print(f"  fase {r[0]:>4} | {r[2]:<12} orden={r[3]:<4} bloqueada={r[4]} | {r[1]}")

print("\n=== PARTIDOS torneo 14 (por fase) ===")
cur.execute("""
  SELECT f.tipo, f.orden, p.id, p.numero_fifa,
         el.nombre AS local, ev.nombre AS visit,
         p.estado, p.goles_local, p.goles_visitante,
         p.api_fixture_id, p.equipo_clasificado_id, p.fecha
  FROM partido p
  JOIN fase f ON f.id=p.fase_id
  JOIN equipo el ON el.id=p.equipo_local_id
  JOIN equipo ev ON ev.id=p.equipo_visitante_id
  WHERE p.torneo_id=%s
  ORDER BY f.orden, p.numero_fifa NULLS LAST, p.id
""", (TID,))
cur_fase=None
for r in cur.fetchall():
    tipo,orden,pid,nf,loc,vis,est,gl,gv,fix,clasif,fecha = r
    if tipo!=cur_fase:
        cur_fase=tipo; print(f"\n  --- {tipo} (orden {orden}) ---")
    marc = f"{gl}-{gv}" if gl is not None else "  -  "
    print(f"    p{pid:>4} n{str(nf):>4} | {loc:<24} {marc} {vis:<24} | {est:<11} fix={str(fix):>8} clasif={clasif} | {fecha}")

print("\n=== equipos clave (Olimpia / Vasco / Medellin / placeholders 'Gan.'/'Por Definir') ===")
cur.execute("""SELECT id,nombre FROM equipo
               WHERE nombre ILIKE '%olimpia%' OR nombre ILIKE '%vasco%'
                  OR nombre ILIKE '%medellin%' OR nombre ILIKE '%medellín%'
                  OR nombre ILIKE 'Gan.%' OR nombre ILIKE '%Por Definir%'
               ORDER BY nombre""")
for r in cur.fetchall():
    print(f"  equipo {r[0]:>4} | {r[1]}")

cur.close(); conn.close()
