"""
Compara la tabla LIVE de la imagen con los puntajes actuales en puntaje_detalle.
Ejecutar: cd "C:\proyecto FAST API\backend" && python ..\comparar_live_vs_bd.py
"""
import urllib.request, json, sys

# ── Datos extraídos de la imagen (tabla LIVE) ─────────────────────────────────
# alias, A(resultado), B(exacto), C(amarillas), D(rojas), E(var), F(penales), G(minuto), total
LIVE = [
    ("SEBA",                   144, 96,  12, 47, 24, 41, 2,  366),
    ("PATITO",                 144, 40,  14, 50, 37, 49, 0,  334),
    ("LAV",                    140, 48,  13, 50, 12, 49, 3,  315),
    ("VITRA",                  116, 48,  13, 50, 37, 49, 2,  315),
    ("FIDELYOLI",              112, 80,  13, 50, 11, 47, 0,  313),
    ("@BS",                    144, 64,   2, 45, 20, 37, 1,  313),
    ("MORO",                   132, 64,  13, 38, 14, 49, 1,  311),
    ("FSCC",                   144, 48,   6, 50, 14, 49, 0,  311),
    ("CHECHO",                 132, 48,  10, 47, 12, 48, 4,  301),
    ("HAKEMBO",                136, 64,   5, 45,  5, 42, 3,  300),
    ("COCO",                   116, 48,  15, 50, 14, 49, 6,  298),
    ("TIM PAYNE",              132, 40,  11, 39, 36, 35, 1,  294),
    ("SONI",                   132, 24,  12, 47, 32, 41, 3,  291),
    ("ALEJANDROLEGUI",         112, 56,   9, 43, 27, 42, 0,  289),
    ("COTO",                   132, 40,  15, 50,  2, 48, 2,  289),
    ("GUSTAV TOTHELIGHTHOUSE", 120, 24,   7, 50, 37, 49, 0,  287),
    ("QUIROGA",                124, 40,  10, 47, 17, 47, 0,  285),
    ("HS",                     124, 32,  10, 49, 24, 43, 3,  285),
    ("KIKAO",                  132, 40,   8, 46, 12, 44, 2,  284),
    ("AleVo",                  116, 48,  15, 48, 14, 40, 1,  282),
    ("MOÑO",                   128, 32,  16, 48,  9, 47, 2,  282),
    ("GRILLITO",               132, 48,  10, 46,  4, 39, 2,  281),
    ("CHEREM",                 112, 40,  13, 50, 14, 49, 1,  279),
    ("PATO",                   128, 16,  10, 48, 34, 41, 1,  278),
    ("TONY",                   136, 40,  11, 40,  9, 39, 2,  277),
    ("SANBIE",                 124, 40,  15, 49,  3, 43, 0,  274),
    ("SAJANO FREDDY",          124, 24,   6, 47, 25, 44, 3,  273),
    ("ALFAORION 99",           124, 24,   6, 47, 25, 44, 3,  273),
    ("GH1S",                   128, 16,  13, 50, 14, 49, 3,  273),
    ("DECANITA",               112, 64,  10, 42,  8, 32, 3,  271),
    ("CAYETANO",               124, 64,  11, 29,  0, 39, 4,  271),
    ("OTI",                    120, 24,   8, 50, 17, 49, 1,  269),
    ("LUDIE-Z",                128, 32,   7, 33, 23, 43, 1,  267),
    ("LUISMA",                 108, 56,  11, 44,  5, 38, 0,  262),
    ("AAA",                    132, 64,   8, 27,  1, 23, 4,  259),
    ("ESYL",                   128, 40,  15, 50, 14,  7, 1,  255),
    ("JUANE",                  136, 40,   6, 42,  4, 26, 0,  254),
    ("ELIASMAJUL",             116,  8,  12, 50, 16, 47, 1,  250),
    ("PUCHETA",                132, 24,  11, 43,  6, 31, 2,  249),
    ("PINGUERO",               112, 32,  14, 36, 11, 41, 3,  249),
    ("GBC",                    128, 64,   9, 14,  0, 29, 1,  245),
    ("EDGAR",                  108, 48,  16, 29, 22, 20, 2,  245),
    ("CAFICHO",                112, 16,   7, 35,  8, 19, 5,  202),
    ("MONKEY",                  84, 48,   9,  4, 14,  7, 1,  167),
]
COLS = ["A-resultado","B-exacto","C-amarillas","D-rojas","E-var","F-penales","G-minuto","TOTAL"]

# ── Consultar BD via API ───────────────────────────────────────────────────────
try:
    login_data = json.dumps({"username": "jose", "password": "catalina"}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        token = json.loads(r.read())["access_token"]

    req2 = urllib.request.Request(
        "http://localhost:8000/api/v1/bets/ranking/2",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req2, timeout=15) as r2:
        ranking = json.loads(r2.read())
except Exception as e:
    print(f"ERROR API: {e}\nAsegurate de que uvicorn esté corriendo en :8000")
    sys.exit(1)

# BD: alias/nombre → row
bd_map = {}
for row in ranking.get("ranking", []):
    alias = (row.get("nombre") or row.get("username") or "").upper().strip()
    bd_map[alias] = row

# ── Comparar ──────────────────────────────────────────────────────────────────
print(f"\n{'ALIAS':<25} {'COL':<15} {'LIVE':>6} {'BD':>6} {'DIFF':>6}")
print("-" * 62)

diferencias = []
for row in LIVE:
    alias, la, lb, lc, ld, le, lf, lg, ltotal = row
    alias_up = alias.upper()

    # Buscar en BD (fuzzy: primeras 6 letras)
    bd = None
    for k in bd_map:
        if k == alias_up or k.startswith(alias_up[:6]) or alias_up.startswith(k[:6]):
            bd = bd_map[k]
            break

    if not bd:
        print(f"  ⚠ {alias:<23} NOT FOUND en BD")
        continue

    bd_a  = bd.get("cat_resultado",       0) or 0
    bd_b  = bd.get("cat_marcador",        0) or 0
    bd_c  = bd.get("cat_amarillas",       0) or 0
    bd_d  = bd.get("cat_rojas",           0) or 0
    bd_e  = bd.get("cat_var",             0) or 0
    bd_f  = bd.get("cat_penales_partido", 0) or 0
    bd_g  = bd.get("cat_minuto",          0) or 0
    bd_tot= (bd.get("puntos_total") or bd.get("puntos_partidos_total") or 0)

    live_vals = [la, lb, lc, ld, le, lf, lg, ltotal]
    bd_vals   = [bd_a, bd_b, bd_c, bd_d, bd_e, bd_f, bd_g, bd_tot]

    for col, lv, bv in zip(COLS, live_vals, bd_vals):
        diff = lv - bv
        if diff != 0:
            marker = "⚠" if abs(diff) > 2 else "~"
            print(f"  {marker} {alias:<23} {col:<15} {lv:>6} {bv:>6} {diff:>+6}")
            diferencias.append((alias, col, lv, bv, diff))

if not diferencias:
    print("  ✅ Sin diferencias encontradas")
else:
    print(f"\nTotal diferencias: {len(diferencias)}")
    # Agrupar por columna
    from collections import Counter
    col_count = Counter(d[1] for d in diferencias)
    print("\nDiferencias por columna:")
    for col, cnt in col_count.most_common():
        print(f"  {col}: {cnt} apostadores")
