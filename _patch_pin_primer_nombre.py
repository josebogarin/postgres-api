# -*- coding: utf-8 -*-
"""PIN = primer nombre (users.nombre) en vez de username. Backend + textos frontend."""
import ast, re, shutil, subprocess, os
from datetime import datetime

HTML = r"C:\proyecto FAST API\backend\static\becbuc-live-playoffs.html"
PY   = r"C:\proyecto FAST API\backend\app\api\v1\endpoints\apostador_bets.py"
BKP  = r"C:\proyecto FAST API\_backups"
if not os.path.exists(HTML):
    base = "/sessions/stoic-busy-euler/mnt/proyecto FAST API"
    HTML = base + "/backend/static/becbuc-live-playoffs.html"
    PY   = base + "/backend/app/api/v1/endpoints/apostador_bets.py"
    BKP  = base + "/_backups"
os.makedirs(BKP, exist_ok=True)

def backup(p):
    d = os.path.join(BKP, os.path.basename(p) + '.' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.bak')
    shutil.copy2(p, d); return d

def verify_html(p):
    raw = open(p, 'rb').read()
    if not raw.rstrip().endswith(b'</html>'): return False, 'Falta </html>'
    s = re.findall(rb'<script>([\s\S]*?)</script>', raw)
    if not s: return False, 'sin <script>'
    r = subprocess.run(['node','--check'], input=s[-1], capture_output=True)
    return (r.returncode==0), ('OK' if r.returncode==0 else r.stderr.decode(errors='replace')[:120])

def verify_py(p):
    try: ast.parse(open(p,encoding='utf-8').read()); return True,'OK'
    except SyntaxError as e: return False, f'line {e.lineno}: {e.msg}'

def apply(path, repls, verifier):
    src = open(path, encoding='utf-8').read()
    for old,new in repls:
        c = src.count(old)
        if c != 1: raise SystemExit(f'count={c} (esperado 1): {old[:70]!r}')
        src = src.replace(old,new,1)
    b = backup(path); open(path,'w',encoding='utf-8').write(src)
    ok,msg = verifier(path)
    if not ok: shutil.copy2(b,path); raise SystemExit(f'VERIFY FALLO {msg} -> restaurado')
    print(f'OK {os.path.basename(path)} ({msg})')

# Backend
py_old = '''        ur = await conn.execute(
            text("SELECT username FROM users WHERE id = :aid"),
            {"aid": body.apostador_id})
        urow = ur.first()
    if not urow:
        raise HTTPException(404, "Apostador no encontrado")
    username = (urow[0] or "").strip()
    if (body.pin or "").strip().upper() != username.upper():
        return {"ok": False, "error": "PIN incorrecto. El PIN es tu nombre de usuario."}'''
py_new = '''        ur = await conn.execute(
            text("SELECT username, nombre FROM users WHERE id = :aid"),
            {"aid": body.apostador_id})
        urow = ur.first()
    if not urow:
        raise HTTPException(404, "Apostador no encontrado")
    username = (urow[0] or "").strip()
    nombre_full = (urow[1] or "").strip()
    primer_nombre = nombre_full.split()[0] if nombre_full else username
    if (body.pin or "").strip().upper() != primer_nombre.upper():
        return {"ok": False, "error": "PIN incorrecto. El PIN es tu primer nombre."}'''

# Frontend (3 textos)
h1o = 'Se te pedirá un PIN (tu nombre de usuario) para confirmar.'
h1n = 'Se te pedirá un PIN (tu primer nombre) para confirmar.'
h2o = 'Ingresá tu PIN (tu nombre de usuario) para guardar '
h2n = 'Ingresá tu PIN (tu primer nombre) para guardar '
h3o = 'placeholder="PIN = tu usuario"'
h3n = 'placeholder="PIN = tu primer nombre"'

apply(PY,   [(py_old, py_new)], verify_py)
apply(HTML, [(h1o,h1n),(h2o,h2n),(h3o,h3n)], verify_html)
print("TODO OK.")
