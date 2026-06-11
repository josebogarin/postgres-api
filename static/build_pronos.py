"""
build_pronos.py — Regenera BECBUC-pronos.html desde BECBUC-movil.html.
Ejecutar cada vez que se modifique la sección de pronósticos en movil.html.

Uso:
    python build_pronos.py
    cd backend/static && python build_pronos.py
"""
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(BASE, 'BECBUC-movil.html')
DST  = os.path.join(BASE, 'BECBUC-pronos.html')

print(f"Leyendo {SRC} ...")
with open(SRC, 'r', encoding='utf-8') as f:
    lines = f.readlines()
src = ''.join(lines)
print(f"  {len(lines)} líneas, {len(src):,} chars")

# ── 1. CSS ────────────────────────────────────────────────────────────────
css_m = re.search(r'<style>(.*?)</style>', src, re.DOTALL)
if not css_m:
    raise RuntimeError("No se encontró bloque <style>")
css = css_m.group(1)

# Fix body: eliminar padding-bottom que depende de --tabh
css = css.replace(
    'padding-bottom:calc(var(--tabh) + env(safe-area-inset-bottom));',
    'padding-bottom:calc(env(safe-area-inset-bottom) + 20px);')

# Fix savebar: sube sin la barra de tabs
css = css.replace(
    'bottom:calc(var(--tabh) + env(safe-area-inset-bottom));z-index:35;',
    'bottom:calc(env(safe-area-inset-bottom) + 8px);z-index:35;')

# Fix toast: sube sin la barra de tabs
css = css.replace(
    'bottom:calc(var(--tabh) + env(safe-area-inset-bottom) + 12px);',
    'bottom:calc(env(safe-area-inset-bottom) + 80px);')

# Eliminar bloque CSS de la barra de tabs (nav.tabs / .tab / .bdg)
css = re.sub(
    r'\s*/\* ── Bottom tabs ── \*/.*?\.tab \.bdg\.show\{display:flex\}',
    '',
    css, flags=re.DOTALL)

# ── 2. JS ─────────────────────────────────────────────────────────────────
js_m = re.search(r'<script>(.*?)</script>', src, re.DOTALL)
if not js_m:
    raise RuntimeError("No se encontró bloque <script>")
js = js_m.group(1)

# Cortar todo lo que viene después de /* ════════ GRUPOS (real) ════════ */
grupos_marker = '/* ════════ GRUPOS (real) ════════ */'
idx_cut = js.find(grupos_marker)
if idx_cut != -1:
    js = js[:idx_cut].rstrip()
    print(f"  JS cortado en '{grupos_marker}' ({len(js):,} chars)")
else:
    print("  ADVERTENCIA: no se encontró el marcador de GRUPOS — el JS no fue cortado")

# ── Reemplazar boot() simplificado (sin tabs, sin loadMensajes, con KPIs) ──
BOOT_NEW = '''/* ════════ Boot ════════ */
let _rankingCache=[];
async function boot(){
  try{_me=await api('/api/v1/auth/me');}catch{showLogin();return;}
  const roles=(_me.roles||[]).map(r=>r.name);
  _isSuper=roles.includes('superadmin');
  _isAdmin=_isSuper||roles.includes('admin');
  const name=_me.nombre_completo||_me.username||_me.ci||\'?\';
  document.getElementById(\'userName\').textContent=name;
  document.getElementById(\'avatar\').textContent=name.charAt(0).toUpperCase();
  document.getElementById(\'login\').classList.add(\'hidden\');
  document.getElementById(\'topbar\').style.display=\'flex\';
  try{const a=await api(\'/api/v1/torneo/activas\');if(a&&a.length){_torneoId=a[0].id;_torneoNombre=a[0].nombre;}}catch{}
  document.getElementById(\'torneoName\').textContent=_torneoNombre||\'Sin torneo activo\';
  try{
    _rankingCache=await api(`/api/v1/bets/ranking/${_torneoId}`)|| [];
    _renderKpiBar(_rankingCache);
  }catch{}
  if(!_torneoId){document.getElementById(\'page-pronos\').innerHTML=empty(\'🏆\',\'No hay torneo activo\',\'Pedile al admin que active un torneo.\');return;}
  loadPronos();
}
function _renderKpiBar(rk){
  const chip=document.getElementById(\'ptsChip\');
  const yo=rk.find(r=>r.apostador_id===_me.id);
  if(!yo||!chip) return;
  const pos=rk.indexOf(yo)+1;
  const lider=rk[0];
  const diff=lider&&lider.apostador_id!==_me.id?lider.puntos_total-(yo.puntos_total||0):null;
  let txt=`${yo.puntos_total??0} pts`;
  if(pos) txt=`#${pos} · `+txt;
  if(diff!==null&&diff>=0) txt+=` (-${diff})`;
  chip.textContent=txt;
}'''

