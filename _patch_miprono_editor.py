import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""
Patch: Editor de apuestas en tab Mi Prono (becbuc-live-playoffs.html) + endpoint
POST /live-guardar-apuestas (apostador_bets.py). Con backup + verificacion + rollback.
"""
import ast, re, shutil, subprocess, sys, os
from datetime import datetime

HTML = _osp.path.join(_BASE, 'backend', 'static', 'becbuc-live-playoffs.html')
PY   = _osp.path.join(_BASE, 'backend', 'app', 'api', 'v1', 'endpoints', 'apostador_bets.py')
BKP  = _osp.path.join(_BASE, '_backups')
os.makedirs(BKP, exist_ok=True)

# Permite correr desde el sandbox Linux (paths montados) o Windows.
if not os.path.exists(HTML):
    HTML = "/sessions/stoic-busy-euler/mnt/proyecto FAST API/backend/static/becbuc-live-playoffs.html"
    PY   = "/sessions/stoic-busy-euler/mnt/proyecto FAST API/backend/app/api/v1/endpoints/apostador_bets.py"
    BKP  = "/sessions/stoic-busy-euler/mnt/proyecto FAST API/_backups"
    os.makedirs(BKP, exist_ok=True)

def backup(p):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    d = os.path.join(BKP, os.path.basename(p) + '.' + ts + '.bak')
    shutil.copy2(p, d); return d

def verify_html(p):
    raw = open(p, 'rb').read()
    if not raw.rstrip().endswith(b'</html>'):
        return False, 'Falta </html>'
    scripts = re.findall(rb'<script>([\s\S]*?)</script>', raw)
    if not scripts:
        return False, 'sin <script>'
    r = subprocess.run(['node', '--check'], input=scripts[-1], capture_output=True)
    if r.returncode != 0:
        return False, 'JS SyntaxError: ' + r.stderr.decode(errors='replace').strip().split(chr(10))[0]
    return True, 'OK'

def verify_py(p):
    try:
        ast.parse(open(p, encoding='utf-8').read()); return True, 'OK'
    except SyntaxError as e:
        return False, 'SyntaxError line %s: %s' % (e.lineno, e.msg)

def apply(path, repls, verifier):
    src = open(path, encoding='utf-8').read()
    for old, new in repls:
        c = src.count(old)
        if c != 1:
            raise SystemExit('ANCHOR count=%d (esperado 1) en %s:\n  %r' % (c, os.path.basename(path), old[:90]))
        src = src.replace(old, new, 1)
    b = backup(path)
    open(path, 'w', encoding='utf-8').write(src)
    ok, msg = verifier(path)
    if not ok:
        shutil.copy2(b, path)
        raise SystemExit('VERIFY FALLO en %s: %s -> restaurado desde %s' % (os.path.basename(path), msg, b))
    print('OK %s (%s) backup=%s' % (os.path.basename(path), msg, os.path.basename(b)))

# ─────────────────────────────────────────────────────────────────────────────
# 1) BLOQUE JS del editor (se inserta antes de function renderMiProno)
# ─────────────────────────────────────────────────────────────────────────────
JS_BLOCK = r"""
// ===== EDITOR DE APUESTAS (Mi Prono) — cargar/modificar partidos no jugados =====
let _blockedFases = null;   // Set de tipos de fase bloqueada

async function _loadBlockedFases(){
  try{
    const r = await api('/api/v1/bets/fases-bloqueo/'+_torneoId);
    const d = await r.json();
    const arr = Array.isArray(d) ? d : (d.fases||[]);
    _blockedFases = new Set(arr.filter(function(f){return f.bloqueada;}).map(function(f){return f.tipo;}));
  }catch(e){ _blockedFases = new Set(); }
  if(_activeTab==='miprono') renderMiPronoEditor();
}

function _mpEditable(m){
  if(m.finalizado) return false;
  if(m.en_vivo || m.estado==='en_juego') return false;
  if(_blockedFases && _blockedFases.has(m.tipo)) return false;
  if(!m.local || !m.visitante || !m.local.id || !m.visitante.id) return false;
  return true;
}

