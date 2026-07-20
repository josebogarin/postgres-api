# -*- coding: utf-8 -*-
"""
extract_puntajes_excel.py — Fase 3: mover el cuerpo del endpoint exportar_puntajes
a backend/app/services/reportes/puntajes_excel.py. La ruta queda delgada (delega).
Backup + ast en ambos archivos + rollback. Idempotente.
"""
import ast
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "backend", "app", "api", "v1", "endpoints", "apostador_bets.py")
REPORTES_DIR = os.path.join(ROOT, "backend", "app", "services", "reportes")
NEW_MODULE = os.path.join(REPORTES_DIR, "puntajes_excel.py")
BKPDIR = os.path.join(ROOT, "_backups")

DEF_LINE = "async def exportar_puntajes(torneo_id: int, db: DBSession, current: CurrentUser):"
RETURN_END = '        headers={"Content-Disposition": f\'attachment; filename="becbuc_puntajes_copa_{ts}.xlsx"\'},\n    )'

MODULE_HEADER = '''# -*- coding: utf-8 -*-
"""
puntajes_excel.py — Export Excel de puntajes (resumen + detalle) (Fase 3).
Movido desde apostador_bets.py. Lee las vistas v_copamundial_puntajes(_det).
"""
from datetime import datetime as _dt

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text


'''

WRAPPER_BODY = (
    "\n    from app.services.reportes.puntajes_excel import build_puntajes_export\n"
    "    return await build_puntajes_export(db, torneo_id)\n"
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
    if "from app.services.reportes.puntajes_excel import build_puntajes_export" in src:
        print("[extract] ya aplicado. Skip."); return
    if src.count(DEF_LINE) != 1:
        print(f"[extract] ERROR DEF_LINE x{src.count(DEF_LINE)}. Abort."); sys.exit(1)
    if src.count(RETURN_END) != 1:
        print(f"[extract] ERROR RETURN_END x{src.count(RETURN_END)}. Abort."); sys.exit(1)

    i = src.find(DEF_LINE)
    j = src.find(RETURN_END)
    j_end = j + len(RETURN_END)
    if j_end <= i:
        print("[extract] ERROR: RETURN antes de DEF. Abort."); sys.exit(1)

    body_text = src[i + len(DEF_LINE):j_end]           # cuerpo con indentacion (4 sp)
    service_func = "async def build_puntajes_export(db, torneo_id: int):" + body_text

    os.makedirs(REPORTES_DIR, exist_ok=True)
    with open(NEW_MODULE, "w", encoding="utf-8") as f:
        f.write(MODULE_HEADER + service_func + "\n")
    ok, msg = _verify(NEW_MODULE)
    if not ok:
        os.remove(NEW_MODULE); print(f"[extract] modulo invalido ({msg}). Abort."); sys.exit(1)

    new_route = DEF_LINE + WRAPPER_BODY
    new_src = src[:i] + new_route + src[j_end:]
    bkp = _backup(TARGET)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_src)
    ok, msg = _verify(TARGET)
    if not ok:
        shutil.copy2(bkp, TARGET); print(f"[extract] apostador_bets invalido ({msg}). Restaurado {bkp}."); sys.exit(1)

    lb, la = len(src.splitlines()), len(new_src.splitlines())
    print(f"[extract] OK. apostador_bets.py: {lb} -> {la} lineas (-{lb-la}). backup: {bkp}")


if __name__ == "__main__":
    main()
