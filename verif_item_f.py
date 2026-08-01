import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""verif_item_f.py — SOLO LECTURA. Cierre del tema item F (Etapa Paraguay).
Cruza la BD (post-fix) con el Excel master de globales para:
  - Huguito (caso de referencia de la imagen)
  - los 18 '8vos' (0->6)
  - los 10 remapeados 'ronda16'->'ronda32' (cherem etc.)
No modifica nada."""
import sys, os, unicodedata
import psycopg2
from psycopg2.extras import RealDictCursor

TID = 2
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")
XLSX = _osp.path.join(_BASE, '20260611_2000- TBL CONSOLIDADA PRONOSTICOS ok.xlsx')

def p(*a): print(*a); sys.stdout.flush()
def norm(s):
    s = str(s or "").replace("\xa0", " ").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

becbuc = psycopg2.connect(dbname="becbuc", **DB)
appdb  = psycopg2.connect(dbname="app_db", **DB)
bc = becbuc.cursor(cursor_factory=RealDictCursor)
ac = appdb.cursor(cursor_factory=RealDictCursor)

ac.execute("SELECT id, username, COALESCE(nombre,'') AS nombre FROM users")
urows = ac.fetchall()
umap = {r["id"]: r for r in urows}

# ---------- Excel: etapa escrita por alias (fila P115, col EQUIPO 1) ----------
excel_etapa = {}   # norm(alias) -> valor escrito
excel_info = "no leido"
try:
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    found = False
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        # buscar fila de encabezado con ID PARTIDO / ALIAS / EQUIPO 1
        hdr_idx = None; cID=cAL=cV1=None
        for i, row in enumerate(rows[:15]):
            cells = [norm(c) for c in row]
            if "id partido" in cells and "alias" in cells:
                hdr_idx = i
                cID = cells.index("id partido")
                cAL = cells.index("alias")
                cV1 = cells.index("equipo 1") if "equipo 1" in cells else None
                break
        if hdr_idx is None:
            continue
        found = True
        for row in rows[hdr_idx+1:]:
            pid = norm(row[cID]) if cID is not None and cID < len(row) else ""
            if pid in ("p115", "115"):
                alias = row[cAL] if cAL < len(row) else None
                val   = row[cV1] if (cV1 is not None and cV1 < len(row)) else None
                if alias is not None:
                    excel_etapa[norm(alias)] = val
        excel_info = f"hoja '{ws.title}', header fila {hdr_idx+1}, {len(excel_etapa)} aliases con P115"
        break
    if not found:
        excel_info = "no se encontro encabezado ID PARTIDO/ALIAS en ninguna hoja"
        excel_info += " | hojas: " + ", ".join(w.title for w in wb.worksheets)
except Exception as e:
    excel_info = f"ERROR leyendo Excel: {e}"

def excel_de(uid):
    u = umap.get(uid, {})
    for key in (norm(u.get("username")), norm(u.get("nombre"))):
        if key in excel_etapa:
            return excel_etapa[key]
    return None

# ---------- pts item F actuales ----------
bc.execute(f"""SELECT ag.apostador_id AS uid, ag.pred_etapa_paraguay AS pe,
                      COALESCE(pg.pts_etapa_paraguay,0) AS pts, COALESCE(pg.pts_total,0) AS gtot
               FROM apuesta_global ag
               LEFT JOIN puntaje_global pg
                 ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
               WHERE ag.torneo_id={TID}""")
rows = {r["uid"]: r for r in bc.fetchall()}

def uname(uid): return (umap.get(uid,{}).get("username") or f"U{uid}")

p("="*74)
p(" VERIFICACION ITEM F (Etapa Paraguay) — post-fix")
p("="*74)
p(f"Excel master: {os.path.basename(XLSX)}")
p(f"  lectura: {excel_info}")

# ---------- 1) HUGUITO ----------
p("\n[1] HUGUITO — candidatos (username/nombre con 'hugo' o 'huguito'):")
cands = [r for r in urows if ("hugo" in norm(r["username"]) or "huguito" in norm(r["username"])
                              or "hugo" in norm(r["nombre"]) or "huguito" in norm(r["nombre"]))]
for u in cands:
    uid = u["id"]; r = rows.get(uid)
    pe = r["pe"] if r else "(sin apuesta_global)"
    pts = r["pts"] if r else "-"
    via = "web (select)" if str(pe) in ("ronda16","ronda32","ronda32 ") else ("Excel/import" if pe else "-")
    p(f"    {u['username']:<12} (id={uid}) nombre={u['nombre']!r}")
    p(f"        pred_etapa BD = {pe!r}   via={via}   pts_F={pts}")
    p(f"        etapa escrita en Excel master = {excel_de(uid)!r}")

# ---------- 2) los 18 '8vos' (0->6) ----------
p("\n[2] Los '8vos' (deberian cobrar 6 tras el fix):")
ochos = [uid for uid,r in rows.items() if str(r["pe"]).lower()=="8vos"]
n6=0
for uid in sorted(ochos, key=lambda x: norm(uname(x))):
    r = rows[uid]
    if r["pts"]==6: n6+=1
    p(f"    {uname(uid):<12} pred=8vos  pts_F={r['pts']}  excel={excel_de(uid)!r}")
p(f"    -> {len(ochos)} apostadores '8vos', con 6 pts: {n6}")

# ---------- 3) los 10 remapeados ronda16->ronda32 (cherem etc.) ----------
p("\n[3] Los remapeados a 'ronda32' (eran 'ronda16'; deberian tener 0):")
r32 = [uid for uid,r in rows.items() if str(r["pe"]).lower()=="ronda32"]
n0=0
for uid in sorted(r32, key=lambda x: norm(uname(x))):
    r = rows[uid]
    if r["pts"]==0: n0+=1
    p(f"    {uname(uid):<12} pred=ronda32  pts_F={r['pts']}  excel={excel_de(uid)!r}")
p(f"    -> {len(r32)} remapeados, con 0 pts: {n0}")

# ---------- 4) totales ----------
tot6 = sum(1 for r in rows.values() if r["pts"]==6)
p("\n[4] TOTAL que cobran el item F (6 pts) ahora: %d" % tot6)
# distribucion
from collections import Counter
dist = Counter(str(r["pe"]) for r in rows.values())
p("    distribucion pred_etapa_paraguay: " + ", ".join(f"{k}={v}" for k,v in dist.most_common()))
p("="*74)

bc.close(); ac.close(); becbuc.close(); appdb.close()