function _scrollToMpCard(num){
  const c = document.getElementById('mp-card-'+num);
  if(!c) return;
  c.scrollIntoView({behavior:'smooth', block:'center'});
  c.style.transition='box-shadow .3s';
  c.style.boxShadow='0 0 0 2px #f59e0b';
  setTimeout(function(){ c.style.boxShadow=''; }, 1600);
}

function _mpNumInput(id, val, ph, mn, mx){
  const v = (val!==null && val!==undefined && val!=='') ? val : '';
  return '<input id="'+id+'" type="number" inputmode="numeric"'
    + (mn!=null?' min="'+mn+'"':'') + (mx!=null?' max="'+mx+'"':'')
    + ' value="'+v+'" placeholder="'+(ph||'')+'"'
    + ' style="width:54px;background:#0b1120;border:1px solid #334155;color:#e2e8f0;border-radius:6px;padding:5px 6px;text-align:center;font-size:14px">';
}

function _mpEdRow(letter, icon, label, inputHtml){
  return '<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:1px solid #0f1225">'
    + '<span style="width:26px;color:#64748b;font-weight:700;font-size:12px">'+letter+'</span>'
    + '<span style="width:22px;font-size:16px">'+icon+'</span>'
    + '<span style="flex:1;color:#cbd5e1;font-size:13px">'+label+'</span>'
    + '<span>'+inputHtml+'</span></div>';
}

function _mpEditorCard(m){
  const num=m.num;
  const p=_userPreds[num]||{};
  const localN=(m.local&&m.local.nombre)||'TBD', visitN=(m.visitante&&m.visitante.nombre)||'TBD';
  const flagL=teamFlag(localN,(m.local&&m.local.iso)||''), flagV=teamFlag(visitN,(m.visitante&&m.visitante.iso)||'');
  const faseLabel=_apuestasFaseLabel(m.tipo||'');
  const fechaStr=m.fecha?fmtFechaCorta(m.fecha):'';
  const locS=localN.split(' ')[0], visS=visitN.split(' ')[0];
  const locId=(m.local&&m.local.id)||'', visId=(m.visitante&&m.visitante.id)||'';
  const pec=(p.pred_equipo_clasifica!=null)?p.pred_equipo_clasifica:null;
  const mult=isPyMatch(localN,visitN)?2:1;
  let h='<div class="ap-match-card" id="mp-card-'+num+'" data-num="'+num+'" data-edit="1">';
  h+='<div class="ap-match-hdr"><span class="ap-match-num">P'+num+'</span>'
    +'<span class="ap-match-teams">'+flagL+' '+localN+' <small style="color:#475569;font-size:10px">vs</small> '+visitN+' '+flagV+'</span>'
    +'<span class="ap-match-fase">'+faseLabel+(mult>1?' ×2🇵🇾':'')+'</span></div>';
  h+='<div style="display:flex;align-items:center;justify-content:center;gap:10px;padding:11px 6px;background:#060c18">'
    +'<span style="font-size:12px;color:#94a3b8;flex:1;text-align:right;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+locS+'</span>'
    +_mpNumInput('mpe-'+num+'-pl', p.pred_local, '', 0, 99)
    +'<span style="color:#475569">–</span>'
    +_mpNumInput('mpe-'+num+'-pv', p.pred_visitante, '', 0, 99)
    +'<span style="font-size:12px;color:#94a3b8;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+visS+'</span>'
    +'</div>';
  h+='<div class="ai-items-wrap">';
  h+=_mpEdRow('J','🟨','Amarillas',       _mpNumInput('mpe-'+num+'-j', p.pred_amarillas,'0',0,60));
  h+=_mpEdRow('K','🟥','Rojas',           _mpNumInput('mpe-'+num+'-k', p.pred_rojas,'0',0,20));
  h+=_mpEdRow('L','📺','VAR',             _mpNumInput('mpe-'+num+'-l', p.pred_var,'0',0,20));
  h+=_mpEdRow('M','🥅','Penales (juego)', _mpNumInput('mpe-'+num+'-m', p.pred_penales_partido,'0',0,10));
  h+=_mpEdRow('N','⏱','Minuto 1er gol',        _mpNumInput('mpe-'+num+'-n', p.pred_minuto_gol,'min',1,130));
  h+='<div class="ai-section-lbl">⚡ Definición por penales</div>';
  h+=_mpEdRow('Ol','⚡','Tanda '+locS, _mpNumInput('mpe-'+num+'-ol', p.pred_penales_local_tanda,'0',0,30));
  h+=_mpEdRow('Ov','⚡','Tanda '+visS, _mpNumInput('mpe-'+num+'-ov', p.pred_penales_visitante_tanda,'0',0,30));
  const sel='<select id="mpe-'+num+'-p" style="background:#0b1120;border:1px solid #334155;color:#e2e8f0;border-radius:6px;padding:5px 6px;font-size:13px">'
    +'<option value="">—</option>'
    +'<option value="'+locId+'"'+(pec===locId?' selected':'')+'>'+locS+'</option>'
    +'<option value="'+visId+'"'+(pec===visId?' selected':'')+'>'+visS+'</option></select>';
  h+=_mpEdRow('P','🏅','Clasifica', sel);
  h+='</div>';
  if(fechaStr) h+='<div class="ap-match-fecha">📅 '+fechaStr+'</div>';
  h+='</div>';
  return h;
}