boot_pattern = re.compile(
    r'/\* ════════ Boot ════════ \*/\nasync function boot\(\)\{.*?\}(?=\n\n/\* ════════ Navegación)',
    re.DOTALL)
js, n_boot = boot_pattern.subn(BOOT_NEW, js)
print(f"  boot() reemplazado: {n_boot} vez/veces")

# ── Reemplazar go() con función vacía ──
go_pattern = re.compile(
    r'(/\* ════════ Navegación ════════ \*/\n)function go\(tab\)\{.*?\}(?=\nconst empty)',
    re.DOTALL)
js, n_go = go_pattern.subn(r'\1function go(tab){}', js)
print(f"  go() simplificado: {n_go} vez/veces")

# ── Fix saveKOM: loadBracket → loadPronos ──
js = js.replace(
    '_koSlipM={};_bracketDirty=true;await loadBracket();}',
    '_koSlipM={};_bracketDirty=true;await loadPronos();}')

# ── 3. HTML ────────────────────────────────────────────────────────────────
# Extraer bloque LOGIN
login_m = re.search(r'(<!-- LOGIN -->.*?)(?=<!-- CHANGE PASSWORD)', src, re.DOTALL)
login_block = login_m.group(1) if login_m else ''

# Extraer bloque CHANGE PASSWORD MODAL
cpm_m = re.search(r'(<!-- CHANGE PASSWORD MODAL.*?)(?=<!-- TOPBAR -->)', src, re.DOTALL)
cpm_block = cpm_m.group(1) if cpm_m else ''

# ── 4. Generar archivo final ───────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0b111d">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>BECBUC · Pronósticos</title>
<style>{css}</style>
</head>
<body>

{login_block}
{cpm_block}
<!-- TOPBAR -->
<div class="topbar" id="topbar" style="display:none">
  <div class="logo">BB</div>
  <div><div class="tt-title">BECBUC</div><div class="tt-sub" id="torneoName">—</div></div>
  <div class="spacer"></div>
  <div id="ptsChip" style="font-size:.7rem;font-weight:800;color:var(--orange2);background:rgba(232,85,31,.12);border:1px solid rgba(232,85,31,.3);border-radius:12px;padding:3px 10px;white-space:nowrap;margin-right:4px;"></div>
  <div class="user-chip"><div class="avatar" id="avatar">?</div><span id="userName">—</span></div>
  <button class="logout" onclick="logout()" title="Salir">⏻</button>
</div>

<!-- PAGE -->
<div class="wrap">
  <div class="page active" id="page-pronos"><div class="loader"><span class="spin">◌</span> Cargando…</div></div>
</div>

<!-- SAVE BAR -->
<div class="savebar" id="savebar"><div class="in">
  <button class="btn-ghost" onclick="reloadPronos()" title="Recargar">↻</button>
  <button class="btn-save" id="btnSave" onclick="saveAll()" disabled><span>Guardar pronósticos</span><span class="sc" id="saveCount">0</span></button>
</div></div>

<div class="toast" id="toast"></div>

<script>
{js}
</script>
</body>
</html>"""

with open(DST, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅  {DST}")
print(f"   {len(html):,} chars totales")
# Verify no undesired functions leaked through
for fn in ['function loadGrupos', 'function loadBracket', 'function loadRanking',
           'function loadMensajes', 'function loadAdmin']:
    if fn in html:
        print(f"   ⚠️  ADVERTENCIA: '{fn}' encontrado en la salida — revisar corte de JS")
    else:
        print(f"   ✓  '{fn}' no está en la salida")
