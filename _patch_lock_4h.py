import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""Bloqueo de edicion de Mi Prono 4h antes del partido (backend + frontend)."""
import ast, re, shutil, subprocess, os
from datetime import datetime
HTML = _osp.path.join(_BASE, 'backend', 'static', 'becbuc-live-playoffs.html')
PY   = _osp.path.join(_BASE, 'backend', 'app', 'api', 'v1', 'endpoints', 'apostador_bets.py')
BKP  = _osp.path.join(_BASE, '_backups')
if not os.path.exists(HTML):
    base="/sessions/stoic-busy-euler/mnt/proyecto FAST API"
    HTML=base+"/backend/static/becbuc-live-playoffs.html"; PY=base+"/backend/app/api/v1/endpoints/apostador_bets.py"; BKP=base+"/_backups"
os.makedirs(BKP, exist_ok=True)

def vhtml(p):
    raw=open(p,'rb').read()
    if not raw.rstrip().endswith(b'</html>'): return False,'falta </html>'
    s=re.findall(rb'<script>([\s\S]*?)</script>',raw)
    r=subprocess.run(['node','--check'],input=s[-1],capture_output=True)
    return (r.returncode==0),('OK' if r.returncode==0 else r.stderr.decode(errors='replace')[:180])
def vpy(p):
    try: ast.parse(open(p,encoding='utf-8').read()); return True,'OK'
    except SyntaxError as e: return False,f'line {e.lineno}: {e.msg}'
def apply(path,repls,verifier):
    src=open(path,encoding='utf-8').read()
    for old,new in repls:
        c=src.count(old)
        if c!=1: raise SystemExit(f'count={c} en {os.path.basename(path)}: {old[:70]!r}')
        src=src.replace(old,new,1)
    b=os.path.join(BKP,os.path.basename(path)+'.'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
    shutil.copy2(path,b); open(path,'w',encoding='utf-8').write(src)
    ok,msg=verifier(path)
    if not ok: shutil.copy2(b,path); raise SystemExit(f'VERIFY FALLO {os.path.basename(path)}: {msg} -> restaurado')
    print(f'OK {os.path.basename(path)} ({msg})')

# ── HTML 1: _mpLocked + _mpNumInput(dis) ──
num_old = """function _mpNumInput(id, val, ph, mn, mx){
  const v = (val!==null && val!==undefined && val!=='') ? val : '';
  return '<input id="'+id+'" type="number" inputmode="numeric"'
    + (mn!=null?' min="'+mn+'"':'') + (mx!=null?' max="'+mx+'"':'')
    + ' value="'+v+'" placeholder="'+(ph||'')+'"'
    + ' style="width:54px;background:#0b1120;border:1px solid #334155;color:#e2e8f0;border-radius:6px;padding:5px 6px;text-align:center;font-size:14px">';
}"""
num_new = r"""function _mpLocked(m){
  if(!m || !m.fecha) return false;
  let s=String(m.fecha);
  if(!/[zZ]$|[+\-]\d\d:?\d\d$/.test(s)) s+='Z';
  const start=new Date(s).getTime();
  if(isNaN(start)) return false;
  return Date.now() >= (start - 4*3600*1000);
}
function _mpNumInput(id, val, ph, mn, mx, dis){
  const v = (val!==null && val!==undefined && val!=='') ? val : '';
  return '<input id="'+id+'" type="number" inputmode="numeric"'+(dis?' disabled':'')
    + (mn!=null?' min="'+mn+'"':'') + (mx!=null?' max="'+mx+'"':'')
    + ' value="'+v+'" placeholder="'+(ph||'')+'"'
    + ' style="width:54px;background:#0b1120;border:1px solid #334155;color:#e2e8f0;border-radius:6px;padding:5px 6px;text-align:center;font-size:14px">';
}"""

# ── HTML 2: _mpEditorCard(m, locked) ──
card_old = """function _mpEditorCard(m){
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
  let h='<div class="ap-match-card" id="mp-card-'+num+'" data-num="'+num+'" data-edit="1">';"""
card_new = """function _mpEditorCard(m, locked){
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
  const de=locked?'':' data-edit="1"';
  let h='<div class="ap-match-card" id="mp-card-'+num+'" data-num="'+num+'"'+de+'>';
  if(locked) h+='<div style="text-align:center;background:#3f2d0a;color:#fbbf24;font-size:12px;font-weight:700;padding:6px">🔒 Edición cerrada — faltan menos de 4 h para el partido</div>';"""

# reemplazar las llamadas _mpNumInput(...) sin dis por versiones con locked, y el select
call_repls = [
    ("_mpNumInput('mpe-'+num+'-pl', p.pred_local, '', 0, 99)",
     "_mpNumInput('mpe-'+num+'-pl', p.pred_local, '', 0, 99, locked)"),
    ("_mpNumInput('mpe-'+num+'-pv', p.pred_visitante, '', 0, 99)",
     "_mpNumInput('mpe-'+num+'-pv', p.pred_visitante, '', 0, 99, locked)"),
    ("_mpNumInput('mpe-'+num+'-j', p.pred_amarillas,'0',0,60)",
     "_mpNumInput('mpe-'+num+'-j', p.pred_amarillas,'0',0,60,locked)"),
    ("_mpNumInput('mpe-'+num+'-k', p.pred_rojas,'0',0,20)",
     "_mpNumInput('mpe-'+num+'-k', p.pred_rojas,'0',0,20,locked)"),
    ("_mpNumInput('mpe-'+num+'-l', p.pred_var,'0',0,20)",
     "_mpNumInput('mpe-'+num+'-l', p.pred_var,'0',0,20,locked)"),
    ("_mpNumInput('mpe-'+num+'-m', p.pred_penales_partido,'0',0,10)",
     "_mpNumInput('mpe-'+num+'-m', p.pred_penales_partido,'0',0,10,locked)"),
    ("_mpNumInput('mpe-'+num+'-n', p.pred_minuto_gol,'min',1,130)",
     "_mpNumInput('mpe-'+num+'-n', p.pred_minuto_gol,'min',1,130,locked)"),
    ("_mpNumInput('mpe-'+num+'-ol', p.pred_penales_local_tanda,'0',0,30)",
     "_mpNumInput('mpe-'+num+'-ol', p.pred_penales_local_tanda,'0',0,30,locked)"),
    ("_mpNumInput('mpe-'+num+'-ov', p.pred_penales_visitante_tanda,'0',0,30)",
     "_mpNumInput('mpe-'+num+'-ov', p.pred_penales_visitante_tanda,'0',0,30,locked)"),
    ("""const sel='<select id="mpe-'+num+'-p" style="background:#0b1120;""",
     """const sel='<select id="mpe-'+num+'-p"'+(locked?' disabled':'')+' style="background:#0b1120;"""),
]