function _miItemRow(letter, icon, label, realVal, predVal, ptsVal){
  const realStr=(realVal!==null&&realVal!==undefined)?String(realVal):'–';
  const predStr=(predVal!==null&&predVal!==undefined)?String(predVal):'–';
  const rowCls=(ptsVal>0)?'ai-row ai-hit':'ai-row';
  let ptsFrag;
  if(ptsVal===null||ptsVal===undefined) ptsFrag='<span style="color:#334">–</span>';
  else if(ptsVal>0) ptsFrag='<span style="color:#22c55e;font-weight:800">+'+ptsVal+'</span>';
  else ptsFrag='<span style="color:#475569">0</span>';
  return '<div class="'+rowCls+'"><span class="ai-letter">'+letter+'</span><span class="ai-icon">'+icon+'</span><span class="ai-label">'+label+'</span><span class="ai-pred">'+predStr+'</span><span class="ai-real">'+realStr+'</span><span class="ai-pts">'+ptsFrag+'</span></div>';
}

function _mpCotejoCard(m){
  const num=m.num;
  const pred=_userPreds[num]||null;
  const hasPred=pred!==null && pred.pred_local!==null && pred.pred_local!==undefined;
  const localN=(m.local&&m.local.nombre)||'TBD', visitN=(m.visitante&&m.visitante.nombre)||'TBD';
  const flagL=teamFlag(localN,(m.local&&m.local.iso)||''), flagV=teamFlag(visitN,(m.visitante&&m.visitante.iso)||'');
  const faseLabel=_apuestasFaseLabel(m.tipo||'');
  const mult=isPyMatch(localN,visitN)?2:1;
  const done=m.finalizado, live=m.en_vivo||m.estado==='en_juego';
  const gl=(m.gl!=null)?m.gl:null, gv=(m.gv!=null)?m.gv:null;
  const penL=(m.pen_l!=null)?m.pen_l:null, penV=(m.pen_v!=null)?m.pen_v:null;
  const pl=pred?(pred.pred_local!=null?pred.pred_local:null):null;
  const pv=pred?(pred.pred_visitante!=null?pred.pred_visitante:null):null;
  const cls=_apuestasCls(pl,pv,gl,gv);
  const clsIcon=cls==='ap-pleno'?'✅':cls==='ap-res'?'🟡':cls==='ap-miss'?'❌':'⏳';
  const clsColor=cls==='ap-pleno'?'#22c55e':cls==='ap-res'?'#eab308':cls==='ap-miss'?'#ef4444':'#475569';
  const scoreReal=(gl!=null)?(gl+'–'+gv):'–';
  const scorePred=hasPred?(pl+'–'+pv):'Sin prono';
  let items='';
  const rH=(gl!=null)?(gl>gv?'L':gl<gv?'V':'E'):null;
  const pH=hasPred?(pl>pv?'L':pl<pv?'V':'E'):null;
  items+=_miItemRow('H','⚽','Resultado',rH,pH, done?(pred?pred.pts_resultado:null):null);
  items+=_miItemRow('I','🎯','Marcador exacto',(gl!=null)?(gl+'-'+gv):null,hasPred?(pl+'-'+pv):null, done?(pred?pred.pts_marcador:null):null);
  if(pred&&(pred.pred_amarillas!=null||pred.amarillas!=null))
    items+=_miItemRow('J','🟨','Amarillas',(done||live)?pred.amarillas:null,pred.pred_amarillas, done?pred.pts_amarillas:null);
  if(pred&&(pred.pred_rojas!=null||pred.rojas!=null))
    items+=_miItemRow('K','🟥','Rojas',(done||live)?pred.rojas:null,pred.pred_rojas, done?pred.pts_rojas:null);
  if(pred&&(pred.pred_var!=null||pred.decisiones_var!=null))
    items+=_miItemRow('L','📺','VAR',(done||live)?pred.decisiones_var:null,pred.pred_var, done?pred.pts_var:null);
  if(pred&&(pred.pred_penales_partido!=null||pred.penales_partido!=null))
    items+=_miItemRow('M','🥅','Penales (juego)',(done||live)?pred.penales_partido:null,pred.pred_penales_partido, done?pred.pts_penales_partido:null);
  if(pred&&(pred.pred_minuto_gol!=null||pred.minuto_primer_gol!=null))
    items+=_miItemRow('N','⏱','Minuto gol',(done||live)?pred.minuto_primer_gol:null,pred.pred_minuto_gol, done?pred.pts_minuto:null);
  const pOl=pred?(pred.pred_penales_local_tanda!=null?pred.pred_penales_local_tanda:null):null;
  const pOv=pred?(pred.pred_penales_visitante_tanda!=null?pred.pred_penales_visitante_tanda:null):null;
  if(penL!==null||pOl!==null||pOv!==null){
    const locS=localN.split(' ')[0], visS=visitN.split(' ')[0];
    items+='<div class="ai-section-lbl">⚡ Definición por penales</div>';
    const hitOl=done&&pOl!==null&&penL!==null&&pOl===penL, hitOv=done&&pOv!==null&&penV!==null&&pOv===penV;
    items+=_miItemRow('Ol','⚡','Tanda '+locS,penL,pOl, done&&penL!==null?(hitOl?2*mult:0):null);
    items+=_miItemRow('Ov','⚡','Tanda '+visS,penV,pOv, done&&penV!==null?(hitOv?2*mult:0):null);
  }
  const predPId=pred?(pred.pred_equipo_clasifica!=null?pred.pred_equipo_clasifica:null):null;
  const realEcId=pred?(pred.equipo_clasificado_id!=null?pred.equipo_clasificado_id:null):null;
  const locId=(m.local&&m.local.id)||null, visId=(m.visitante&&m.visitante.id)||null;
  const realEcNom=realEcId?(realEcId===locId?localN.split(' ')[0]:(realEcId===visId?visitN.split(' ')[0]:'?')):null;
  const predEcNom=predPId?(predPId===locId?localN.split(' ')[0]:(predPId===visId?visitN.split(' ')[0]:'?')):null;
  if(predPId!==null||realEcId!==null)
    items+=_miItemRow('P','🏅','Clasifica',realEcNom,predEcNom, done?(pred?pred.pts_equipo:null):null);
  const totalPts=done?(pred?(pred.pts_total!=null?pred.pts_total:0):0):null;
  const totalRow=(done&&hasPred)?'<div class="ai-total">Total partido: <strong style="color:#f59e0b">'+(totalPts||0)+' pts'+(mult>1?' ×2🇵🇾':'')+'</strong></div>':'';
  const itemsBlock='<div class="ai-items-wrap"><div class="ai-hdr"><span></span><span></span><span></span><span style="text-align:right">Prono</span><span style="text-align:right">Real</span><span style="text-align:right">Pts</span></div>'+items+totalRow+'</div>';
  return '<div class="ap-match-card" id="mp-card-'+num+'" data-num="'+num+'">'
    +'<div class="ap-match-hdr"><span class="ap-match-num">P'+num+'</span>'
    +'<span class="ap-match-teams">'+flagL+' '+localN+' <small style="color:#475569;font-size:10px">vs</small> '+visitN+' '+flagV+'</span>'
    +'<span class="ap-match-fase">'+faseLabel+'</span>'+(live?'<span class="ap-live-badge">EN VIVO</span>':'')+'</div>'
    +'<div class="ai-score-row"><div class="ai-score-col"><div class="ai-score-lbl">REAL</div><div class="ai-score-val" style="color:'+((done||live)?'#e2e8f0':'#475569')+'">'+scoreReal+'</div></div>'
    +'<div style="font-size:24px">'+clsIcon+'</div>'
    +'<div class="ai-score-col"><div class="ai-score-lbl">TU PRONO</div><div class="ai-score-val" style="color:'+(hasPred?clsColor:'#475569')+'">'+scorePred+'</div></div></div>'
    +itemsBlock+'</div>';
}

