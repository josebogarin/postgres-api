# -*- coding: utf-8 -*-
"""
patch_frontend_core.py — Fase 4 (piloto): extrae el bloque de banderas
(ISO_MAP + SPECIAL + isoFlag + flag) de becbuc-live.html a un nucleo compartido
static/js/becbuc-core.js, lo carga con <script src> antes del script principal,
y elimina la copia inline. Splice por indice (no re-transcribe emojis/acentos).
Backup + verificacion (node --check core + verify_html live) + rollback.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from safe_write import verify_html, _backup  # noqa: E402

LIVE = os.path.join(ROOT, "backend", "static", "becbuc-live.html")
COREDIR = os.path.join(ROOT, "backend", "static", "js")
COREJS = os.path.join(COREDIR, "becbuc-core.js")

HEADER = (
    "// becbuc-core.js - Nucleo compartido de las superficies BECBUC (Fase 4).\n"
    "// Componente 1: banderas por codigo ISO / nombre de equipo.\n"
    "// Cargar con <script src=\"/static/js/becbuc-core.js\"></script> ANTES del <script> principal.\n\n"
)

SCRIPT_ANCHOR = "</div><!-- /screen-main -->\n\n<script>"
SCRIPT_NEW = ("</div><!-- /screen-main -->\n\n"
              "<script src=\"/static/js/becbuc-core.js\"></script>\n<script>")


def main():
    src = open(LIVE, encoding="utf-8").read()
    if "becbuc-core.js" in src:
        print("[core] ya aplicado. Skip."); return

    # Guards de unicidad
    for marker in ("// FLAGS", "const ISO_MAP = {", "// DEMO MODE", SCRIPT_ANCHOR):
        if src.count(marker) != 1:
            print(f"[core] ERROR: marcador {marker!r} x{src.count(marker)} (esperado 1). Abort.")
            sys.exit(1)

    i_flags = src.index("// FLAGS")
    i_iso = src.index("const ISO_MAP = {")
    i_demo = src.index("// DEMO MODE")
    i_box = src.rindex("// ═", 0, i_demo)   # caja de comentario justo antes de DEMO
    if not (i_flags < i_iso < i_box < i_demo):
        print("[core] ERROR: orden de marcadores inesperado. Abort."); sys.exit(1)

    move_block = src[i_iso:i_box].rstrip() + "\n"

    # 1) escribir el nucleo
    os.makedirs(COREDIR, exist_ok=True)
    with open(COREJS, "w", encoding="utf-8") as f:
        f.write(HEADER + move_block)
    r = subprocess.run(["node", "--check", COREJS], capture_output=True)
    if r.returncode != 0:
        os.remove(COREJS)
        print("[core] core.js invalido:", r.stderr.decode(errors="replace")[:200]); sys.exit(1)

    # 2) quitar inline + insertar <script src>
    comment = "// FLAGS -> movido a /static/js/becbuc-core.js (Fase 4)\n\n"
    new_src = src[:i_flags] + comment + src[i_box:]
    new_src = new_src.replace(SCRIPT_ANCHOR, SCRIPT_NEW, 1)

    bkp = _backup(LIVE)
    with open(LIVE, "w", encoding="utf-8") as f:
        f.write(new_src)
    ok, msg = verify_html(LIVE)
    if not ok:
        import shutil
        shutil.copy2(bkp, LIVE)
        print(f"[core] verify_html FALLO ({msg}). Restaurado {bkp}."); sys.exit(1)

    lb, la = len(src.splitlines()), len(new_src.splitlines())
    print(f"[core] OK. becbuc-live.html: {lb} -> {la} lineas (-{lb-la}). "
          f"core.js: {len(move_block.splitlines())} lineas de datos. backup: {bkp}")


if __name__ == "__main__":
    main()
