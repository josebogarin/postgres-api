# -*- coding: utf-8 -*-
"""
estado_fases.py  (solo lectura)
Muestra el estado de bloqueo de cada fase del torneo 2 y si sus partidos estan
finalizados. Sirve para saber que apuestas se pueden editar todavia.
"""
import psycopg2, psycopg2.extras
CONN="host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TID=2
c=psycopg2.connect(CONN); cur=c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
  SELECT f.id, f.tipo, f.nombre, COALESCE(f.bloqueada,FALSE) AS bloq,
         COUNT(p.id) AS parts,
         COUNT(p.id) FILTER (WHERE p.estado='finalizado') AS fin,
         COUNT(p.id) FILTER (WHERE p.estado='programado')  AS prog
  FROM fase f LEFT JOIN partido p ON p.fase_id=f.id
  WHERE f.torneo_id=%s
  GROUP BY f.id, f.tipo, f.nombre, f.bloqueada
  ORDER BY MIN(p.numero_fifa) NULLS LAST, f.id
""",(TID,))
print("="*78)
print("ESTADO DE FASES (torneo 2)")
print("="*78)
print(f"{'id':>4}  {'tipo':<14}{'nombre':<26}{'BLOQ':>6}{'part':>6}{'fin':>5}{'prog':>6}   EDITABLE?")
for r in cur.fetchall():
    editable = (not r['bloq']) and (r['prog']>0)
    et = 'SI (hay programados)' if editable else ('no (bloqueada)' if r['bloq'] else 'no (sin programados)')
    print(f"{r['id']:>4}  {r['tipo']:<14}{(r['nombre'] or '')[:24]:<26}{('SI' if r['bloq'] else 'no'):>6}{r['parts']:>6}{r['fin']:>5}{r['prog']:>6}   {et}")
c.close()