function renderMiPronoEditor(){
  const el=document.getElementById('mp-content');
  if(!el) return;
  if(!_viewAsId){
    el.innerHTML='<div class="ap-empty" style="padding:24px;text-align:center;color:#6b7280">Seleccioná tu nombre en la barra superior para cargar o ver tus apuestas</div>';
    return;
  }
  if(_blockedFases===null){ _blockedFases=new Set(); _loadBlockedFases(); }
  const ko=(_bracket||[]).filter(function(m){return m.num>=73;}).sort(function(a,b){return a.num-b.num;});
  const editables=ko.filter(_mpEditable);
  const cotejo=ko.filter(function(m){return m.finalizado||m.en_vivo||m.estado==='en_juego';});
  let html='';
  html+='<div class="mpe-sec-hdr" style="padding:12px 12px 6px;font-size:14px;font-weight:800;color:#e2e8f0">📝 Cargar / modificar apuestas <small style="color:#6b7280;font-weight:500">(partidos no jugados)</small></div>';
  if(!editables.length){
    html+='<div class="ap-empty" style="padding:14px;text-align:center;color:#6b7280">No hay partidos abiertos para cargar apuestas ahora.</div>';
  }else{
    editables.forEach(function(m){ html+=_mpEditorCard(m); });
    html+='<div style="padding:14px 10px 6px;text-align:center">'
      +'<button onclick="_mpGuardarClick()" style="background:#16a34a;color:#fff;border:none;border-radius:10px;padding:12px 30px;font-size:15px;font-weight:800;cursor:pointer">💾 Guardar apuestas</button>'
      +'<div style="font-size:11px;color:#6b7280;margin-top:6px">Se te pedirá un PIN (tu nombre de usuario) para confirmar.</div>'
      +'<div id="mpe-save-result" style="margin-top:10px"></div></div>';
  }
  html+='<div class="mpe-sec-hdr" style="padding:16px 12px 6px;margin-top:8px;font-size:14px;font-weight:800;color:#e2e8f0;border-top:1px solid #1e293b">📊 Partidos jugados (cotejo)</div>';
  if(!cotejo.length){
    html+='<div class="ap-empty" style="padding:14px;text-align:center;color:#6b7280">Todavía no hay partidos jugados.</div>';
  }else{
    cotejo.forEach(function(m){ html+=_mpCotejoCard(m); });
  }
  el.innerHTML=html;
  if(typeof twemoji!=='undefined'){ twemoji.parse(el,{folder:'svg',ext:'.svg',base:'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/'}); }
}

