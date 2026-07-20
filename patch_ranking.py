# -*- coding: utf-8 -*-
"""
patch_ranking.py — Wire del endpoint `ranking` a la capa de repositorio (Fase 2).

Reemplaza el bloque de 7 queries SQL crudas dentro de `ranking` por llamadas a
backend/app/repositories/ranking_repo.py. La agregacion en Python queda igual.
Splice entre START (unico) y el ANCHOR de la linea que sigue al bloque.
Hace backup + verifica sintaxis (ast) + rollback si falla. Idempotente.
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from safe_write import verify_py, _backup  # noqa: E402

TARGET = os.path.join(ROOT, "backend", "app", "api", "v1", "endpoints", "apostador_bets.py")

# START: primera linea del bloque a reemplazar (unica en el archivo)
START = (
    '    _ITEMS = [\n'
    '        "pts_resultado", "pts_marcador", "pts_amarillas", "pts_rojas",'
)
# ANCHOR: primera linea DESPUES del bloque (se conserva). Debe ser unica.
ANCHOR = '    _ZERO_CATS = {'

NEW_BODY = (
    "    # ── Datos via capa de repositorio (Fase 2: ranking_repo) ───────\n"
    "    from app.repositories import ranking_repo as _rr\n"
    "    rows                = await _rr.fetch_puntajes_por_item(db, torneo_id)\n"
    "    global_pts, glob_detalle_map = await _rr.fetch_globales(db, torneo_id)\n"
    "    clas_pts            = await _rr.fetch_grupos_p(db, torneo_id)\n"
    "    clasifica_ko_by_uid = await _rr.fetch_pts_equipo_ko(db, torneo_id)\n"
    "    peor_equipo_pts     = await _rr.fetch_peor_equipo_d(db, torneo_id)\n"
    "    fases_by_uid        = await _rr.fetch_fases_por_uid(db, torneo_id)\n"
    "    apostadores_all, user_map = await _rr.fetch_apostadores(\n"
    "        _app_engine, [r[\"apostador_id\"] for r in rows]\n"
    "    )\n\n"
)


def main():
    src = open(TARGET, encoding="utf-8").read()

    if "from app.repositories import ranking_repo" in src:
        print("[patch] ya aplicado (endpoint ya usa ranking_repo). Skip.")
        return

    if src.count(START) != 1:
        print(f"[patch] ERROR: START aparece {src.count(START)} veces (esperado 1). Abort.")
        sys.exit(1)
    if src.count(ANCHOR) != 1:
        print(f"[patch] ERROR: ANCHOR aparece {src.count(ANCHOR)} veces (esperado 1). Abort.")
        sys.exit(1)

    i = src.find(START)
    k = src.find(ANCHOR)
    if k <= i:
        print("[patch] ERROR: ANCHOR no esta despues de START. Abort.")
        sys.exit(1)

    new_src = src[:i] + NEW_BODY + src[k:]
    lines_before = len(src.splitlines())
    lines_after = len(new_src.splitlines())

    bkp = _backup(TARGET)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_src)

    ok, msg = verify_py(TARGET)
    if not ok:
        shutil.copy2(bkp, TARGET)
        print(f"[patch] VERIFY FAIL ({msg}). Restaurado desde backup: {bkp}")
        sys.exit(1)

    print(f"[patch] OK. apostador_bets.py: {lines_before} -> {lines_after} lineas "
          f"(-{lines_before - lines_after}). backup: {bkp}")


if __name__ == "__main__":
    main()
