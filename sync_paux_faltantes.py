"""
sync_paux_faltantes.py
Inserta registros FALTANTES en apuesta desde pronosticos_aux.

Problema: la tabla apuesta le falta registros para algunos partidos finalizados
por apostador. pronosticos_aux tiene datos para los 72 partidos de grupos.
Este script:
  1. Diagnostica cuántos registros faltan
  2. Inserta los registros faltantes
  3. Recalcula puntajes via API

Ejecutar:
  cd "C:\\proyecto FAST API"
  backend\\.venv\\Scripts\\python.exe sync_paux_faltantes.py
"""

import psycopg2
import traceback
import requests

BECBUC_DSN  = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
APP_DB_DSN  = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
API_BASE    = "http://localhost:8000/api/v1"
TORNEO_ID   = 2
ADMIN_USER  = "jose"
ADMIN_PASS  = "catalina"

def login():
    r = requests.post(f"{API_BASE}/auth/login",
                      json={"username": ADMIN_USER, "password": ADMIN_PASS})
    r.raise_for_status()
    return r.json()["access_token"]

def main():
    conn = psycopg2.connect(BECBUC_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    print("=" * 60)
    print("DIAGNÓSTICO")
    print("=" * 60)

    # 1. Total apuestas en torneo 2 con goles
    cur.execute("""
        SELECT COUNT(DISTINCT (a.apostador_id, a.partido_id))
        FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = %s
          AND p.estado = 'finalizado'
          AND p.goles_local IS NOT NULL
    """, (TORNEO_ID,))
    total_ap_fin = cur.fetchone()[0]
    print(f"Apuestas existentes para partidos finalizados: {total_ap_fin}")

    # 2. Partidos finalizados en torneo
    cur.execute("""
        SELECT COUNT(*)
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = %s AND p.estado = 'finalizado' AND p.goles_local IS NOT NULL
    """, (TORNEO_ID,))
    n_fin = cur.fetchone()[0]
    print(f"Partidos finalizados en torneo {TORNEO_ID}: {n_fin}")

    # 3. Apostadores únicos
    cur.execute("""
        SELECT COUNT(DISTINCT apostador_id)
        FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = %s
    """, (TORNEO_ID,))
    n_apost = cur.fetchone()[0]
    print(f"Apostadores con al menos 1 apuesta en torneo {TORNEO_ID}: {n_apost}")

    esperado = n_fin * n_apost
    faltantes_estimados = esperado - total_ap_fin
    print(f"Esperado (fin × apostadores): {n_fin} × {n_apost} = {esperado}")
    print(f"Faltantes estimados: {faltantes_estimados}")

    # 4. ¿pronosticos_aux tiene numero_partido_fifa?
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pronosticos_aux' AND column_name = 'numero_partido_fifa'
    """)
    tiene_numfifa = cur.fetchone() is not None
    print(f"\npronosticos_aux.numero_partido_fifa existe: {tiene_numfifa}")

    if not tiene_numfifa:
        print("ERROR: Ejecutar sync_paux_a_apuesta.py primero (crea numero_partido_fifa)")
        conn.close()
        return

    # 5. ¿partido tiene numero_fifa?
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'partido' AND column_name = 'numero_fifa'
    """)
    partido_tiene_numfifa = cur.fetchone() is not None
    print(f"partido.numero_fifa existe: {partido_tiene_numfifa}")

    if not partido_tiene_numfifa:
        print("ADVERTENCIA: partido.numero_fifa no existe. Intentando join por equipo...")

    # 6. Construir mapa nombre → apostador_id desde apuesta existente
    cur.execute("""
        SELECT LOWER(TRIM(nombre_apostador)), apostador_id
        FROM apuesta
        WHERE nombre_apostador IS NOT NULL
        GROUP BY LOWER(TRIM(nombre_apostador)), apostador_id
        HAVING COUNT(*) > 0
        ORDER BY COUNT(*) DESC
    """)
    nombre_map = {}
    for nombre, aid in cur.fetchall():
        if nombre not in nombre_map:
            nombre_map[nombre] = aid
    print(f"\nMapa nombre→apostador_id: {len(nombre_map)} entradas")

    # También buscar en pronosticos_aux aliases
    cur.execute("SELECT DISTINCT LOWER(TRIM(nombre)), LOWER(TRIM(alias)) FROM pronosticos_aux")
    alias_names = cur.fetchall()
    for nombre, alias in alias_names:
        if nombre in nombre_map and alias and alias not in nombre_map:
            nombre_map[alias] = nombre_map[nombre]

    # 7. Encontrar registros faltantes en apuesta
    print("\n" + "=" * 60)
    print("BUSCANDO FALTANTES")
    print("=" * 60)

    if partido_tiene_numfifa:
        join_condition = "p.numero_fifa = pa.numero_partido_fifa"
    else:
        join_condition = """p.equipo_local_id = pa.idequipolocal
            AND p.equipo_visitante_id = pa.idequipovisitante
            AND pa.idequipolocal IS NOT NULL"""

    cur.execute(f"""
        SELECT
            pa.numero_partido_fifa,
            pa.nombre,
            pa.alias,
            pa.goles_local,
            pa.goles_visitante,
            pa.amarillas,
            pa.rojas,
            pa.var,
            pa.penales,
            pa.primer_gol,
            p.id AS partido_id
        FROM pronosticos_aux pa
        JOIN partido p ON {join_condition}
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN apuesta a ON a.partido_id = p.id
            AND LOWER(TRIM(a.nombre_apostador)) = LOWER(TRIM(pa.nombre))
        WHERE f.torneo_id = %s
          AND p.estado = 'finalizado'
          AND p.goles_local IS NOT NULL
          AND a.id IS NULL
        ORDER BY pa.nombre, p.id
    """, (TORNEO_ID,))
    faltantes = cur.fetchall()
    print(f"Registros faltantes encontrados: {len(faltantes)}")

    if not faltantes:
        print("\nNo hay registros faltantes. Verificando pred_local NULL en existentes...")

        # Puede que los registros existan pero con pred_local=NULL
        cur.execute(f"""
            SELECT COUNT(*)
            FROM apuesta a
            JOIN partido p ON p.id = a.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = %s
              AND p.estado = 'finalizado'
              AND p.goles_local IS NOT NULL
              AND a.pred_local IS NULL
        """, (TORNEO_ID,))
        null_preds = cur.fetchone()[0]
        print(f"Apuestas existentes con pred_local=NULL (sin predicción): {null_preds}")

        if null_preds > 0:
            print("\nActualizando pred_local NULL desde pronosticos_aux...")
            cur.execute(f"""
                UPDATE apuesta a
                SET
                    pred_local           = pa.goles_local,
                    pred_visitante       = pa.goles_visitante,
                    pred_amarillas       = pa.amarillas,
                    pred_rojas           = pa.rojas,
                    pred_var             = pa.var,
                    pred_penales_partido = pa.penales,
                    pred_minuto_gol      = pa.primer_gol
                FROM pronosticos_aux pa, partido p, fase f
                WHERE p.id = a.partido_id
                  AND f.id = p.fase_id
                  AND f.torneo_id = %s
                  AND {join_condition.replace('p.', 'p.')}
                  AND LOWER(TRIM(a.nombre_apostador)) = LOWER(TRIM(pa.nombre))
                  AND a.pred_local IS NULL
                  AND p.estado = 'finalizado'
            """, (TORNEO_ID,))
            n_updated = cur.rowcount
            print(f"Actualizados: {n_updated}")
            conn.commit()
        else:
            print("Nada que hacer. Los puntajes ya deberían ser correctos.")
            print("Prueba: POST /calcular-puntajes/2")
        conn.close()
        return

    # 8. Insertar registros faltantes
    print("\n" + "=" * 60)
    print("INSERTANDO REGISTROS FALTANTES")
    print("=" * 60)

    insertados = 0
    sin_match = {}

    for row in faltantes:
        numfifa, nombre, alias, gl, gv, amar, rojas, var, penales, min_gol, partido_id = row
        nombre_lower = nombre.lower().strip() if nombre else ""
        alias_lower  = alias.lower().strip()  if alias  else ""

        aid = nombre_map.get(nombre_lower) or nombre_map.get(alias_lower)
        if aid is None:
            sin_match[nombre] = sin_match.get(nombre, 0) + 1
            continue

        cur.execute("""
            INSERT INTO apuesta (
                apostador_id, partido_id,
                pred_local, pred_visitante,
                pred_amarillas, pred_rojas, pred_var,
                pred_penales_partido, pred_minuto_gol,
                pred_penales,
                puntos, puntos_bonus,
                nombre_apostador,
                numero_fifa
            )
            VALUES (
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s,
                0, 0,
                %s,
                %s
            )
            ON CONFLICT DO NOTHING
        """, (
            aid, partido_id,
            gl, gv,
            amar, rojas, var,
            penales, min_gol,
            1 if penales and penales > 0 else 0,
            nombre,
            numfifa
        ))
        if cur.rowcount > 0:
            insertados += 1

    print(f"Insertados: {insertados}")
    if sin_match:
        print(f"Sin match ({len(sin_match)} nombres): {list(sin_match.keys())[:10]}")

    conn.commit()
    print("✅ Commit OK")

    # 9. Verificación
    cur.execute("""
        SELECT COUNT(*)
        FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = %s AND p.estado = 'finalizado'
          AND p.goles_local IS NOT NULL
    """, (TORNEO_ID,))
    total_post = cur.fetchone()[0]
    print(f"\nApuestas para partidos finalizados post-fix: {total_post}")
    print(f"Esperado: {esperado}")

    cur.close()
    conn.close()

    # 10. Recalcular puntajes
    print("\n" + "=" * 60)
    print("RECALCULANDO PUNTAJES")
    print("=" * 60)
    try:
        token = login()
        r = requests.post(
            f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}",
            headers={"Authorization": f"Bearer {token}"}
        )
        r.raise_for_status()
        data = r.json()
        print(f"✅ Recalculado: {data.get('apuestas')} apuestas, "
              f"{data.get('plenos')} plenos, {data.get('aciertos')} aciertos")
    except Exception as e:
        print(f"Error recalculando (hacerlo manualmente): {e}")

    print("\n✅ LISTO. Refresca becbuc-live.html para ver los puntajes actualizados.")

if __name__ == "__main__":
    main()
