"""
Diagnóstico rápido: estado de partidos de octavos de final (ronda16) en la BD.
"""
import subprocess, sys, os

SQL = """
SELECT
    p.numero_fifa AS num,
    el.nombre AS local,
    p.goles_local AS gl,
    p.goles_visitante AS gv,
    ev.nombre AS visitante,
    p.penales_local AS pen_l,
    p.penales_visitante AS pen_v,
    p.amarillas, p.rojas, p.decisiones_var AS var,
    p.penales_partido AS pen_partido,
    p.minuto_primer_gol AS minuto_gol,
    p.estado,
    f.tipo AS fase,
    COALESCE(f.bloqueada, FALSE) AS bloqueada,
    p.api_fixture_id,
    p.datos_confirmados
FROM partido p
JOIN fase f ON f.id = p.fase_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE f.tipo = 'ronda16'
ORDER BY p.numero_fifa;
"""

def run():
    cmd = [
        "docker", "exec", "core-postgres",
        "psql", "-U", "app_user", "-d", "becbuc",
        "-c", SQL
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print("=== OCTAVOS (ronda16) ===")
        print(result.stdout or "(sin output)")
        if result.returncode != 0:
            print("STDERR:", result.stderr)
    except FileNotFoundError:
        # Docker no en PATH, probar con ruta completa
        try:
            result = subprocess.run(
                ["C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
                 "exec", "core-postgres", "psql", "-U", "app_user", "-d", "becbuc", "-c", SQL],
                capture_output=True, text=True, timeout=30
            )
            print("=== OCTAVOS (ronda16) ===")
            print(result.stdout or "(sin output)")
            if result.returncode != 0:
                print("STDERR:", result.stderr)
        except Exception as e:
            print(f"Error con Docker: {e}")
            # Intentar via psycopg2 directo
            try_psycopg2()

def try_psycopg2():
    """Conectar directamente al puerto PostgreSQL expuesto por Docker."""
    # Buscar el venv del proyecto
    venv_python = os.path.join(os.path.dirname(__file__), "backend", ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        print("No se encontró el venv. Instalar psycopg2 manualmente.")
        return

    script = """
import psycopg2, sys
conn = psycopg2.connect(host='localhost', port=5432, user='app_user', password='app_password', dbname='becbuc')
cur = conn.cursor()
cur.execute('''
SELECT p.numero_fifa, el.nombre, p.goles_local, p.goles_visitante, ev.nombre,
       p.penales_local, p.penales_visitante, p.amarillas, p.rojas,
       p.decisiones_var, p.penales_partido, p.minuto_primer_gol,
       p.estado, f.tipo, COALESCE(f.bloqueada,FALSE), p.api_fixture_id, p.datos_confirmados
FROM partido p JOIN fase f ON f.id=p.fase_id
LEFT JOIN equipo el ON el.id=p.equipo_local_id
LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
WHERE f.tipo='ronda16' ORDER BY p.numero_fifa
''')
rows = cur.fetchall()
cols = ['num','local','gl','gv','visitante','pen_l','pen_v','amarillas','rojas','var','pen_partido','minuto_gol','estado','fase','bloqueada','api_fixture_id','confirmado']
print('\\t'.join(cols))
for r in rows:
    print('\\t'.join(str(x) if x is not None else 'NULL' for x in r))
cur.close(); conn.close()
"""
    result = subprocess.run([venv_python, "-c", script], capture_output=True, text=True, timeout=30)
    print(result.stdout or "(sin output)")
    if result.returncode != 0:
        print("STDERR:", result.stderr)

if __name__ == "__main__":
    run()
    input("\nPresioná Enter para cerrar...")
