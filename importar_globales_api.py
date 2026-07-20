"""
importar_globales_api.py
Lee pronósticos globales (P111-P118) del Excel consolidado y los importa
llamando al endpoint POST /bets/importar-globales-apostador/{torneo_id}.

Uso:
    python importar_globales_api.py <ruta_excel> [--torneo-id 2] [--dry-run]

Ejemplo:
    python importar_globales_api.py "20260611_2000- TBL CONSOLIDADA PRONOSTICOS ok.xlsx"
    python importar_globales_api.py "...xlsx" --dry-run
"""

import sys
import os
import json
import argparse
import unicodedata
import urllib.request
import urllib.error
import openpyxl

API_BASE   = "http://localhost:8000/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = "faute1964"
HOJA       = "50- TBL MASTER"
TORNEO_ID  = None   # None = auto-detect desde /torneo/activas

P_MAP = {
    "P111": "campeon",
    "P112": "otro_finalista",
    "P113": "goleador",
    "P114": "peor_equipo",
    "P115": "etapa_paraguay",
    "P116": "goles_paraguay",
    "P117": "goleada_ganador",
    "P118": "goleada_perdedor",
}

FASE_NORM = {
    "grupo": "grupos", "grupos": "grupos",
    "16avos": "16avos", "dieciseisavos": "16avos",
    "8vos": "8vos", "octavos": "8vos",
    "4tos": "4tos", "cuartos": "4tos",
    "semi": "semis", "semifinal": "semis", "semis": "semis",
    "3p": "3p", "tercer puesto": "3p",
    "final": "final",
}

# Mapeo nombres en español (Excel) → nombres en BD (inglés)
EQUIPO_ES_EN = {
    "espana": "Spain",
    "espanya": "Spain",
    "francia": "France",
    "inglaterra": "England",
    "brazil": "Brazil",
    "brasil": "Brazil",
    "curazao": "Curaçao",
    "curacao": "Curaçao",
    "nueva zelanda": "New Zealand",
    "nueva zelandia": "New Zealand",
    "marruecos": "Morocco",
    "alemania": "Germany",
    "belgica": "Belgium",
    "paises bajos": "Netherlands",
    "holanda": "Netherlands",
    "costa de marfil": "Ivory Coast",
    "arabia saudita": "Saudi Arabia",
    "arabia saudi": "Saudi Arabia",
    "corea del sur": "South Korea",
    "sudafrica": "South Africa",
    "sudáfrica": "South Africa",
    "turquia": "Türkiye",
    "turkiye": "Türkiye",
    "egipto": "Egypt",
    "noruega": "Norway",
    "suecia": "Sweden",
    "suiza": "Switzerland",
    "escocia": "Scotland",
    "estados unidos": "USA",
    "eeuu": "USA",
    "canada": "Canada",
    "haiti": "Haiti",
    "iran": "Iran",
    "irak": "Iraq",
    "jordania": "Jordan",
    "japon": "Japan",
    "bosnia": "Bosnia & Herzegovina",
    "republica checa": "Czech Republic",
    "uzbekistan": "Uzbekistan",
    "panama": "Panama",
    "congo": "Congo DR",
    "republica democratica del congo": "Congo DR",
    "argelia": "Algeria",
    "cabo verde": "Cape Verde Islands",
    "islas cabo verde": "Cape Verde Islands",
    "republica checa": "Czech Republic",
    # Nombres que ya están en inglés (por si acaso):
    "spain": "Spain",
    "brazil": "Brazil",
    "france": "France",
    "germany": "Germany",
    "england": "England",
    "netherlands": "Netherlands",
    "belgium": "Belgium",
    "portugal": "Portugal",
    "argentina": "Argentina",
    "mexico": "Mexico",
    "usa": "USA",
    "uruguay": "Uruguay",
    "croatia": "Croatia",
    "colombia": "Colombia",
    "morocco": "Morocco",
    "senegal": "Senegal",
    "ecuador": "Ecuador",
    "ghana": "Ghana",
    "japan": "Japan",
    "south korea": "South Korea",
    "australia": "Australia",
    "new zealand": "New Zealand",
    "paraguay": "Paraguay",
    "canada": "Canada",
    "norway": "Norway",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "denmark": "Denmark",
    "iran": "Iran",
    "iraq": "Iraq",
    "saudi arabia": "Saudi Arabia",
    "egypt": "Egypt",
    "algeria": "Algeria",
    "tunisia": "Tunisia",
    "ivory coast": "Ivory Coast",
    "south africa": "South Africa",
    "scotland": "Scotland",
    "austria": "Austria",
    "turkey": "Türkiye",
}

def traducir_equipo(nombre: str) -> str:
    """Traduce nombre de equipo español/variante → nombre en BD."""
    if not nombre:
        return nombre
    key = unicodedata.normalize("NFKD", nombre.strip().lower()).encode("ascii", "ignore").decode()
    return EQUIPO_ES_EN.get(key, nombre)

