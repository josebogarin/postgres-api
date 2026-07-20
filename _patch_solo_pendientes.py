# -*- coding: utf-8 -*-
"""Mi Prono: mostrar solo partidos pendientes (quitar seccion cotejo)."""
import re, shutil, subprocess, os
from datetime import datetime
HTML = r"C:\proyecto FAST API\backend\static\becbuc-live-playoffs.html"
BKP  = r"C:\proyecto FAST API\_backups"
if not os.path.exists(HTML):
    HTML = "/sessions/stoic-busy-euler/mnt/proyecto FAST API/backend/static/becbuc-live-playoffs.html"
    BKP  = "/sessions/stoic-busy-euler/mnt/proyecto FAST API/_backups"
os.makedirs(BKP, exist_ok=True)

def verify(p):
    raw=open(p,'rb').read()
    if not raw.rstrip().endswith(b'</html>'): return False,'falta </html>'
    s=re.findall(rb'<script>([\s\S]*?)</script>',raw)
    r=subprocess.run(['node','--check'],input=s[-1],capture_output=True)
    return (r.returncode==0),('OK' if r.returncode==0 else r.stderr.decode(errors='replace')[:120])

old = '''  html+='<div class="mpe-sec-hdr" style="padding:16px 12px 6px;margin-top:8px;font-size:14px;font-weight:800;color:#e2e8f0;border-top:1px solid #1e293b">📊 Partidos jugados (cotejo)</div>';
  if(!cotejo.length){
    html+='<div class="ap-empty" style="padding:14px;text-align:center;color:#6b7280">Todavía no hay partidos jugados.</div>';
  }else{
    cotejo.forEach(function(m){ html+=_mpCotejoCard(m); });
  }
'''
new = '''  // Mi Prono muestra SOLO partidos pendientes: seccion de cotejo (finalizados) oculta.
'''

src=open(HTML,encoding='utf-8').read()
c=src.count(old)
if c!=1: raise SystemExit(f'count={c} (esperado 1)')
src=src.replace(old,new,1)
b=os.path.join(BKP,os.path.basename(HTML)+'.'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
shutil.copy2(HTML,b); open(HTML,'w',encoding='utf-8').write(src)
ok,msg=verify(HTML)
if not ok: shutil.copy2(b,HTML); raise SystemExit(f'VERIFY FALLO {msg} -> restaurado')
print(f'OK ({msg})')
