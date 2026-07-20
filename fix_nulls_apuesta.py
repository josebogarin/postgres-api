import psycopg2
DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
conn = psycopg2.connect(**DB)
conn.autocommit = True
cur = conn.cursor()
cur.execute("""
    UPDATE apuesta SET
        pred_local           = COALESCE(pred_local, 0),
        pred_visitante       = COALESCE(pred_visitante, 0),
        pred_amarillas       = COALESCE(pred_amarillas, 0),
        pred_rojas           = COALESCE(pred_rojas, 0),
        pred_var             = COALESCE(pred_var, 0),
        pred_penales_partido = COALESCE(pred_penales_partido, 0),
        pred_minuto_gol      = COALESCE(pred_minuto_gol, 0)
    WHERE pred_local IS NULL OR pred_visitante IS NULL
       OR pred_amarillas IS NULL OR pred_rojas IS NULL
       OR pred_var IS NULL OR pred_penales_partido IS NULL
       OR pred_minuto_gol IS NULL;
""")
print(f"Filas actualizadas: {cur.rowcount}")
cur.close()
conn.close()
