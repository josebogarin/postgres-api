"""
Reconciliacion de partido_id en apuesta.

PROBLEMA: El parser Excel anterior tenia offsets incorrectos en las columnas,
por lo que algunas apuestas quedaron asignadas al partido_id equivocado.

SOLUCION:
1. Usa pronosticos_aux (que tiene equipo_local/equipo_visitante + idequipolocal/idequipovisitante)
   junto con la tabla partido para encontrar el partido_id correcto por nombres de equipos.
2. Actualiza apuesta.id_partido_ok = partido_id correcto (donde difiere del actual).
3. OPCIONALMENTE actualiza apuesta.partido_id = id_partido_ok (correccion definitiva).

Requiere que sync_paux_a_apuesta.py haya corrido primero (para tener idequipolocal/idequipovisitante).

Ejecutar:
  cd "C:\\proyecto FAST API\\backend"
  .venv\\Scripts\\Activate.ps1
  cd ..
  python reconciliar_partido_id.py [--apply]

  --apply : aplica la correccion (actualiza partido_id). Sin este flag solo diagnostica.
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import sys
import psycopg2
import psycopg2.extras

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = _osp.path.join(_BASE, 'resultado_reconciliar.txt')
APPLY = "--apply" in sys.argv

lines = []
log = lambda s: (lines.append(s), print(s))

conn = psycopg2.connect(**DB)
cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# ─── PASO 0: verificar columnas ───────────────────────────────────────────────
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='apuesta'
      AND column_name IN ('id_partido_ok','equipo_local_excel','equipo_visitante_excel')
    ORDER BY column_name;
""")
cols = [r[0] for r in cur.fetchall()]
log(f"Columnas nuevas en apuesta: {cols}")
if 'id_partido_ok' not in cols:
    log("ERROR: columna id_partido_ok no existe en apuesta. Ejecutar migracion primero.")
    log("SQL: ALTER TABLE apuesta ADD COLUMN id_partido_ok INT;")
    log("     ALTER TABLE apuesta ADD COLUMN equipo_local_excel TEXT;")
    log("     ALTER TABLE apuesta ADD COLUMN equipo_visitante_excel TEXT;")
    conn.close()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.exit(1)

# ─── PASO 1: verificar pronosticos_aux tiene idequipolocal/idequipovisitante ──
cur.execute("""
    SELECT COUNT(*), COUNT(idequipolocal), COUNT(idequipovisitante)
    FROM pronosticos_aux;
""")
tot, con_loc, con_vis = cur.fetchone()
log(f"pronosticos_aux: {tot} filas, idequipolocal={con_loc}, idequipovisitante={con_vis}")

if con_loc == 0:
    log("AVISO: idequipolocal no poblado. Corriendo lookup por nombres de partido...")
    # Hacer el mapeo inline: usa partido.equipo_local_id/visitante_id + equipo.nombre
    # para encontrar el partido correcto desde pronosticos_aux.equipo_local/equipo_visitante
    cur.execute("""
        SELECT COUNT(*) FROM pronosticos_aux
        WHERE numero_partido_fifa IS NULL;
    """)
    sin_num = cur.fetchone()[0]
    if sin_num > 0:
        log(f"AVISO: {sin_num} filas sin numero_partido_fifa. Ejecutar sync_paux_a_apuesta.py primero.")
        conn.close()
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        sys.exit(1)

# ─── PASO 2: encontrar partido_id correcto via pronosticos_aux ────────────────
# Para cada fila de apuesta:
#   join con pronosticos_aux en (nombre_apostador, numero_fifa)
#   -> obtenemos idequipolocal, idequipovisitante
#   join con partido en (equipo_local_id=idequipolocal AND equipo_visitante_id=idequipovisitante AND torneo_id=2)
#   -> obtenemos partido_id correcto
#   Comparar con apuesta.partido_id actual

log("\n=== Buscando partidos mal asignados ===")
cur.execute("""
    SELECT
        a.id            AS apuesta_id,
        a.apostador_id,
        a.nombre_apostador,
        a.numero_fifa,
        a.partido_id    AS partido_id_actual,
        pt_correcto.id  AS partido_id_correcto,
        el.nombre       AS equipo_local_paux,
        ev.nombre       AS equipo_visitante_paux,
        el2.nombre      AS equipo_local_actual,
        ev2.nombre      AS equipo_visitante_actual
    FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    -- Join con pronosticos_aux para obtener equipos correctos
    JOIN pronosticos_aux pa ON pa.numero_partido_fifa = a.numero_fifa
                            AND LOWER(pa.nombre) = LOWER(a.nombre_apostador)
    -- Encuentra el partido correcto por equipos
    JOIN partido pt_correcto ON pt_correcto.equipo_local_id    = pa.idequipolocal
                             AND pt_correcto.equipo_visitante_id = pa.idequipovisitante
    JOIN fase f2 ON f2.id = pt_correcto.fase_id AND f2.torneo_id = 2
    -- Nombres para diagnostico
    JOIN equipo el ON el.id = pa.idequipolocal
    JOIN equipo ev ON ev.id = pa.idequipovisitante
    JOIN equipo el2 ON el2.id = pt.equipo_local_id
    JOIN equipo ev2 ON ev2.id = pt.equipo_visitante_id
    WHERE f.torneo_id = 2
      AND pa.idequipolocal IS NOT NULL
      AND pa.idequipovisitante IS NOT NULL
      AND pt_correcto.id != a.partido_id  -- solo los mal asignados
    ORDER BY a.nombre_apostador, a.numero_fifa;
""")
mal_asignados = cur.fetchall()
log(f"Apuestas con partido_id INCORRECTO: {len(mal_asignados)}")

