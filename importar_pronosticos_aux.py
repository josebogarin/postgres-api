"""
Script para crear tabla pronosticos_aux e importar datos del CSV.
Ejecutar con doble-click desde Explorer o desde PowerShell:
  python "C:\proyecto FAST API\importar_pronosticos_aux.py"
"""
import psycopg2
import sys
import os

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "dbname": "becbuc",
    "user": "app_user",
    "password": "superpassword",
}

SQL_FILE = os.path.join(os.path.dirname(__file__), "documentacion", "migracion_pronosticos_aux.sql")
RESULT_FILE = os.path.join(os.path.dirname(__file__), "resultado_importacion.txt")

def main():
    lines = []
    try:
        print("Conectando a PostgreSQL...")
        conn = psycopg2.connect(**DB_PARAMS)
        conn.autocommit = False
        cur = conn.cursor()
        lines.append("Conexion OK")

        print(f"Leyendo SQL: {SQL_FILE}")
        with open(SQL_FILE, "r", encoding="utf-8") as f:
            sql = f.read()
        lines.append(f"SQL leido: {len(sql)} chars")

        print("Ejecutando migracion...")
        # Ejecutar todo el SQL
        cur.execute(sql)
        conn.commit()
        lines.append("Migracion ejecutada y commiteada OK")

        # Verificacion
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT nombre) as apostadores,
                   MIN(id_partido) AS desde,
                   MAX(id_partido) AS hasta
            FROM pronosticos_aux
        """)
        row = cur.fetchone()
        msg = f"RESULTADO: total={row[0]}, apostadores={row[1]}, desde={row[2]}, hasta={row[3]}"
        print(msg)
        lines.append(msg)

        cur.close()
        conn.close()

    except Exception as e:
        msg = f"ERROR: {e}"
        print(msg)
        lines.append(msg)

    # Escribir resultado a archivo
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nResultado escrito en: {RESULT_FILE}")
    input("\nPresione ENTER para cerrar...")

if __name__ == "__main__":
    main()
