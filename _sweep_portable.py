"""Barrido de portabilidad (AST): reemplaza literales string cuyo valor empieza
por 'C:\\proyecto FAST API' por rutas derivadas de __file__ (_BASE). Ignora
docstrings/comentarios. Valida con ast y no escribe si algo falla."""
import os, ast, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\proyecto FAST API"
H1 = "import os as _osp"
H2 = "_BASE = _osp.path.dirname(_osp.path.abspath(__file__))"

def strip_header(src):
    lines = src.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() == H1 and i + 1 < len(lines) and lines[i + 1].strip() == H2:
            i += 2
            continue
        out.append(lines[i]); i += 1
    return "\n".join(out)

def repl_for(value):
    rel = value[len(BASE):].lstrip("\\")
    if not rel:
        return "_BASE"
    parts = [p for p in rel.split("\\") if p]
    return "_osp.path.join(_BASE, " + ", ".join(repr(p) for p in parts) + ")"

def inject_header(src):
    lines = src.split("\n")
    ins = 0
    if lines and lines[0].startswith("#!"):
        ins = 1
    j = ins
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j < len(lines) and (lines[j].lstrip().startswith('"""') or lines[j].lstrip().startswith("'''")):
        q = lines[j].lstrip()[:3]
        if lines[j].count(q) >= 2:
            ins = j + 1
        else:
            k = j + 1
            while k < len(lines) and q not in lines[k]:
                k += 1
            ins = k + 1
    lines.insert(ins, H1 + "\n" + H2)
    return "\n".join(lines)

changed, failed, fstr = [], [], []
for f in glob.glob(os.path.join(ROOT, "*.py")):
    name = os.path.basename(f)
    if name.startswith("_sweep") or name == "safe_write.py":
        continue
    with open(f, encoding="utf-8") as fh:
        orig = fh.read()
    if BASE not in orig:
        continue
    work = strip_header(orig)
    try:
        tree = ast.parse(work)
    except SyntaxError as e:
        failed.append((name, "parse inicial: " + str(e))); continue
    edits = []
    has_fstring = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith(BASE):
            if node.end_lineno is None:
                continue
            edits.append((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, repl_for(node.value)))
        if isinstance(node, ast.JoinedStr):
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str) and BASE in v.value:
                    has_fstring = True
    if has_fstring:
        fstr.append(name)
    if not edits:
        if work != orig:
            try:
                ast.parse(work)
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(work)
                changed.append(name + " (header espurio removido)")
            except SyntaxError as e:
                failed.append((name, str(e)))
        continue
    wl = work.split("\n")
    for (sl, sc, el, ec, rep) in sorted(edits, key=lambda t: (t[0], t[1]), reverse=True):
        if sl == el:
            line = wl[sl - 1]
            wl[sl - 1] = line[:sc] + rep + line[ec:]
        else:
            first = wl[sl - 1][:sc]
            last = wl[el - 1][ec:]
            wl[sl - 1] = first + rep + last
            del wl[sl:el]
    new = "\n".join(wl)
    new = inject_header(new)
    try:
        ast.parse(new)
    except SyntaxError as e:
        failed.append((name, str(e))); continue
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(new)
    changed.append(name)

print("CAMBIADOS (%d):" % len(changed))
for n in changed: print("  ", n)
print("F-STRINGS con ruta (revisar a mano) (%d):" % len(fstr), fstr)
print("FALLARON (%d):" % len(failed))
for n, e in failed: print("  ", n, "->", e)
