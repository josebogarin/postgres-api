# -*- coding: utf-8 -*-
"""Recibo v2: lista todos los partidos pendientes con items (desde BD) + nombre y apellido."""
import ast, re, shutil, subprocess, os
from datetime import datetime
HTML = r"C:\proyecto FAST API\backend\static\becbuc-live-playoffs.html"
PY   = r"C:\proyecto FAST API\backend\app\api\v1\endpoints\apostador_bets.py"
BKP  = r"C:\proyecto FAST API\_backups"
if not os.path.exists(HTML):
    base="/sessions/stoic-busy-euler/mnt/proyecto FAST API"
    HTML=base+"/backend/static/becbuc-live-playoffs.html"
    PY=base+"/backend/app/api/v1/endpoints/apostador_bets.py"
    BKP=base+"/_backups"
os.makedirs(BKP, exist_ok=True)

def vhtml(p):
    raw=open(p,'rb').read()
    if not raw.rstrip().endswith(b'</html>'): return False,'falta </html>'
    s=re.findall(rb'<script>([\s\S]*?)</script>',raw)
    r=subprocess.run(['node','--check'],input=s[-1],capture_output=True)
    return (r.returncode==0),('OK' if r.returncode==0 else r.stderr.decode(errors='replace')[:160])
def vpy(p):
    try: ast.parse(open(p,encoding='utf-8').read()); return True,'OK'
    except SyntaxError as e: return False,f'line {e.lineno}: {e.msg}'

def apply(path,repls,verifier):
    src=open(path,encoding='utf-8').read()
    for old,new in repls:
        c=src.count(old)
        if c!=1: raise SystemExit(f'count={c} (esperado 1) en {os.path.basename(path)}: {old[:70]!r}')
        src=src.replace(old,new,1)
    b=os.path.join(BKP,os.path.basename(path)+'.'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
    shutil.copy2(path,b); open(path,'w',encoding='utf-8').write(src)
    ok,msg=verifier(path)
    if not ok: shutil.copy2(b,path); raise SystemExit(f'VERIFY FALLO {os.path.basename(path)}: {msg} -> restaurado')
    print(f'OK {os.path.basename(path)} ({msg})')

# ── HTML repl 1: fuente de datos = partidos pendientes desde _userPreds ──
old1 = ("function _mpMostrarRecibo(saved, okSet, alias){\n"
        "  const rows=(saved||[]).filter(function(a){ return okSet.has(a.numero_fifa); });\n"
        "  if(!rows.length) return;\n"
        "  const fecha=new Date().toLocaleString('es');\n"
        "  let body='';\n"
        "  rows.forEach(function(a){\n"
        "    const m=(_bracket||[]).find(function(x){return x.num===a.numero_fifa;});\n")
new1 = ("function _mpMostrarRecibo(nombreFull, alias){\n"
        "  const _ko=(_bracket||[]).filter(function(x){return x.num>=73;}).sort(function(x,y){return x.num-y.num;});\n"
        "  const rows=_ko.filter(_mpEditable).map(function(m){ return {m:m, p:_userPreds[m.num]}; }).filter(function(r){ return r.p && r.p.pred_local!=null; });\n"
        "  if(!rows.length) return;\n"
        "  const fecha=new Date().toLocaleString('es');\n"
        "  let body='';\n"
        "  rows.forEach(function(r){\n"
        "    const m=r.m, a=r.p;\n")

# ── HTML repl 2: header con nombre y apellido + usuario ──
old2 = "+'<div style=\"font-size:13px;color:#333;margin-top:3px\">Apostador: <b>'+(alias||'')+'</b></div>'"
new2 = ("+'<div style=\"font-size:13px;color:#333;margin-top:3px\">Nombre: <b>'+(nombreFull||alias||'')+'</b></div>'\n"
        "    +'<div style=\"font-size:12px;color:#555\">Usuario: '+(alias||'')+'</div>'")

# ── HTML repl 3: call site ──
old3 = "    if(okN>0){ const okNums=new Set((d.resultados||[]).filter(function(x){return x.ok;}).map(function(x){return x.numero_fifa;})); _mpMostrarRecibo(ap, okNums, _viewAsName); }"
new3 = "    if(okN>0){ _mpMostrarRecibo(d.nombre||_viewAsName, _viewAsName); }"

# ── PY repl: devolver nombre completo ──
oldpy = '            "total": len(body.apuestas), "resultados": resultados, "apostador": username}'
newpy = '            "total": len(body.apuestas), "resultados": resultados, "apostador": username, "nombre": nombre_full}'

apply(HTML, [(old1,new1),(old2,new2),(old3,new3)], vhtml)
apply(PY,   [(oldpy,newpy)], vpy)
print("TODO OK.")
