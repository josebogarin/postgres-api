import psycopg2, psycopg2.extras, sys

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

try:
    conn = psycopg2.connect(CONN_BEC)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Apuestas 8vos
    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT a.apostador_id) AS apostadores,
               COUNT(DISTINCT a.partido_id) AS partidos
        FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        WHERE p.numero_fifa BETWEEN 89 AND 96
    """)
    r = cur.fetchone()
    lineas = [
        f"8vos en BD: {r['total']} apuestas | {r['apostadores']} apostadores | {r['partidos']} partidos"
    ]

    # Estado R32 bloqueo
    cur.execute("""
        SELECT nombre, COALESCE(bloqueada, FALSE) AS bloqueada
        FROM fase WHERE torneo_id = 2 AND tipo ILIKE 'ronda32'
        ORDER BY id
    """)
    for f in cur.fetchall():
        estado = "BLOQUEADA" if f['bloqueada'] else "SIN BLOQUEAR"
        lineas.append(f"R32: {f['nombre']} -> {estado}")

    # Detalle por partido 8vos
    cur.execute("""
        SELECT p.numero_fifa, e1.nombre AS local, e2.nombre AS visitante,
               COUNT(a.id) AS apuestas
        FROM partido p
        JOIN equipo e1 ON e1.id = p.equipo_local_id
        JOIN equipo e2 ON e2.id = p.equipo_visitante_id
        LEFT JOIN apuesta a ON a.partido_id = p.id
        WHERE p.numero_fifa BETWEEN 89 AND 96
        GROUP BY p.numero_fifa, e1.nombre, e2.nombre
        ORDER BY p.numero_fifa
    """)
    lineas.append("")
    lineas.append("Detalle por partido:")
    for row in cur.fetchall():
        lineas.append(f"  P{row['numero_fifa']:03d}: {row['local']} vs {row['visitante']} -> {row['apuestas']} apuestas")

    conn.close()

    resultado = "\n".join(lineas) + "\n\nOK"
    print(resultado)
    with open(r"C:\proyecto FAST API\resultado_verificacion_8vos.txt", "w", encoding="utf-8") as f:
        f.write(resultado)

except Exception as e:
    msg = f"ERROR: {e}"
    print(msg)
    with open(r"C:\proyecto FAST API\resultado_verificacion_8vos.txt", "w", encoding="utf-8") as f:
        f.write(msg)
