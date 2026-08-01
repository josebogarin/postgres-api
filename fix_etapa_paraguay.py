import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""
fix_etapa_paraguay.py — FIX ITEM F (Etapa Paraguay).

Corrige la inversion de nomenclatura de fases del item F:
  - "16avos" = R32 = ronda32  (Alemania, Paraguay avanzo -> NO cobra)
  - "octavos"/"8vos" = R16 = ronda16  (Francia, eliminacion -> cobra 6)

Hace, en orden:
  1) Snapshot ANTES (distribucion pred + pts_etapa_paraguay).
  2) Parche de codigo con safe_patch_* (backup + verificacion, rollback si falla):
       - copa_mundo_2026.py  _norm_etapa: 16avos->ronda32, agrega 8vos->ronda16
       - BECBUC-portal.html / BECBUC-movil.html / BECBUC-pronos.html faseOpts: relabel
  3) Backup + remap de datos: apuesta_global.pred_etapa_paraguay 'ronda16' -> 'ronda32'
     (los 10 que via el select mal etiquetado pusieron "16avos"/Alemania).
     Los '8vos' NO se tocan: el fix de codigo los normaliza a ronda16.
  4) Recalculo de globales via POST /calcular-puntajes/2 (uvicorn debe estar corriendo).
  5) Snapshot DESPUES + verificacion (cherem=0, decanita=6, 8vos=6, ronda32=0).