function _mpCollectApuestas(){
  const cards=document.querySelectorAll('#mp-content .ap-match-card[data-edit="1"]');
  const out=[];
  cards.forEach(function(card){
    const num=+card.getAttribute('data-num');
    const g=function(id){ const e=document.getElementById('mpe-'+num+'-'+id); return e?e.value.trim():''; };
    const pl=g('pl'), pv=g('pv');
    if(pl===''||pv==='') return;
    const nn=function(v){ return v===''?null:parseInt(v,10); };
    out.push({
      numero_fifa:num,
      pred_local:parseInt(pl,10),
      pred_visitante:parseInt(pv,10),
      pred_amarillas:nn(g('j')),
      pred_rojas:nn(g('k')),
      pred_var:nn(g('l')),
      pred_penales_partido:nn(g('m')),
      pred_minuto_gol:nn(g('n')),
      pred_penales_local_tanda:nn(g('ol')),
      pred_penales_visitante_tanda:nn(g('ov')),
      pred_equipo_clasifica:nn(g('p'))
    });
  });
  return out;
}

function _mpGuardarClick(){
  const ap=_mpCollectApuestas();
  const rEl=document.getElementById('mpe-save-result');
  if(!ap.length){ if(rEl) rEl.innerHTML='<span style="color:#f59e0b">Cargá al menos el marcador (local–visitante) de un partido.</span>'; return; }
  _mpShowPinModal(ap.length);
}