def norm(s):
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s

def limpiar_alias(v):
    if v is None: return ""
    return str(v).replace("\xa0", "").strip()

def api_post(path, body, token=None):
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8")), r.status
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        try:
            return json.loads(body_err), e.code
        except:
            return {"detail": body_err}, e.code

def api_get(path, token=None):
    url = API_BASE + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8")), r.status
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        try:
            return json.loads(body_err), e.code
        except Exception:
            return {"detail": body_err}, e.code


def login():
    resp, code = api_post("/auth/login", {"username": ADMIN_USER, "password": ADMIN_PASS})
    if code != 200 or "access_token" not in resp:
        raise RuntimeError(f"Login fallido ({code}): {resp}")
    return resp["access_token"]


def get_active_torneo_id(token: str) -> int:
    """Retorna el ID del torneo activo. Falla si no hay ninguno."""
    resp, code = api_get("/torneo/activas", token)
    if code == 200 and isinstance(resp, list) and resp:
        tid = resp[0].get("id") or resp[0].get("torneo_id")
        nombre = resp[0].get("nombre", "")
        print(f"  Torneo activo detectado: '{nombre}' (id={tid})")
        return int(tid)
    raise RuntimeError(
        f"No se pudo detectar torneo activo (HTTP {code}). "
        "Pasá --torneo-id manualmente."
    )

def leer_globales(path):
    """Retorna {alias: {campo: valor}}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[HOJA]
    datos = {}
    for row in ws.iter_rows(values_only=True):
        pid = str(row[1]).strip() if row[1] else ""
        if pid not in P_MAP:
            continue
        campo = P_MAP[pid]
        alias = limpiar_alias(row[9]).lower()
        valor = row[10]
        if not alias or valor is None or str(valor).strip() == "":
            continue
        if alias not in datos:
            datos[alias] = {}
        datos[alias][campo] = str(valor).strip() if isinstance(valor, str) else valor
    wb.close()
    return datos

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel")
    parser.add_argument("--torneo-id", type=int, default=None,
                        help="ID del torneo (default: auto desde /torneo/activas)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.excel):
        print(f"ERROR: No existe {args.excel}")
        sys.exit(1)

    print(f"Leyendo {args.excel} ...")
    globales = leer_globales(args.excel)
    print(f"Apostadores con globales: {len(globales)}\n")

    token = None
    torneo_id = args.torneo_id
    if not args.dry_run:
        print("Login como admin ...")
        token = login()
        print("  Token OK")
        if torneo_id is None:
            torneo_id = get_active_torneo_id(token)
        print()

    ok = err = 0

    for alias, d in sorted(globales.items()):
        # Construir body para el endpoint
        etapa_raw  = str(d.get("etapa_paraguay", "")).strip()
        etapa_norm = FASE_NORM.get(norm(etapa_raw), etapa_raw) if etapa_raw else None

        def to_int(v):
            try: return int(v) if v is not None else None
            except: return None

        campeon_tr   = traducir_equipo(d.get("campeon"))
        finalista_tr = traducir_equipo(d.get("otro_finalista"))
        peor_tr      = traducir_equipo(d.get("peor_equipo"))

        body = {
            "apostador":            alias,
            "pred_campeon":         campeon_tr,
            "pred_finalista1":      campeon_tr,       # campeon tambien es finalista
            "pred_finalista2":      finalista_tr,
            "pred_goleador":        d.get("goleador"),
            "pred_peor_equipo":     peor_tr,
            "pred_etapa_paraguay":  etapa_norm,
            "pred_goles_paraguay":  to_int(d.get("goles_paraguay")),
            "pred_goleada_ganador": to_int(d.get("goleada_ganador")),
            "pred_goleada_perdedor":to_int(d.get("goleada_perdedor")),
        }

        if args.dry_run or token is None:
            print(f"  [{alias}]")
            print(f"    A={body['pred_campeon']}  B={body['pred_finalista2']}  C={body['pred_goleador']}")
            print(f"    D={body['pred_peor_equipo']}  E={body['pred_goleada_ganador']}-{body['pred_goleada_perdedor']}")
            print(f"    F={etapa_raw}→{etapa_norm}  G={body['pred_goles_paraguay']}")
            ok += 1
            continue

        resp, code = api_post(
            f"/bets/importar-globales-apostador/{torneo_id}",
            body, token
        )
        if code == 200 and resp.get("ok"):
            nr = resp.get("no_resueltos_input", {})
            status = "⚠️  sin resolver: " + str(nr) if nr else "✓"
            print(f"  [{alias}] {status}")
            ok += 1
        else:
            detail = resp.get("detail", resp)
            print(f"  [{alias}] ✗ ERROR {code}: {detail}")
            err += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Resultado: {ok} OK, {err} errores")

if __name__ == "__main__":
    main()
