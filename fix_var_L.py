# -*- coding: utf-8 -*-
"""
fix_var_L.py [--apply]
Diagnostica y corrige el item L (VAR) en puntaje_detalle.

El motor puntua L = mult si (pred_var == real_var). puntaje_detalle guarda pred_var,
real_var y pts_var usados al puntuar. Si esos valores guardados NO coinciden con los
actuales (apuesta.pred_var / partido.decisiones_var), el puntaje quedo STALE.

DRY RUN: muestra por fila  pred/real GUARDADO en puntaje_detalle  vs  ACTUAL,
         el pts_var guardado, el correcto, y la causa (real stale / pred stale / motor).
--apply: recalcula pts_var desde los datos ACTUALES y corrige pts_var, pts_bonus y
         pts_total por el delta exacto. Solo toca el item L.

Uso:
  backend\.venv\Scripts\python.exe fix_var_L.py
  backend\.venv\Scripts\python.exe fix_var_L.py --apply
"""
import sys
from collections import Counter
DO_APPLY = '--apply' in [a.lower() for a in sys.argv[1:]]
print('[APPLY]' if DO_APPLY else '[DRY RUN]')
try:
    import psycopg2, psycopg2.extras
except ImportError:
    import os; os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TID = 2
conn = psycopg2.connect(CONN); conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT pd.apostador_id, pd.partido_id, p.numero_fifa,
           COALESCE(pd.multiplicador,1) AS mult,
           pd.pred_var AS pd_pred, pd.real_var AS pd_real, COALESCE(pd.pts_var,0) AS pd_pts,
           COALESCE(pd.pts_bonus,0) AS pts_bonus, COALESCE(pd.pts_total,0) AS pts_total,
           a.pred_var AS cur_pred, p.decisiones_var AS cur_real
    FROM puntaje_detalle pd
    JOIN partido p ON p.id = pd.partido_id
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN apuesta a ON a.apostador_id = pd.apostador_id AND a.partido_id = pd.partido_id
    WHERE f.torneo_id = %s AND p.numero_fifa BETWEEN 1 AND 102
    ORDER BY p.numero_fifa, pd.apostador_id
""", (TID,))
rows = cur.fetchall()

fixes=[]; causa=Counter(); muestra=[]
for r in rows:
    correct = r['mult'] if ((r['cur_pred'] or 0)==(r['cur_real'] or 0)) else 0
    if correct == r['pd_pts']:
        continue
    delta = correct - r['pd_pts']
    if r['pd_real'] != r['cur_real']:
        c=f"real_var stale (guardo {r['pd_real']}, actual {r['cur_real']})"
    elif (r['pd_pred'] or 0) != (r['cur_pred'] or 0):
        c=f"pred_var stale (guardo {r['pd_pred']}, actual {r['cur_pred']})"
    else:
        c="motor (mismos datos, pts distinto)"
    causa[c.split(' (')[0]] += 1
    fixes.append((r['partido_id'], r['apostador_id'], correct, delta))
    if len(muestra)<20:
        muestra.append((r['numero_fifa'], r['apostador_id'], r['pd_pred'], r['pd_real'], r['pd_pts'],
                        r['cur_pred'], r['cur_real'], correct, c))

print(f"\nFilas L a corregir: {len(fixes)}")
print(f"\n{'P#':<5}{'uid':<6}{'pdPred':>7}{'pdReal':>7}{'pdPts':>6}   {'curPred':>8}{'curReal':>8}{'correcto':>9}   CAUSA")
for nf,uid,pp,pr,pt,cp,cr,co,c in muestra:
    print(f"P{nf:03d} {uid:<6}{str(pp):>7}{str(pr):>7}{pt:>6}   {str(cp):>8}{str(cr):>8}{co:>9}   {c}")
if len(fixes)>20: print(f"  ... (+{len(fixes)-20} mas)")
print("\nRESUMEN POR CAUSA:")
for c,n in causa.most_common(): print(f"   {n:>4}  {c}")

if not DO_APPLY:
    print("\n[DRY RUN] No se escribio. Para aplicar: fix_var_L.py --apply")
    conn.close(); sys.exit(0)

print("\nAPLICANDO correccion de L (pts_var + pts_bonus + pts_total por delta)...")
for partido_id, uid, correct, delta in fixes:
    cur.execute("""
        UPDATE puntaje_detalle
        SET pts_var = %s,
            pts_bonus = COALESCE(pts_bonus,0) + %s,
            pts_total = COALESCE(pts_total,0) + %s,
            real_var  = (SELECT decisiones_var FROM partido WHERE id=%s),
            pred_var  = (SELECT pred_var FROM apuesta WHERE apostador_id=%s AND partido_id=%s)
        WHERE partido_id=%s AND apostador_id=%s
    """, (correct, delta, delta, partido_id, uid, partido_id, partido_id, uid))
conn.commit()
print(f"OK. {len(fixes)} filas corregidas.")
print("Nota: si luego se corre un recalculo que refresca grupos, deberia dar el mismo valor.")
conn.close()
