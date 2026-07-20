# -*- coding: utf-8 -*-
"""
extract_auditoria_excel.py — Fase 3: mover _build_auditoria_workbook (~611 lineas)
del God file (apostador_bets.py) a backend/app/services/reportes/auditoria_excel.py.

En apostador_bets queda un wrapper delgado que delega. Copia las 2 constantes de
fase que la funcion usa (para evitar import circular). Backup + ast en AMBOS
archivos + rollback si algo falla. Idempotente.
"""
import ast
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "backend", "app", "api", "v1", "endpoints", "apostador_bets.py")
REPORTES_DIR = os.path.join(ROOT, "backend", "app", "services", "reportes")
NEW_MODULE = os.path.join(REPORTES_DIR, "auditoria_excel.py")
BKPDIR = os.path.join(ROOT, "_backups")

START = "async def _build_auditoria_workbook(db, torneo_id: int):"
ANCHOR = '@router.get("/transparencia/{torneo_id}",\n            summary='

MODULE_HEADER = '''# -*- coding: utf-8 -*-
"""
auditoria_excel.py — Generacion del Workbook de auditoria/transparencia (Fase 3).

Movido desde apostador_bets.py (God file). Construye el Excel unico usado por
las salidas de export (Auditoria, Transparencia, Puntos por fase).
Comportamiento identico al original.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.session import engine as _app_engine

# Constantes de fase (copiadas de apostador_bets para no acoplar al endpoint)
_PHASE_ORDER = ["grupo", "ronda32", "ronda16", "cuartos", "semis", "tercer_puesto", "final"]
_PHASE_LABELS_FULL = {
    "grupo": "Fase de grupos", "ronda32": "Ronda de 32", "ronda16": "Octavos de final",
    "cuartos": "Cuartos de final", "semis": "Semifinales",
    "tercer_puesto": "Tercer puesto", "final": "Final",
}


'''

WRAPPER = '''async def _build_auditoria_workbook(db, torneo_id: int):
    """Delegado a services/reportes/auditoria_excel (Fase 3). Ver ese modulo."""
    from app.services.reportes.auditoria_excel import build_auditoria_workbook
    return await build_auditoria_workbook(db, torneo_id)
'''


def _backup(path):
    os.makedirs(BKPDIR, exist_ok=True)
    dst = os.path.join(BKPDIR, os.path.basename(path) + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak")
    shutil.copy2(path, dst)
    return dst


def _verify(path):
    try:
        ast.parse(open(path, encoding="utf-8").read())
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError line {e.lineno}: {e.msg}"


def main():
    src = open(TARGET, encoding="utf-8").read()

    if os.path.exists(NEW_MODULE) and "from app.services.reportes.auditoria_excel import build_auditoria_workbook" in src:
        print("[extract] ya aplicado. Skip.")
        return

    if src.count(START) != 1:
        print(f"[extract] ERROR: START x{src.count(START)} (esperado 1). Abort."); sys.exit(1)
    if src.count(ANCHOR) != 1:
        print(f"[extract] ERROR: ANCHOR x{src.count(ANCHOR)} (esperado 1). Abort."); sys.exit(1)

    i = src.find(START)
    k = src.find(ANCHOR)
    if k <= i:
        print("[extract] ERROR: ANCHOR antes de START. Abort."); sys.exit(1)

    func_text = src[i:k].rstrip() + "\n"
    func_renamed = func_text.replace(
        "async def _build_auditoria_workbook(", "async def build_auditoria_workbook(", 1)

    # 1) escribir modulo nuevo
    os.makedirs(REPORTES_DIR, exist_ok=True)
    init_path = os.path.join(REPORTES_DIR, "__init__.py")
    if not os.path.exists(init_path):
        open(init_path, "w", encoding="utf-8").write(
            '"""Servicios de reportes/export (Fase 3)."""\n')
    with open(NEW_MODULE, "w", encoding="utf-8") as f:
        f.write(MODULE_HEADER + func_renamed)
    ok, msg = _verify(NEW_MODULE)
    if not ok:
        os.remove(NEW_MODULE)
        print(f"[extract] modulo nuevo invalido ({msg}). Abort."); sys.exit(1)

    # 2) patchear apostador_bets con el wrapper
    new_src = src[:i] + WRAPPER + "\n\n" + src[k:]
    bkp = _backup(TARGET)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_src)
    ok, msg = _verify(TARGET)
    if not ok:
        shutil.copy2(bkp, TARGET)
        print(f"[extract] apostador_bets invalido ({msg}). Restaurado {bkp}. Abort."); sys.exit(1)

    lb, la = len(src.splitlines()), len(new_src.splitlines())
    print(f"[extract] OK. apostador_bets.py: {lb} -> {la} lineas (-{lb-la}).")
    print(f"[extract] nuevo modulo: {NEW_MODULE} ({len(func_renamed.splitlines())} lineas de funcion).")
    print(f"[extract] backup: {bkp}")


if __name__ == "__main__":
    main()
