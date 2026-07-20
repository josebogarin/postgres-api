# -*- coding: utf-8 -*-
"""Recibo de apuestas imprimible/PDF, auto al guardar con exito (live-playoffs)."""
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
    return (r.returncode==0),('OK' if r.returncode==0 else r.stderr.decode(errors='replace')[:160])

RECIBO = r"""
function _mpTeamName(m, id){
  if(!m) return '';
  if(m.local && m.local.id===id) return m.local.nombre;
  if(m.visitante && m.visitante.id===id) return m.visitante.nombre;
  return '';
}
function _mpCerrarRecibo(){ const o=document.getElementById('mpe-recibo-ov'); if(o) o.remove(); }
function _mpMostrarRecibo(saved, okSet, alias){
  const rows=(saved||[]).filter(function(a){ return okSet.has(a.numero_fifa); });
  if(!rows.length) return;
  const fecha=new Date().toLocaleString('es');
  let body='';
  rows.forEach(function(a){
    const m=(_bracket||[]).find(function(x){return x.num===a.numero_fifa;});
    const localN=(m&&m.local)?m.local.nombre:'?', visitN=(m&&m.visitante)?m.visitante.nombre:'?';
    const fase=_apuestasFaseLabel(m?m.tipo:'');
    const ex=[];
    if(a.pred_amarillas!=null) ex.push('Amarillas: '+a.pred_amarillas);
    if(a.pred_rojas!=null) ex.push('Rojas: '+a.pred_rojas);
    if(a.pred_var!=null) ex.push('VAR: '+a.pred_var);
    if(a.pred_penales_partido!=null) ex.push('Penales juego: '+a.pred_penales_partido);
    if(a.pred_minuto_gol!=null) ex.push('Min. 1er gol: '+a.pred_minuto_gol);
    if(a.pred_penales_local_tanda!=null||a.pred_penales_visitante_tanda!=null)
      ex.push('Tanda penales: '+(a.pred_penales_local_tanda!=null?a.pred_penales_local_tanda:'-')+'-'+(a.pred_penales_visitante_tanda!=null?a.pred_penales_visitante_tanda:'-'));
    if(a.pred_equipo_clasifica!=null){ const cn=_mpTeamName(m,a.pred_equipo_clasifica); if(cn) ex.push('Clasifica: '+cn); }
    body+='<div style="border-bottom:1px dotted #bbb;padding:7px 0">'
      +'<div style="font-size:13px"><b>P'+a.numero_fifa+'</b> '+localN+' vs '+visitN+' <span style="color:#777;font-size:11px">('+fase+')</span></div>'
      +'<div style="font-size:14px;margin-top:2px">Marcador: <b>'+a.pred_local+' - '+a.pred_visitante+'</b></div>'
      +(ex.length?'<div style="font-size:11px;color:#444;margin-top:2px">'+ex.join(' &middot; ')+'</div>':'')
      +'</div>';
  });
  const style='<style>@media print{ body>*:not(#mpe-recibo-ov){display:none!important;} '
    +'#mpe-recibo-ov{position:absolute!important;inset:0!important;background:#fff!important;padding:0!important;overflow:visible!important;} '
    +'.mpe-recibo-noprint{display:none!important;} #mpe-recibo{box-shadow:none!important;max-width:100%!important;border-radius:0!important;} }</style>';
  const html=style
    +'<div id="mpe-recibo-ov" style="position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,.78);display:flex;flex-direction:column;align-items:center;overflow:auto;padding:16px 10px">'
    +'<div id="mpe-recibo" style="background:#fff;color:#111;max-width:420px;width:100%;border-radius:12px;padding:18px;font-family:system-ui,-apple-system,Arial,sans-serif;box-sizing:border-box">'
    +'<div style="text-align:center;border-bottom:2px dashed #999;padding-bottom:8px;margin-bottom:8px">'
    +'<div style="font-size:18px;font-weight:800">BECBUC - Recibo de apuestas</div>'
    +'<div style="font-size:13px;color:#333;margin-top:3px">Apostador: <b>'+(alias||'')+'</b></div>'
    +'<div style="font-size:11px;color:#666">'+fecha+'</div></div>'
    +body
    +'<div style="border-top:2px dashed #999;margin-top:8px;padding-top:8px;text-align:center;font-size:10px;color:#666">Comprobante de pronostico - conservalo como respaldo</div>'
    +'</div>'
    +'<div class="mpe-recibo-noprint" style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;justify-content:center">'
    +'<button onclick="window.print()" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:12px 22px;font-size:14px;font-weight:700;cursor:pointer">Imprimir / Guardar PDF</button>'
    +'<button onclick="_mpCerrarRecibo()" style="background:#334155;color:#fff;border:none;border-radius:8px;padding:12px 22px;font-size:14px;cursor:pointer">Cerrar</button>'
    +'</div></div>';
  const prev=document.getElementById('mpe-recibo-ov'); if(prev) prev.remove();
  document.body.insertAdjacentHTML('beforeend', html);
  if(typeof twemoji!=='undefined'){ const ov=document.getElementById('mpe-recibo-ov'); if(ov) twemoji.parse(ov,{folder:'svg',ext:'.svg',base:'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/'}); }
}

function renderMiPronoEditor(){"""

anchor_r = "function renderMiPronoEditor(){"
new_r = RECIBO

anchor_save = ("    const rEl=document.getElementById('mpe-save-result'); if(rEl) rEl.innerHTML=out;\n"
               "    showToast('Guardado ✓ ('+okN+')');")
new_save = ("    const rEl=document.getElementById('mpe-save-result'); if(rEl) rEl.innerHTML=out;\n"
            "    if(okN>0){ const okNums=new Set((d.resultados||[]).filter(function(x){return x.ok;}).map(function(x){return x.numero_fifa;})); _mpMostrarRecibo(ap, okNums, _viewAsName); }\n"
            "    showToast('Guardado ✓ ('+okN+')');")

src=open(HTML,encoding='utf-8').read()
for old,new in [(anchor_r,new_r),(anchor_save,new_save)]:
    c=src.count(old)
    if c!=1: raise SystemExit(f'count={c} (esperado 1): {old[:60]!r}')
    src=src.replace(old,new,1)
b=os.path.join(BKP,os.path.basename(HTML)+'.'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
shutil.copy2(HTML,b); open(HTML,'w',encoding='utf-8').write(src)
ok,msg=verify(HTML)
if not ok: shutil.copy2(b,HTML); raise SystemExit(f'VERIFY FALLO {msg} -> restaurado')
print(f'OK ({msg})')