SOLO afecta el item F (global). No toca match scores ni el bloqueo de fases.
Idempotente: se puede correr 2 veces sin efecto adicional.
"""
import sys, os, time, json, urllib.request, urllib.error
import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = _BASE
sys.path.insert(0, ROOT)
TID = 2
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")
API = "http://localhost:8000"

ENGINE = os.path.join(ROOT, r"backend\app\services\scoring\engines\copa_mundo_2026.py")
PORTAL = os.path.join(ROOT, r"backend\static\BECBUC-portal.html")
MOVIL  = os.path.join(ROOT, r"backend\static\BECBUC-movil.html")
PRONOS = os.path.join(ROOT, r"backend\static\BECBUC-pronos.html")


def p(*a):
    print(*a); sys.stdout.flush()


# ---- normalizador CORREGIDO (para snapshots) --------------------------------
_NORM_FIX = {
    "grupo": "grupo", "ronda32": "ronda32", "ronda16": "ronda16",
    "cuartos": "cuartos", "semis": "semis", "final": "final", "tercer_puesto": "final",
    "grupos": "grupo", "fase de grupos": "grupo",
    "16avos": "ronda32", "16avos de final": "ronda32",
    "dieciseisavos": "ronda32", "32avos": "ronda32",
    "octavos": "ronda16", "octavos de final": "ronda16",
    "8vos": "ronda16", "8vo": "ronda16", "8avos": "ronda16",
    "cuartos de final": "cuartos", "semifinal": "semis", "semis ": "semis",
}
def norm_fix(v):
    return _NORM_FIX.get(str(v or "").lower().strip(), str(v or "").lower().strip())


def snapshot(cur, titulo):
    p(f"\n--- {titulo} ---")
    cur.execute(f"""
        SELECT ag.pred_etapa_paraguay AS pe,
               COUNT(*) AS n,
               COUNT(*) FILTER (WHERE COALESCE(pg.pts_etapa_paraguay,0) > 0) AS cobraron
        FROM apuesta_global ag
        LEFT JOIN puntaje_global pg
          ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
        WHERE ag.torneo_id={TID}
        GROUP BY ag.pred_etapa_paraguay ORDER BY n DESC
    """)
    p("    pred_guardado  | count | cobraron(F>0)")
    for r in cur.fetchall():
        p(f"    {str(r['pe']):<14} | {r['n']:>5} | {r['cobraron']}")


def foco(becbuc, appdb, titulo):
    bc = becbuc.cursor(cursor_factory=RealDictCursor)
    ac = appdb.cursor(cursor_factory=RealDictCursor)
    ac.execute("SELECT id, username FROM users")
    umap = {r["id"]: r["username"] for r in ac.fetchall()}
    bc.execute(f"""
        SELECT ag.apostador_id AS uid, ag.pred_etapa_paraguay AS pe,
               pg.pts_etapa_paraguay AS pts
        FROM apuesta_global ag
        LEFT JOIN puntaje_global pg
          ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
        WHERE ag.torneo_id={TID}
    """)
    rows = bc.fetchall()
    p(f"\n--- {titulo}: cherem / decanita ---")
    for r in rows:
        u = (umap.get(r["uid"]) or "").lower()
        if u in ("cherem", "decanita"):
            p(f"    {umap.get(r['uid']):<10} pred={r['pe']!r} pts_F={r['pts']}")
    tot = sum(1 for r in rows if (r["pts"] or 0) > 0)
    p(f"    total que cobran F (6 pts): {tot}")
    bc.close(); ac.close()


def api_post(path, token=None, timeout=300):
    url = API + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login():
    body = json.dumps({"username": "jose", "password": "catalina"}).encode()
    req = urllib.request.Request(API + "/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return d.get("access_token") or d.get("token") or d.get("jwt")


def patch_codigo():
    from safe_write import safe_patch_py, safe_patch_html
    p("\n[2] Parche de codigo (safe_patch_* con backup + verificacion):")

    # 2a) Engine
    eng_src = open(ENGINE, encoding="utf-8").read()
    if '"8vos": "ronda16"' in eng_src:
        p("    engine: ya parcheado (contiene 8vos->ronda16). Skip.")
    else:
        old = '            "16avos": "ronda16", "16avos de final": "ronda16", "octavos": "ronda16",\n'
        new = (
            '            # R32 = "16avos"/"dieciseisavos de final" (NO es ronda16)\n'
            '            "16avos": "ronda32", "16avos de final": "ronda32",\n'
            '            "dieciseisavos": "ronda32", "dieciseisavos de final": "ronda32",\n'
            '            # R16 = "octavos"/"8vos"\n'
            '            "octavos": "ronda16", "octavos de final": "ronda16",\n'
            '            "8vos": "ronda16", "8vo": "ronda16", "8avos": "ronda16",\n'
        )
        safe_patch_py(ENGINE, [(old, new)])
        p("    engine: OK (16avos->ronda32, +8vos->ronda16)")

    # 2b) Frontends: relabel del select faseOpts (cosmetico, alinea con ETAPA_LABEL)
    def relabel(path, reps, nombre):
        try:
            src = open(path, encoding="utf-8").read()
            if "Octavos de Final" in src:
                p(f"    {nombre}: ya parcheado. Skip."); return
            safe_patch_html(path, reps)
            p(f"    {nombre}: OK (relabel select)")
        except Exception as e:
            p(f"    {nombre}: AVISO no parcheado ({e}). (no critico para el scoring)")

    relabel(PORTAL, [
        ("{ t:'ronda32', n:'32avos de Final' },", "{ t:'ronda32', n:'16avos de Final' },"),
        ("{ t:'ronda16', n:'16avos de Final' },", "{ t:'ronda16', n:'Octavos de Final' },"),
    ], "portal")
    relabel(MOVIL, [
        ("{t:'ronda32',n:'32avos de Final'}", "{t:'ronda32',n:'16avos de Final'}"),
        ("{t:'ronda16',n:'16avos de Final'}", "{t:'ronda16',n:'Octavos de Final'}"),
    ], "movil")
    relabel(PRONOS, [
        ("{t:'ronda32',n:'32avos de Final'}", "{t:'ronda32',n:'16avos de Final'}"),
        ("{t:'ronda16',n:'16avos de Final'}", "{t:'ronda16',n:'Octavos de Final'}"),
    ], "pronos")


def main():
    p("=" * 78)
    p(" FIX ITEM F — ETAPA PARAGUAY")
    p("=" * 78)

    becbuc = psycopg2.connect(dbname="becbuc", **DB)
    appdb  = psycopg2.connect(dbname="app_db", **DB)
    becbuc.autocommit = False
    cur = becbuc.cursor(cursor_factory=RealDictCursor)

    # 1) ANTES
    snapshot(cur, "[1] ANTES (distribucion + cobraron)")
    foco(becbuc, appdb, "[1] ANTES")

    # 2) Parche de codigo
    patch_codigo()

    # 3) Remap de datos: ronda16 -> ronda32 (los 10 que pusieron '16avos'/Alemania)
    p("\n[3] Remap de datos apuesta_global (ronda16 -> ronda32):")
    cur.execute(f"""SELECT apostador_id, pred_etapa_paraguay
                    FROM apuesta_global
                    WHERE torneo_id={TID} AND pred_etapa_paraguay='ronda16'""")
    afect = cur.fetchall()
    # backup a archivo
    bkp = os.path.join(ROOT, "fix_etapa_paraguay_backup_rows.txt")
    with open(bkp, "w", encoding="utf-8") as f:
        for r in afect:
            f.write(f"{r['apostador_id']}\t{r['pred_etapa_paraguay']}\n")
    p(f"    filas a remapear (ronda16): {len(afect)}  (backup: {bkp})")
    cur.execute(f"""UPDATE apuesta_global SET pred_etapa_paraguay='ronda32'
                    WHERE torneo_id={TID} AND pred_etapa_paraguay='ronda16'""")
    p(f"    UPDATE aplicados: {cur.rowcount}")
    becbuc.commit()
    p("    commit OK.")

    # 4) Recalculo de globales (uvicorn --reload ya tomo el cambio del engine)
    p("\n[4] Recalculo de globales (POST /calcular-puntajes/%d):" % TID)
    p("    esperando 6s a que uvicorn --reload recargue el engine...")
    time.sleep(6)
    try:
        tok = login()
        if not tok:
            p("    !! login sin token. Verifica credenciales / uvicorn.");
        else:
            res = api_post(f"/api/v1/bets/calcular-puntajes/{TID}", token=tok, timeout=300)
            p(f"    recalc OK. respuesta: {json.dumps(res)[:400]}")
    except urllib.error.URLError as e:
        p(f"    !! No se pudo llamar al API ({e}). ARRANCA uvicorn y volve a correr este .bat")
        p("       (el remap de datos ya quedo aplicado; solo falta recalcular).")
    except Exception as e:
        p(f"    !! Error en recalc: {e}")

    # 5) DESPUES
    cur2 = becbuc.cursor(cursor_factory=RealDictCursor)
    snapshot(cur2, "[5] DESPUES (distribucion + cobraron)")
    foco(becbuc, appdb, "[5] DESPUES")

    # verificacion final
    cur2.execute(f"""
        SELECT ag.pred_etapa_paraguay AS pe,
               COUNT(*) FILTER (WHERE COALESCE(pg.pts_etapa_paraguay,0)=6) AS con6,
               COUNT(*) FILTER (WHERE COALESCE(pg.pts_etapa_paraguay,0)=0) AS con0,
               COUNT(*) AS n
        FROM apuesta_global ag
        LEFT JOIN puntaje_global pg
          ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
        WHERE ag.torneo_id={TID}
        GROUP BY ag.pred_etapa_paraguay ORDER BY n DESC
    """)
    p("\n[6] VERIFICACION (esperado: 8vos=6pts, ronda32=0pts):")
    ok = True
    for r in cur2.fetchall():
        pe = r["pe"]
        estado = ""
        if norm_fix(pe) == "ronda16" and r["con6"] != r["n"]:
            estado = "  <-- ERROR: deberian cobrar 6 (revisar uvicorn reload)"; ok = False
        if norm_fix(pe) == "ronda32" and r["con0"] != r["n"]:
            estado = "  <-- ERROR: no deberian cobrar"; ok = False
        p(f"    {str(pe):<12} n={r['n']:>2} con6={r['con6']:>2} con0={r['con0']:>2}{estado}")
    p("\n  RESULTADO:", "OK — fix aplicado y verificado." if ok else
      "REVISAR — si 8vos siguen en 0, uvicorn no recargo el engine: reinicia uvicorn y re-corre.")

    cur.close(); cur2.close(); becbuc.close(); appdb.close()
    p("=" * 78)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        p("ERROR FATAL:", e); traceback.print_exc()
