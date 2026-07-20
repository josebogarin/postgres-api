"""
fix_p030.py
===========
DIAGNOSTICO de resultados en BD vs valores esperados.

Por defecto: DRY_RUN = True -> solo muestra diferencias, NO modifica nada.
Para aplicar cambios: pasar argumento --apply.

IMPORTANTE: Verificar el resultado REAL de cada partido FIFA antes de aplicar.
"""
import sys, io, psycopg2, psycopg2.extras
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Por defecto solo diagnostica. Pasar --apply para commitear cambios.
DRY_RUN = '--apply' not in sys.argv

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

# Resultados segun Excel oficial BECBUC_contexto.xlsx
# VERIFICAR cada diferencia contra resultado real FIFA antes de --apply
RESULTADOS_EXCEL = {
    'P001':(2,0),'P002':(2,1),'P003':(1,1),'P004':(4,1),'P005':(0,1),
    'P006':(2,0),'P007':(1,1),'P008':(1,1),'P009':(1,0),'P010':(7,1),
    'P011':(2,2),'P012':(5,1),'P013':(1,1),'P014':(0,0),'P015':(2,2),
    'P016':(1,1),'P017':(3,1),'P018':(1,4),'P019':(3,0),'P020':(3,1),
    'P021':(1,0),'P022':(4,2),'P023':(1,1),'P024':(1,3),'P025':(1,1),
    'P026':(3,1),'P027':(6,0),'P028':(1,0),'P029':(3,0),'P030':(1,0),
    'P031':(0,1),'P032':(2,0),'P033':(2,1),'P034':(0,0),'P035':(5,1),
    'P036':(0,4),
}

conn = psycopg2.connect(**PG)
conn.autocommit = False
cur = conn.cursor()

modo = "DRY-RUN (solo diagnostico)" if DRY_RUN else "APPLY (aplicara cambios!)"
print(f"=== VERIFICACION RESULTADOS BD vs EXCEL ===")
print(f"Modo: {modo}\n")

cur.execute("""
    SELECT p.numero_partido_fifa, p.goles_local, p.goles_visitante, p.id,
           el.nombre AS local_nom, ev.nombre AS visitante_nom
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE p.estado = 'finalizado' AND f.torneo_id = 2
    ORDER BY p.numero_partido_fifa
""")
bd_partidos = {f"P{str(r['numero_partido_fifa']).zfill(3)}": dict(r) for r in cur.fetchall()}

print(f"{'PID':<6} {'LOCAL':<20} {'VISITANTE':<20} {'BD':^9} {'EXCEL':^9} STATUS")
print("─"*82)

errores = []
for pid in sorted(RESULTADOS_EXCEL.keys()):
    if pid not in bd_partidos:
        print(f"{pid:<6} {'(NO EN BD)':<42} {'?':^9} "
              f"{RESULTADOS_EXCEL[pid][0]}-{RESULTADOS_EXCEL[pid][1]:^9} ⚠")
        continue
    bd = bd_partidos[pid]
    gl_xls, gv_xls = RESULTADOS_EXCEL[pid]
    gl_bd, gv_bd = bd['goles_local'], bd['goles_visitante']
    match = (gl_bd == gl_xls and gv_bd == gv_xls)
    status = "✅" if match else "🔴 DIFIERE"
    loc = (bd['local_nom'] or '')[:18]
    vis = (bd['visitante_nom'] or '')[:18]
    print(f"{pid:<6} {loc:<20} {vis:<20} {gl_bd}-{gv_bd:^8} {gl_xls}-{gv_xls:^8} {status}")
    if not match:
        errores.append((pid, bd['id'], gl_xls, gv_xls, gl_bd, gv_bd,
                        bd['local_nom'], bd['visitante_nom']))

print(f"\n✅ Coinciden: {len(bd_partidos)-len(errores)}")
print(f"🔴 Difieren:  {len(errores)}")

if errores:
    print(f"\n=== DETALLES DE DIFERENCIAS ===")
    for pid, pid_id, gl_xls, gv_xls, gl_bd, gv_bd, loc, vis in errores:
        print(f"\n  {pid}: {loc} vs {vis}")
        print(f"    BD:    {gl_bd}-{gv_bd}")
        print(f"    Excel: {gl_xls}-{gv_xls}")
        print(f"    ⚠ Confirmar resultado real antes de aplicar")

    if DRY_RUN:
        print(f"\n{'='*50}")
        print(f"DRY-RUN: ningun cambio aplicado.")
        print(f"Si el Excel es correcto, ejecutar con:")
        print(f"  python fix_p030.py --apply")
    else:
        print(f"\nAplicando {len(errores)} correcciones...")
        for pid, pid_id, gl_xls, gv_xls, gl_bd, gv_bd, _, _ in errores:
            cur.execute(
                "UPDATE partido SET goles_local=%s, goles_visitante=%s WHERE id=%s",
                (gl_xls, gv_xls, pid_id)
            )
            print(f"  {pid}: {gl_bd}-{gv_bd} → {gl_xls}-{gv_xls} ✓")
        conn.commit()
        print("\n✅ Cambios commiteados.")
else:
    print("\nTodos los resultados coinciden. No hay correcciones necesarias.")

cur.close()
conn.close()
