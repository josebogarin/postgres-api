# -*- coding: utf-8 -*-
"""
extract_ranking_excel.py — Fase 3c: mover _ranking_export_inner (~662 lineas)
a backend/app/services/reportes/ranking_excel.py. La ruta ranking_export queda
igual: se agrega en apostador_bets un alias de import para que su llamada a
_ranking_export_inner siga funcionando. Backup + ast + rollback. Idempotente.
"""
import ast
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "backend", "app", "api", "v1", "endpoints", "apostador_bets.py")
REPORTES_DIR = os.path.join(ROOT, "backend", "app", "services", "reportes")
NEW_MODULE = os.path.join(REPORTES_DIR, "ranking_excel.py")
BKPDIR = os.path.join(ROOT, "_backups")

START = "async def _ranking_export_inner(torneo_id: int, current, db):"
ANCHOR = '@router.get("/exportar-pronosticos/{torneo_id}",'

MODULE_HEADER = '''# -*- coding: utf-8 -*-
"""
ranking_excel.py — Excel de ranking con desglose por fase (Fase 3c).
Movido desde apostador_bets.py. Hoja 'Puntaje general' + una hoja por fase.
"""
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from sqlalchemy import text

from app.db.session import engine as _app_engine


'''

IMPORT_LINE = (
    "# _ranking_export_inner: movido a services/reportes/ranking_excel.py (Fase 3c)\n"
    "from app.services.reportes.ranking_excel import build_ranking_export as _ranking_export_inner\n\n\n"
)


def _backup(path):
    os.makedirs(BKPDIR, exist_ok=True)
    dst = os.path.join(BKPDIR, os.path.basename(path) + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak")
    shutil.copy2(path, dst); return dst


def _verify(path):
    try:
        ast.parse(open(path, encoding="utf-8").read()); return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError line {e.lineno}: {e.msg}"


def main():
    src = open(TARGET, encoding="utf-8").read()
    if "from app.services.reportes.ranking_excel import build_ranking_export" in src:
        print("[extract] ya aplicado. Skip."); return
    if src.count(START) != 1:
        print(f"[extract] ERROR START x{src.count(START)}. Abort."); sys.exit(1)
    if src.count(ANCHOR) != 1:
        print(f"[extract] ERROR ANCHOR x{src.count(ANCHOR)}. Abort."); sys.exit(1)

    i = src.find(START)
    k = src.find(ANCHOR)
    if k <= i:
        print("[extract] ERROR: ANCHOR antes de START. Abort."); sys.exit(1)

    func_text = src[i:k].rstrip() + "\n"
    func_renamed = func_text.replace(
        "async def _ranking_export_inner(", "async def build_ranking_export(", 1)

    os.makedirs(REPORTES_DIR, exist_ok=True)
    with open(NEW_MODULE, "w", encoding="utf-8") as f:
        f.write(MODULE_HEADER + func_renamed)
    ok, msg = _verify(NEW_MODULE)
    if not ok:
        os.remove(NEW_MODULE); print(f"[extract] modulo invalido ({msg}). Abort."); sys.exit(1)

    new_src = src[:i] + IMPORT_LINE + src[k:]
    bkp = _backup(TARGET)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_src)
    ok, msg = _verify(TARGET)
    if not ok:
        shutil.copy2(bkp, TARGET); print(f"[extract] apostador_bets invalido ({msg}). Restaurado {bkp}."); sys.exit(1)

    lb, la = len(src.splitlines()), len(new_src.splitlines())
    print(f"[extract] OK. apostador_bets.py: {lb} -> {la} lineas (-{lb-la}). "
          f"modulo: {len(func_renamed.splitlines())} lineas. backup: {bkp}")


if __name__ == "__main__":
    main()
