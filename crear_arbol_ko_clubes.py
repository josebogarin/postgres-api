# -*- coding: utf-8 -*-
"""
Crea el arbol KO encadenado hasta la FINAL para un torneo de clubes:
  Octavos (ya existe, 8 llaves) -> Cuartos (4) -> Semis (2) -> Final (1, partido unico).
Cada slot de la ronda siguiente es un placeholder "Gan. O{n}" / "Gan. C{n}" / "Gan. S{n}"
(ganador de la llave n de la ronda anterior) -> el cuadro queda encadenado por posicion.
La propagacion real (reemplazar el placeholder por el ganador) se hace cuando se juega.
Idempotente: no recrea una fase que ya tiene partidos.
Ejecutar:  python crear_arbol_ko_clubes.py <torneo_id> [--apply]
"""
import sys
import psycopg2

TORNEO_ID = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
APPLY = "--apply" in sys.argv

# (tipo, nombre, orden, n_llaves, ida_vuelta)
ROUNDS = [
    ("cuartos", "Cuartos de Final", 30, 4, True),
    ("semis",   "Semifinal",        40, 2, True),
    ("final",   "Final",            50, 1, False),
]

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

def get_or_create_eq(nombre):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s LIMIT 1", (nombre,))
    r = cur.fetchone()
    if r: return r[0]
    if not APPLY: return None
    cur.execute("INSERT INTO equipo (nombre, nombre_es, tipo) VALUES (%s,%s,'club') RETURNING id",
                (nombre, nombre))
    return cur.fetchone()[0]

def get_or_create_fase(tipo, nombre, orden):
    cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo=%s", (TORNEO_ID, tipo))
    r = cur.fetchone()
    if r: return r[0], True
    if not APPLY: return None, False
    cur.execute("INSERT INTO fase (torneo_id, nombre, tipo, orden) VALUES (%s,%s,%s,%s) RETURNING id",
                (TORNEO_ID, nombre, tipo, orden))
    return cur.fetchone()[0], False

# etiquetas de la ronda ORIGEN de cada slot (O=octavos, C=cuartos, S=semis)
PREV_ABBR = {"cuartos": "O", "semis": "C", "final": "S"}

print(f"=== CREAR ARBOL KO torneo {TORNEO_ID} ===")
for tipo, nombre, orden, n, ida_vuelta in ROUNDS:
    fase_id, existed = get_or_create_fase(tipo, nombre, orden)
    if existed and fase_id:
        cur.execute("SELECT count(*) FROM partido WHERE fase_id=%s", (fase_id,))
        if cur.fetchone()[0] > 0:
            print(f"[skip] {nombre}: ya tiene partidos"); continue
    ab = PREV_ABBR[tipo]
    print(f"\n{nombre} (fase {fase_id}) - {n} llave(s):")
    for j in range(n):
        localn = f"Gan. {ab}{2*j+1}"
        visitn = f"Gan. {ab}{2*j+2}"
        lid = get_or_create_eq(localn)
        vid = get_or_create_eq(visitn)
        print(f"  Llave {j+1}: {localn}  vs  {visitn}")
        legs = 1 if not ida_vuelta else 2
        for leg in range(legs):
            L, V = (lid, vid) if leg == 0 else (vid, lid)
            if APPLY:
                cur.execute("""INSERT INTO partido (fase_id, torneo_id, equipo_local_id,
                               equipo_visitante_id, estado) VALUES (%s,%s,%s,%s,'programado')""",
                            (fase_id, TORNEO_ID, L, V))

if APPLY:
    conn.commit(); print("\n== COMMIT ok ==")
else:
    print("\n== DRY-RUN (agrega --apply para crear el arbol) ==")
cur.close(); conn.close()