function _mpClosePin(){ const o=document.getElementById('mpe-pin-ov'); if(o) o.remove(); }

function _mpShowPinModal(n){
  _mpClosePin();
  const html='<div id="mpe-pin-ov" style="position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:99999;display:flex;align-items:center;justify-content:center">'
    +'<div style="background:#0f172a;border:1px solid #334155;border-radius:14px;padding:22px;width:300px;max-width:90vw;text-align:center">'
    +'<div style="font-size:16px;font-weight:800;color:#e2e8f0;margin-bottom:6px">🔒 Confirmar apuestas</div>'
    +'<div style="font-size:12px;color:#94a3b8;margin-bottom:12px">Ingresá tu PIN (tu nombre de usuario) para guardar '+n+' partido(s).</div>'
    +'<input id="mpe-pin-inp" type="text" autocomplete="off" placeholder="PIN = tu usuario" style="width:100%;box-sizing:border-box;background:#0b1120;border:1px solid #334155;color:#e2e8f0;border-radius:8px;padding:10px;font-size:15px;text-align:center;margin-bottom:12px">'
    +'<div id="mpe-pin-msg" style="font-size:12px;min-height:16px;margin-bottom:8px"></div>'
    +'<div style="display:flex;gap:8px">'
    +'<button onclick="_mpClosePin()" style="flex:1;background:#334155;color:#e2e8f0;border:none;border-radius:8px;padding:10px;cursor:pointer">Cancelar</button>'
    +'<button id="mpe-pin-ok" onclick="_mpDoSave()" style="flex:1;background:#16a34a;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:700;cursor:pointer">Guardar</button>'
    +'</div></div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
  const inp=document.getElementById('mpe-pin-inp');
  if(inp){ inp.focus(); inp.addEventListener('keydown',function(e){ if(e.key==='Enter') _mpDoSave(); }); }
}

