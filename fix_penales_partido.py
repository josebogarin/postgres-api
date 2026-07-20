"""
fix_penales_partido.py
Limpia pred_penales_partido con valores fuera de rango (> 3) -> NULL
y muestra cuantas apuestas se corrigieron por apostador.

Ejecutar: python fix_penales_partido.py
"""
import subprocess, sys

def psql(sql):
    r = subprocess.run(
        ["docker","exec","-i","core-postgres","psql","-U","app_user","-d","becbuc",
         "-t","-A","-F","\t","-c", sql],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("ERROR psql:", r.stderr); sys.exit(1)
    lines = [l for l in r.stdout.strip().splitlines() if l]
    return [l.split("\t") for l in lines]

print("=== Diagnóstico pred_penales_partido ===\n")

# Cuantas apuestas tienen valores fuera de rango
diag = psql("""
    SELECT COUNT(*) as total,
           COUNT(pred_penales_partido) as con_valor,
           COUNT(*) FILTER (WHERE pred_penales_partido > 3) as fuera_rango,
           MIN(pred_penales_partido) as min_val,
           MAX(pred_penales_partido) as max_val
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    WHERE p.torneo_id = 2;
""")
if diag:
    r = diag[0]
    print(f"  Total apuestas torneo 2: {r[0]}")
    print(f"  Con pred_penales_partido: {r[1]}")
    print(f"  Fuera de rango (> 3):     {r[2]}")
    print(f"  Rango: {r[3]} - {r[4]}")

# Detalle por apostador
print("\n  Valores fuera de rango por apostador:")
detalle = psql("""
    SELECT a.apostador_id, COUNT(*) as n, MIN(pred_penales_partido), MAX(pred_penales_partido)
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    WHERE p.torneo_id = 2 AND a.pred_penales_partido > 3
    GROUP BY a.apostador_id
    ORDER BY a.apostador_id;
""")
if detalle:
    for row in detalle:
        print(f"    apostador_id={row[0]}: {row[1]} apuestas, rango {row[2]}-{row[3]}")
else:
    print("    (ninguno fuera de rango)")

answer = input("\n¿Limpiar valores > 3 a NULL? (s/N): ").strip().lower()
if answer != 's':
    print("Cancelado.")
    sys.exit(0)

# Fix: valores > 3 -> NULL
fix = psql("""
    UPDATE apuesta SET pred_penales_partido = NULL
    WHERE pred_penales_partido > 3
      AND partido_id IN (SELECT id FROM partido WHERE torneo_id = 2);
""")
print("\n✅ Valores fuera de rango limpiados (NULL = sin apuesta = 0 en scoring).")
print("   Recalcular puntajes via POST /calcular-puntajes/2 desde Herramientas del portal.")
