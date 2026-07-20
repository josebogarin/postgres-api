#!/usr/bin/env python3
"""Reforma el tab Puntajes: agrega matriz completa apostador x fase."""
import re

PATH = r"C:\proyecto FAST API\backend\static\becbuc-live-playoffs.html"
# Linux mount path
LPATH = "/sessions/vibrant-vigilant-einstein/mnt/proyecto FAST API/backend/static/becbuc-live-playoffs.html"

with open(LPATH, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Archivo original: {len(content)} bytes")

# ─── 1. Reemplazar HTML del tab-scores ────────────────────────────────────────
OLD_TAB_MARKER = '  <!-- ─── PUNTAJES TAB'
NEW_BOTTOM_MARKER = '\n  <!-- BOTTOM NAV -->'

start = content.find(OLD_TAB_MARKER)
end   = content.find(NEW_BOTTOM_MARKER)
assert start > 0 and end > 0, f"Marcadores no encontrados: start={start}, end={end}"

old_tab_block = content[start:end]
print(f"Bloque tab-scores encontrado: {len(old_tab_block)} chars")

new_tab_block = '''  <!-- ─── PUNTAJES TAB ─────────────────────────────────────────── -->
  <div id="tab-scores" class="tab-pane">
    <!-- Topbar de usuario seleccionado (invisible DOM, necesario para updateComboDisplay) -->
    <div style="display:none">
      <div id="sel-avatar">?</div>
      <div id="sel-name"></div>
      <div id="sel-sub"></div>
    </div>

    <!-- Matriz principal -->
    <div class="sc-matrix-section">
      <div class="sc-matrix-hdr">
        <span class="sc-matrix-title">📊 Tabla de Puntajes</span>
        <button class="sc-refresh-btn" onclick="refreshScoresMatrix()" title="Actualizar">⟳</button>
      </div>
      <div class="sc-matrix-sub">Tocá un nombre para ver su desglose</div>
      <div id="scores-matrix-wrap" class="sc-matrix-wrap">
        <div class="sc-loading">Cargando...</div>
      </div>
    </div>

    <!-- Detalle del apostador seleccionado -->
    <div id="scores-apostador-detail" style="display:none">
      <div class="section-divider"></div>
      <div class="vs-section" id="vs-section">
        <div class="vs-title">
          <span id="sc-detail-name" style="font-weight:700;color:#93c5fd">—</span>
          <span id="vs-total-lbl" style="color:#3b82f6;font-weight:700"></span>
        </div>
        <div class="vs-cards" id="vs-cards"></div>
      </div>
      <div class="section-divider"></div>
      <div class="phase-chips-section" id="phase-chips-section">
        <div class="phase-chips-title">Puntos por fase (playoffs)</div>
        <div class="phase-chips-row" id="phase-chips-row"></div>
      </div>
      <div class="section-divider"></div>
      <div id="sb-breakdown-anchor"></div>
    </div>

    <!-- Detalle de partido (al tocar en el bracket) -->
    <div class="match-detail" id="match-detail-section" style="display:none">
      <div class="md-title">
        <span id="md-phase-lbl">Detalle del partido</span>
        <span id="md-live-chip" style="display:none;font-size:10px;background:rgba(239,68,68,.15);color:#ef4444;padding:3px 8px;border-radius:8px;font-weight:700">● LIVE</span>
      </div>
      <div class="md-scoreboard" id="md-scoreboard"></div>
      <div class="items-list" id="md-items"></div>
      <div class="match-total-bar" id="md-total" style="display:none">
        <div>
          <div class="match-total-label">Puntos partido</div>
          <div class="match-total-of" id="md-total-of">de ? posibles</div>
        </div>
        <div class="match-total-pts" id="md-total-pts">0</div>
      </div>
    </div>
  </div>
'''

content = content[:start] + new_tab_block + content[end:]
print(f"✓ HTML tab-scores reemplazado")

# ─── 2. Agregar CSS ───────────────────────────────────────────────────────────
CSS_ANCHOR = "</style>"'
assert CSS_ANCHOR in content, "No se encontró </style>"

NEW_CSS = '''
/* ── Scores Matrix ─────────────────────────────────────────── */
  .sc-matrix-section { padding: 12px 8px 0; }
  .sc-matrix-hdr { display:flex; align-items:center; gap:8px; margin-bottom:2px; }
  .sc-matrix-title { font-size:15px; font-weight:700; color:#e2e8f0; }
  .sc-matrix-sub { font-size:11px; color:#4b5563; margin-bottom:8px; }
  .sc-refresh-btn { background:none; border:1px solid #1e3a5f; color:#60a5fa; font-size:16px; border-radius:6px; padding:2px 7px; cursor:pointer; line-height:1; }
  .sc-matrix-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .sc-loading { text-align:center; padding:30px; color:#4b5563; font-size:13px; }
  .sc-tbl-wrap { min-width:100%; }
  .sc-tbl { width:100%; border-collapse:collapse; font-size:12px; }
  .sc-th { background:#0d1b2e; color:#64748b; font-size:10px; font-weight:600; padding:6px 4px; text-align:center; position:sticky; top:0; z-index:2; border-bottom:1px solid #1e3a5f; white-space:nowrap; }
  .sc-th-apos { text-align:left; padding-left:8px; min-width:80px; }
  .sc-th-rank { min-width:24px; }
  .sc-th-total { color:#fbbf24; }
  .sc-td { padding:6px 4px; text-align:center; border-bottom:1px solid #0f172a; color:#94a3b8; }
  .sc-td-rank { color:#374151; font-size:11px; }
  .sc-td-apos { text-align:left; padding-left:8px; color:#cbd5e1; font-weight:600; }
  .sc-td-pos { color:#86efac; font-weight:600; }
  .sc-td-zero { color:#1e293b; }
  .sc-td-total { color:#fbbf24; font-weight:700; font-size:13px; }
  .sc-tr { cursor:pointer; transition:background .15s; }
  .sc-tr:hover { background:#0f1e30; }
  .sc-tr-me { background:#0f1e36; }
  .sc-tr-me .sc-td-apos { color:#3b82f6; }
  .sc-tr-me .sc-td-apos::before { content:"▶ "; font-size:9px; color:#3b82f6; }
  .sc-tr-me:hover { background:#132040; }

</style>'''

content = content.replace(CSS_ANCHOR, NEW_CSS, 1)
print(f"✓ CSS de matriz agregado")

# ─── 3. Reemplazar renderScoresTab() ──────────────────────────────────────────
OLD_RENDER_SCORES = '''function renderScoresTab() {
  if (!_viewAsId) return;

  // vs top 3
  const vsSection = document.getElementById('vs-section');
  if (_apostadores.length) {
    vsSection.style.display = 'block';
    renderVsTop3();
  }

  // phase chips
  const phSection = document.getElementById('phase-chips-section');
  if (_bracket.length) {
    phSection.style.display = 'block';
    renderPhaseChips();
  }

  // Breakdown by component (partidos + grupos_p + peor_d + globales)
  renderScoresBreakdown();

  // If a match was already selected
  if (_selectedMatchNum) {
    const m = _bracket.find(x=>x.num===_selectedMatchNum);
    if (m) renderMatchDetail(m);
  }
}'''

NEW_RENDER_SCORES = '''let _rankingData   = null;
let _aliasMap      = {};
let _matrixLoading = false;

function renderScoresTab() {
  // Load matrix if not cached
  if (!_rankingData && !_matrixLoading) loadRankingMatrix();
  else if (_rankingData) renderScoresMatrix();

  // Detail panel for selected apostador
  if (_viewAsId && _apostadores.length) {
    const detail = document.getElementById('scores-apostador-detail');
    if (detail) detail.style.display = 'block';
    const nameEl = document.getElementById('sc-detail-name');
    if (nameEl) nameEl.textContent = _aliasMap[_viewAsId] || _viewAsName || '—';
    renderVsTop3();
    renderPhaseChips();
    renderScoresBreakdown();
  }

  // If a match was already selected
  if (_selectedMatchNum) {
    const m = _bracket.find(x=>x.num===_selectedMatchNum);
    if (m) renderMatchDetail(m);
  }
}

async function loadRankingMatrix() {
  _matrixLoading = true;
  const wrap = document.getElementById('scores-matrix-wrap');
  if (wrap) wrap.innerHTML = '<div class="sc-loading">Cargando ranking...</div>';
  try {
    const [rResp, aResp] = await Promise.all([
      api('/api/v1/bets/ranking/' + _torneoId),
      api('/api/v1/bets/apostadores')
    ]);
    const rData = await rResp.json();
    const aData = await aResp.json();
    _aliasMap = {};
    for (const ap of aData) _aliasMap[ap.id] = ap.username || '?';
    _rankingData = rData.ranking || rData || [];
    _matrixLoading = false;
    renderScoresMatrix();
  } catch(e) {
    _matrixLoading = false;
    if (wrap) wrap.innerHTML = '<div class="sc-loading" style="color:#f87171">Error al cargar (' + e.message + ')</div>';
  }
}

async function refreshScoresMatrix() {
  _rankingData = null;
  await loadRankingMatrix();
}

function renderScoresMatrix() {
  const wrap = document.getElementById('scores-matrix-wrap');
  if (!wrap || !_rankingData) return;

  const FASES = [
    { key:'grupos', label:'Grupos', fn: r => (r.fases||[]).filter(x=>x.tipo?.startsWith('grupo')).reduce((s,x)=>s+x.pts,0) },
    { key:'r32',   label:'R32',    fn: r => (r.fases||[]).find(x=>x.tipo==='ronda32')?.pts || 0 },
    { key:'r16',   label:'8vos',   fn: r => (r.fases||[]).find(x=>x.tipo==='ronda16')?.pts || 0 },
    { key:'qf',    label:'4tos',   fn: r => (r.fases||[]).find(x=>x.tipo==='cuartos')?.pts || 0 },
    { key:'sf',    label:'Semis',  fn: r => (r.fases||[]).find(x=>x.tipo==='semis')?.pts || 0 },
    { key:'fin',   label:'Final',  fn: r => (r.fases||[]).filter(x=>['tercer_puesto','final'].includes(x.tipo)).reduce((s,x)=>s+x.pts,0) },
    { key:'glob',  label:'🌐',    fn: r => (r.pts_globales||0)+(r.pts_grupos_p||0) },
  ];

  const sorted = [..._rankingData].sort((a,b)=>(b.puntos_total||0)-(a.puntos_total||0));

  let html = `<div class="sc-tbl-wrap"><table class="sc-tbl">
    <thead><tr>
      <th class="sc-th sc-th-rank">#</th>
      <th class="sc-th sc-th-apos">Apostador</th>
      ${FASES.map(f=>`<th class="sc-th">${f.label}</th>`).join('')}
      <th class="sc-th sc-th-total">Total</th>
    </tr></thead><tbody>`;

  sorted.forEach((r, i) => {
    const alias = _aliasMap[r.apostador_id] || '?';
    const isMe  = r.apostador_id === _viewAsId;
    const cells = FASES.map(f => {
      const v  = f.fn(r);
      const cl = v > 0 ? 'sc-td sc-td-pos' : 'sc-td sc-td-zero';
      return `<td class="${cl}">${v > 0 ? v : ''}</td>`;
    }).join('');
    html += `<tr class="sc-tr${isMe?' sc-tr-me':''}" onclick="selectAposFromMatrix(${r.apostador_id},'${alias}',${r.puntos_total||0})">
      <td class="sc-td sc-td-rank">${i+1}</td>
      <td class="sc-td sc-td-apos">${alias}</td>
      ${cells}
      <td class="sc-td sc-td-total">${r.puntos_total||0}</td>
    </tr>`;
  });

  html += '</tbody></table></div>';
  wrap.innerHTML = html;
}

async function selectAposFromMatrix(uid, alias, pts) {
  _viewAsId   = uid;
  _viewAsName = alias;
  updateTopbarUser();
  // Load predictions for this apostador
  await loadUserPredictions(uid);
  calcPhaseTotals();
  // Show detail panel
  const detail = document.getElementById('scores-apostador-detail');
  if (detail) {
    detail.style.display = 'block';
    const nameEl = document.getElementById('sc-detail-name');
    if (nameEl) nameEl.textContent = alias;
    renderVsTop3();
    renderPhaseChips();
    renderScoresBreakdown();
    detail.scrollIntoView({ behavior:'smooth', block:'nearest' });
  }
  // Refresh matrix to update highlight
  renderScoresMatrix();
}'''

if OLD_RENDER_SCORES in content:
    content = content.replace(OLD_RENDER_SCORES, NEW_RENDER_SCORES, 1)
    print(f"✓ renderScoresTab() reemplazada + funciones nuevas agregadas")
else:
    print("✗ ERROR: renderScoresTab() no encontrada exactamente")
    # Debug: buscar inicio
    idx = content.find('function renderScoresTab()')
    print(f"  Posición de 'function renderScoresTab()': {idx}")

# ─── 4. Reemplazar renderScoresBreakdown() para usar el anchor ────────────────
OLD_BREAKDOWN_CREATION = '''  let bdiv = document.getElementById('sb-breakdown-section');
  if (!bdiv) {
    bdiv = document.createElement('div');
    bdiv.id = 'sb-breakdown-section';
    bdiv.className = 'sb-breakdown';
    const phSection = document.getElementById('phase-chips-section');
    if (phSection && phSection.parentNode) {
      phSection.parentNode.insertBefore(bdiv, phSection.nextSibling);
    }
  }'''

NEW_BREAKDOWN_CREATION = '''  let bdiv = document.getElementById('sb-breakdown-section');
  if (!bdiv) {
    bdiv = document.createElement('div');
    bdiv.id = 'sb-breakdown-section';
    bdiv.className = 'sb-breakdown';
    const anchor = document.getElementById('sb-breakdown-anchor');
    if (anchor) {
      anchor.innerHTML = '';
      anchor.appendChild(bdiv);
    } else {
      const phSection = document.getElementById('phase-chips-section');
      if (phSection && phSection.parentNode) {
        phSection.parentNode.insertBefore(bdiv, phSection.nextSibling);
      }
    }
  }'''

if OLD_BREAKDOWN_CREATION in content:
    content = content.replace(OLD_BREAKDOWN_CREATION, NEW_BREAKDOWN_CREATION, 1)
    print(f"✓ renderScoresBreakdown() actualizada para usar anchor")
else:
    print("✗ ERROR: bloque de creación de bdiv no encontrado exactamente")

# ─── 5. Agregar setTab('scores') call ─────────────────────────────────────────
OLD_SETTAB_APUESTAS = '''  if (t==='apuestas') renderApuestasTab();
}'''

NEW_SETTAB_APUESTAS = '''  if (t==='apuestas') renderApuestasTab();
  if (t==='scores') renderScoresTab();
}'''

if OLD_SETTAB_APUESTAS in content:
    content = content.replace(OLD_SETTAB_APUESTAS, NEW_SETTAB_APUESTAS, 1)
    print(f"✓ setTab('scores') → renderScoresTab() conectado")
else:
    print("✗ ERROR: setTab no encontrado")

# ─── 6. Escribir ──────────────────────────────────────────────────────────────
with open(LPATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nArchivo final: {len(content)} bytes")

# Verificar integridad básica
script_opens  = content.count('<script')
script_closes = content.count('</script>')
print(f"<script> tags: {script_opens} abiertos / {script_closes} cerrados")
if script_opens != script_closes:
    print("⚠ ADVERTENCIA: tags script desbalanceados")
else:
    print("✓ Tags script balanceados")