async function _mpDoSave(){
  const inp=document.getElementById('mpe-pin-inp');
  const msg=document.getElementById('mpe-pin-msg');
  const okb=document.getElementById('mpe-pin-ok');
  const pin=inp?inp.value.trim():'';
  if(!pin){ if(msg){ msg.style.color='#f59e0b'; msg.textContent='Ingresá tu PIN.'; } return; }
  const ap=_mpCollectApuestas();
  if(!ap.length){ if(msg){ msg.style.color='#f59e0b'; msg.textContent='No hay apuestas para guardar.'; } return; }
  if(okb){ okb.disabled=true; okb.textContent='Guardando…'; }
  try{
    const r=await api('/api/v1/bets/live-guardar-apuestas/'+_torneoId,{
      method:'POST', body:JSON.stringify({apostador_id:_viewAsId, pin:pin, apuestas:ap})
    });
    const d=await r.json();
    if(!d.ok && d.error){
      if(msg){ msg.style.color='#f87171'; msg.textContent=d.error; }
      if(okb){ okb.disabled=false; okb.textContent='Guardar'; }
      return;
    }
    _mpClosePin();
    const okN=(d.resultados||[]).filter(function(x){return x.ok;}).length;
    const errs=(d.resultados||[]).filter(function(x){return !x.ok;});
    await loadUserPredictions(_viewAsId);
    renderMiPronoEditor();
    let out='<div style="color:#22c55e;font-weight:700">✅ '+okN+' apuesta(s) guardada(s).</div>';
    if(errs.length) out+='<div style="color:#f59e0b;font-size:11px;margin-top:4px">'+errs.map(function(e){return 'P'+e.numero_fifa+': '+e.msg;}).join('<br>')+'</div>';
    const rEl=document.getElementById('mpe-save-result'); if(rEl) rEl.innerHTML=out;
    showToast('Guardado ✓ ('+okN+')');
  }catch(e){
    if(msg){ msg.style.color='#f87171'; msg.textContent='Error: '+(e&&e.message?e.message:e); }
    if(okb){ okb.disabled=false; okb.textContent='Guardar'; }
  }
}
// ===== FIN EDITOR DE APUESTAS =====

