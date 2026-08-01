# -*- coding: utf-8 -*-
"""
set_fecha_partido.py — Setea la fecha/hora de UN partido a mano, en HORA DE
PARAGUAY (UTC-3 fijo). La guarda en UTC (que es como el Live la lee y reconvierte).

Util cuando la hora que trae API-Football es un placeholder (ej. los octavos de
Sudamericana venian todos 20:00 UTC) y hay que poner la hora real del fixture.

Uso (hora de Paraguay):
  python set_fecha_partido.py <partido_id> <YYYY-MM-DD> <HH:MM>
Ejemplo (Vasco-Olimpia 12/08 19:00 Paraguay):
  python set_fecha_partido.py 3590 2026-08-12 19:00
"""
import sys
from datetime import datetime, timedelta
import psycopg2

if len(sys.argv) < 4:
    print("Uso: python set_fecha_partido.py <partido_id> <YYYY-MM-DD> <HH:MM>  (hora Paraguay)")
    sys.exit(1)

pid = int(sys.argv[1])
try:
    local = datetime.strptime(sys.argv[2] + " " + sys.argv[3], "%Y-%m-%d %H:%M")
except ValueError:
    print("Formato invalido. Fecha=YYYY-MM-DD  Hora=HH:MM (24h). Ej: 2026-08-12 19:00")
    sys.exit(1)

# Paraguay = UTC-3 fijo  ->  UTC = hora local + 3
utc = local + timedelta(hours=3)

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()
cur.execute("""
    SELECT p.fecha, COALESCE(el.nombre_es, el.nombre), COALESCE(ev.nombre_es, ev.nombre)
    FROM partido p
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE p.id = %s
""", (pid,))
row = cur.fetchone()
if not row:
    print(f"No existe el partido id={pid}")
    sys.exit(1)
old, ln, vn = row
print(f"P{pid}: {ln} vs {vn}")
print(f"  antes:  {old} UTC")
print(f"  nuevo:  {utc} UTC   ( = {local.strftime('%Y-%m-%d %H:%M')} hora Paraguay )")

cur.execute("UPDATE partido SET fecha = %s WHERE id = %s", (utc, pid))
conn.commit()
print("OK: fecha actualizada.")