# ── HTML 3: else block de renderMiPronoEditor ──
else_old = """  }else{
    editables.forEach(function(m){ html+=_mpEditorCard(m); });
    html+='<div style="padding:14px 10px 6px;text-align:center">'
      +'<button onclick="_mpGuardarClick()" style="background:#16a34a;color:#fff;border:none;border-radius:10px;padding:12px 30px;font-size:15px;font-weight:800;cursor:pointer">💾 Guardar apuestas</button>'
      +'<div style="font-size:11px;color:#6b7280;margin-top:6px">Se te pedirá un PIN (tu primer nombre) para confirmar.</div>'
      +'<div id="mpe-save-result" style="margin-top:10px"></div></div>';
  }"""
else_new = """  }else{
    editables.forEach(function(m){ html+=_mpEditorCard(m, _mpLocked(m)); });
    const anyEdit=editables.some(function(m){ return !_mpLocked(m); });
    if(anyEdit){
      html+='<div style="padding:14px 10px 6px;text-align:center">'
        +'<button onclick="_mpGuardarClick()" style="background:#16a34a;color:#fff;border:none;border-radius:10px;padding:12px 30px;font-size:15px;font-weight:800;cursor:pointer">💾 Guardar apuestas</button>'
        +'<div style="font-size:11px;color:#6b7280;margin-top:6px">Se te pedirá un PIN (tu primer nombre) para confirmar.</div>'
        +'<div id="mpe-save-result" style="margin-top:10px"></div></div>';
    }else{
      html+='<div class="ap-empty" style="padding:14px;text-align:center;color:#f59e0b">🔒 La edición está cerrada (faltan menos de 4 h para los partidos).</div>';
    }
  }"""

html_repls = [(num_old,num_new),(card_old,card_new)] + call_repls + [(else_old,else_new)]

# ── PY: agregar p.fecha al SELECT + chequeo 4h ──
py1_old = """            SELECT p.id, p.estado, COALESCE(f.bloqueada, FALSE) AS bloqueada,
                   p.equipo_local_id, p.equipo_visitante_id
            FROM partido p JOIN fase f ON f.id = p.fase_id"""
py1_new = """            SELECT p.id, p.estado, COALESCE(f.bloqueada, FALSE) AS bloqueada,
                   p.equipo_local_id, p.equipo_visitante_id, p.fecha
            FROM partido p JOIN fase f ON f.id = p.fase_id"""

py2_old = """        if bloqueada:
            resultados.append({"numero_fifa": it.numero_fifa, "ok": False, "msg": "Fase bloqueada"})
            continue
        pec = it.pred_equipo_clasifica"""
py2_new = """        if bloqueada:
            resultados.append({"numero_fifa": it.numero_fifa, "ok": False, "msg": "Fase bloqueada"})
            continue
        fecha = prow[5]
        if fecha is not None:
            from datetime import timedelta as _td
            fecha_utc = fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)
            if datetime.now(timezone.utc) >= fecha_utc - _td(hours=4):
                resultados.append({"numero_fifa": it.numero_fifa, "ok": False,
                                   "msg": "Edicion cerrada: faltan menos de 4 h para el partido"})
                continue
        pec = it.pred_equipo_clasifica"""

apply(HTML, html_repls, vhtml)
apply(PY,   [(py1_old,py1_new),(py2_old,py2_new)], vpy)
print("TODO OK.")
