# -*- coding: utf-8 -*-
"""
estado_semis_bracket.py  (solo lectura)
Muestra el estado de Semis (P101-P102), 3er puesto (P103) y Final (P104):
equipos, marcador, estado, api_fixture_id (mapeo API), clasificado, blindado.
No modifica nada. Sirve para decidir como terminar las semis + avanzar bracket.
"""
import sys, os
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

TORNEO_ID = 2
CONN_BEC  = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

conn = psycopg2.connect(CONN_BEC)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 66)
print("BECBUC - Estado Semis / 3er puesto / Final")
print("=" * 66)

# Estado de fases KO finales
cur.execute("""
    SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
    FROM fase WHERE torneo_id=%s
      AND (tipo ILIKE '%%semi%%' OR tipo ILIKE '%%tercer%%' OR tipo ILIKE '%%final%%'
           OR nombre ILIKE '%%semi%%' OR nombre ILIKE '%%tercer%%' OR nombre ILIKE '%%final%%')
    ORDER BY id
""", (TORNEO_ID,))
print("\nFases finales:")
for f in cur.fetchall():
    print(f"  id={f['id']:>3} tipo={f['tipo']:<16} '{f['nombre']}'  bloqueada={f['bloqueada']}")

# Partidos P101-P104
cur.execute("""
    SELECT p.numero_fifa,
           el.nombre AS local, p.goles_local,
           p.goles_visitante, ev.nombre AS visitante,
           p.estado,
           p.api_fixture_id,
           COALESCE(p.datos_confirmados, FALSE) AS blindado,
           COALESCE(ec.nombre, 'sin definir') AS clasificado,
           p.penales_local, p.penales_visitante,
           p.fecha
    FROM partido p
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
    WHERE p.torneo_id=%s AND p.numero_fifa = ANY(%s)
    ORDER BY p.numero_fifa
""", (TORNEO_ID, [101, 102, 103, 104]))
print("\nPartidos:")
for p in cur.fetchall():
    fx = p['api_fixture_id'] if p['api_fixture_id'] is not None else 'sin mapear'
    tanda = ""
    if p['penales_local'] is not None or p['penales_visitante'] is not None:
        tanda = f" (tanda {p['penales_local']}-{p['penales_visitante']})"
    print(f"  P{p['numero_fifa']:03d}: {p['local']:<22} {p['goles_local']}-{p['goles_visitante']} "
          f"{p['visitante']:<22}{tanda}")
    print(f"        estado={p['estado']:<12} api_fixture={fx:<12} blindado={'SI' if p['blindado'] else 'no'}"
          f"  Clasifica: {p['clasificado']}  fecha={p['fecha']}")

conn.close()
print("\n(solo lectura - no se modifico nada)")