"""

anchor_html = ("function renderMiProno(p) {\n"
               "  const el = document.getElementById('mp-content');\n"
               "  if (!el) return;")
new_html = (JS_BLOCK
            + "function renderMiProno(p){ return renderMiPronoEditor(); }\n\n"
            + "function _renderMiProno_OLD(p) {\n"
            + "  const el = document.getElementById('mp-content');\n"
            + "  if (!el) return;")

anchor_sel = ("function selectMatch(num, matchObj) {\n"
              "  _selectedMatchNum = num;\n"
              "  setTab('scores');\n"
              "  renderMatchDetail(matchObj || _bracket.find(m=>m.num===num));\n"
              "}")
new_sel = ("function selectMatch(num, matchObj) {\n"
           "  _selectedMatchNum = num;\n"
           "  setTab('miprono');\n"
           "  setTimeout(function(){ _scrollToMpCard(num); }, 90);\n"
           "}")

# ─────────────────────────────────────────────────────────────────────────────
# 2) Endpoint backend
# ─────────────────────────────────────────────────────────────────────────────
BACKEND = r'''class LiveApuestaItem(BaseModel):
    numero_fifa: int
    pred_local: int
    pred_visitante: int
    pred_amarillas: int | None = None
    pred_var: int | None = None
    pred_rojas: int | None = None
    pred_penales_partido: int | None = None
    pred_minuto_gol: int | None = None
    pred_penales_local_tanda: int | None = None
    pred_penales_visitante_tanda: int | None = None
    pred_equipo_clasifica: int | None = None


class LiveGuardarIn(BaseModel):
    apostador_id: int
    pin: str
    apuestas: list[LiveApuestaItem]


@router.post("/live-guardar-apuestas/{torneo_id}",
             summary="Guardar apuestas desde live-playoffs validando PIN=username (upper)")
async def live_guardar_apuestas(torneo_id: int, body: LiveGuardarIn, db: DBSession) -> dict:
    """Guarda apuestas de un apostador desde becbuc-live-playoffs.html.
    El PIN es el username del apostador en app_db; se compara en MAYUSCULAS.
    Solo guarda partidos en estado 'programado' cuya fase NO este bloqueada.
    No calcula puntajes ni cierra fases.
    """
    # 1. Validar PIN = username (app_db), comparacion en UPPER
    async with _app_engine.connect() as conn:
        ur = await conn.execute(
            text("SELECT username FROM users WHERE id = :aid"),
            {"aid": body.apostador_id})
        urow = ur.first()
    if not urow:
        raise HTTPException(404, "Apostador no encontrado")
    username = (urow[0] or "").strip()
    if (body.pin or "").strip().upper() != username.upper():
        return {"ok": False, "error": "PIN incorrecto. El PIN es tu nombre de usuario."}
    if not body.apuestas:
        return {"ok": False, "error": "No hay apuestas para guardar."}

    resultados: list[dict] = []
    guardadas = 0
    for it in body.apuestas:
        pr = await db.execute(text("""
            SELECT p.id, p.estado, COALESCE(f.bloqueada, FALSE) AS bloqueada,
                   p.equipo_local_id, p.equipo_visitante_id
            FROM partido p JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND p.numero_fifa = :nfifa
            LIMIT 1
        """), {"tid": torneo_id, "nfifa": it.numero_fifa})
        prow = pr.first()
        if not prow:
            resultados.append({"numero_fifa": it.numero_fifa, "ok": False, "msg": "Partido no encontrado"})
            continue
        pid, estado, bloqueada, loc_id, vis_id = prow[0], prow[1], prow[2], prow[3], prow[4]
        if estado in ("finalizado", "en_juego"):
            resultados.append({"numero_fifa": it.numero_fifa, "ok": False,
                               "msg": "Partido " + str(estado) + ": no editable"})
            continue
        if bloqueada:
            resultados.append({"numero_fifa": it.numero_fifa, "ok": False, "msg": "Fase bloqueada"})
            continue
        pec = it.pred_equipo_clasifica
        if pec is not None and pec not in (loc_id, vis_id):
            pec = None
        await db.execute(text("""
            INSERT INTO apuesta
                (apostador_id, partido_id, nombre_apostador, numero_fifa,
                 pred_local, pred_visitante,
                 pred_minuto_gol, pred_amarillas, pred_var,
                 pred_rojas, pred_penales_partido,
                 pred_penales_local_tanda, pred_penales_visitante_tanda,
                 pred_equipo_clasifica)
            VALUES
                (:uid, :pid, :nombre, :nfifa,
                 :pl, :pv, :pmg, :pam, :pvar,
                 :projas, :ppp, :pltanda, :pvtanda, :pec)
            ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                nombre_apostador             = EXCLUDED.nombre_apostador,
                numero_fifa                  = EXCLUDED.numero_fifa,
                pred_local                   = EXCLUDED.pred_local,
                pred_visitante               = EXCLUDED.pred_visitante,
                pred_minuto_gol              = EXCLUDED.pred_minuto_gol,
                pred_amarillas               = EXCLUDED.pred_amarillas,
                pred_var                     = EXCLUDED.pred_var,
                pred_rojas                   = EXCLUDED.pred_rojas,
                pred_penales_partido         = EXCLUDED.pred_penales_partido,
                pred_penales_local_tanda     = EXCLUDED.pred_penales_local_tanda,
                pred_penales_visitante_tanda = EXCLUDED.pred_penales_visitante_tanda,
                pred_equipo_clasifica        = EXCLUDED.pred_equipo_clasifica,
                updated_at                   = NOW()
        """), {
            "uid": body.apostador_id, "pid": pid, "nombre": username,
            "nfifa": it.numero_fifa,
            "pl": it.pred_local, "pv": it.pred_visitante,
            "pmg": it.pred_minuto_gol, "pam": it.pred_amarillas, "pvar": it.pred_var,
            "projas": it.pred_rojas, "ppp": it.pred_penales_partido,
            "pltanda": it.pred_penales_local_tanda,
            "pvtanda": it.pred_penales_visitante_tanda,
            "pec": pec,
        })
        guardadas += 1
        resultados.append({"numero_fifa": it.numero_fifa, "ok": True, "msg": "Guardado"})

    await db.commit()
    return {"ok": guardadas > 0, "guardadas": guardadas,
            "total": len(body.apuestas), "resultados": resultados, "apostador": username}


'''

anchor_py = '@router.post("/resetear-apuestas/{torneo_id}",'
new_py = BACKEND + anchor_py

# ─── aplicar ────────────────────────────────────────────────────────────────
apply(HTML, [(anchor_html, new_html), (anchor_sel, new_sel)], verify_html)
apply(PY,   [(anchor_py, new_py)], verify_py)
print("\nTODO OK.")
