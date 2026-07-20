# -*- coding: utf-8 -*-
"""
verificar_usuario_sandra.py
Lista usuarios (app_db) que matchean sandra/biedermann/pato para confirmar
el username correcto antes de hacer el swap de octavos.
Muestra tambien cuantas apuestas de octavos (P089-P096) tiene cada uno.
"""
import sys, os
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN_APP = "host=localhost port=5432 dbname=app_db user=app_user password=superpassword"
CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TORNEO_ID = 2

app = psycopg2.connect(CONN_APP); bec = psycopg2.connect(CONN_BEC)
ca = app.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cb = bec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

ca.execute("""
    SELECT id, username, COALESCE(nombre,'') AS nombre, is_active
    FROM users
    WHERE nombre ILIKE '%sandra%' OR nombre ILIKE '%biederman%'
       OR nombre ILIKE '%hugo%'   OR nombre ILIKE '%sonia%'
       OR username ILIKE '%san%'  OR username ILIKE '%pato%' OR username ILIKE '%soni%'
    ORDER BY nombre
""")
rows = ca.fetchall()
print(f"{'id':<6}{'username':<16}{'nombre':<30}{'activo':<8}{'apuestas_octavos'}")
for r in rows:
    cb.execute("""
        SELECT COUNT(*) AS n FROM apuesta a JOIN partido p ON p.id=a.partido_id
        JOIN fase f ON f.id=p.fase_id
        WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN 89 AND 96 AND a.apostador_id=%s
    """, (TORNEO_ID, r['id']))
    n = cb.fetchone()['n']
    print(f"{r['id']:<6}{r['username']:<16}{r['nombre']:<30}{str(r['is_active']):<8}{n}")

app.close(); bec.close()