if mal_asignados:
    # Mostrar resumen por apostador
    por_apostador = {}
    for r in mal_asignados:
        nom = r['nombre_apostador'] or f"id={r['apostador_id']}"
        por_apostador.setdefault(nom, []).append(r)

    log(f"Afecta a {len(por_apostador)} apostadores:")
    for nom, rows in sorted(por_apostador.items()):
        log(f"  {nom}: {len(rows)} partidos mal asignados")

    log("\nMuestra de primeros 5:")
    for r in mal_asignados[:5]:
        log(f"  [{r['nombre_apostador'][:20]}] P{r['numero_fifa']:03d} "
            f"partido_actual={r['partido_id_actual']} ({r['equipo_local_actual']} vs {r['equipo_visitante_actual']}) "
            f"-> correcto={r['partido_id_correcto']} ({r['equipo_local_paux']} vs {r['equipo_visitante_paux']})")

# ─── PASO 3: UPDATE id_partido_ok (siempre) ──────────────────────────────────
log("\n=== Actualizando id_partido_ok ===")
cur.execute("""
    UPDATE apuesta a
    SET id_partido_ok = pt_correcto.id
    FROM pronosticos_aux pa,
         partido pt,
         fase f,
         partido pt_correcto,
         fase f2
    WHERE pt.id = a.partido_id
      AND f.id  = pt.fase_id
      AND f.torneo_id = 2
      AND pa.numero_partido_fifa = a.numero_fifa
      AND LOWER(pa.nombre) = LOWER(a.nombre_apostador)
      AND pt_correcto.equipo_local_id    = pa.idequipolocal
      AND pt_correcto.equipo_visitante_id = pa.idequipovisitante
      AND f2.id = pt_correcto.fase_id
      AND f2.torneo_id = 2
      AND pa.idequipolocal IS NOT NULL
      AND pa.idequipovisitante IS NOT NULL;
""")
n_ok = cur.rowcount
conn.commit()
log(f"id_partido_ok actualizado en {n_ok} filas")

# ─── PASO 4: Diagnostico post-update ─────────────────────────────────────────
cur.execute("""
    SELECT COUNT(*) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    WHERE f.torneo_id = 2
      AND a.id_partido_ok IS NOT NULL
      AND a.id_partido_ok != a.partido_id;
""")
con_error = cur.fetchone()[0]
log(f"Apuestas con partido_id != id_partido_ok (mal asignadas): {con_error}")

cur.execute("""
    SELECT COUNT(*) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    WHERE f.torneo_id = 2
      AND (a.id_partido_ok = a.partido_id OR a.id_partido_ok IS NULL);
""")
con_ok = cur.fetchone()[0]
log(f"Apuestas con partido_id correcto (o sin id_partido_ok): {con_ok}")

# ─── PASO 5: APLICAR CORRECCION (solo con --apply) ───────────────────────────
if APPLY:
    log("\n=== APLICANDO CORRECCION (--apply) ===")
    cur.execute("""
        UPDATE apuesta
        SET partido_id = id_partido_ok
        WHERE id_partido_ok IS NOT NULL
          AND id_partido_ok != partido_id;
    """)
    n_fix = cur.rowcount
    conn.commit()
    log(f"partido_id corregido en {n_fix} filas")

    # Verificacion final
    cur.execute("""
        SELECT COUNT(*) FROM apuesta a
        JOIN partido pt ON pt.id = a.partido_id
        JOIN fase f ON f.id = pt.fase_id
        WHERE f.torneo_id = 2
          AND a.id_partido_ok IS NOT NULL
          AND a.id_partido_ok != a.partido_id;
    """)
    restantes = cur.fetchone()[0]
    log(f"Apuestas aun incorrectas despues de fix: {restantes}")
    if restantes == 0:
        log("✅ CORRECCION COMPLETA. Ahora recalcular puntajes:")
        log("   POST /api/v1/bets/calcular-puntajes/2")
else:
    if con_error > 0:
        log(f"\n⚠ Para aplicar la correccion ejecutar:")
        log(f"   python reconciliar_partido_id.py --apply")
    else:
        log("\n✅ No hay correcciones necesarias (o sin datos de pronosticos_aux).")

cur.close()
conn.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nResultado guardado en: {OUT}")
