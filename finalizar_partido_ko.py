"""
Finaliza un partido KO que quedó trabado en estado 'en_juego'.
Maneja: tiempo reglamentario, prórroga y tanda de penales.

Uso interactivo (doble clic en el .bat):
  python finalizar_partido_ko.py

Uso con argumentos:
  python finalizar_partido_ko.py 90 2 1
  python finalizar_partido_ko.py 90 1 1 4 2    (empate, ganó local 4-2 en penales)
"""
import sys, urllib.request, urllib.parse, json

BASE = 'http://localhost:8000'

def ask_int(prompt, min_val=0, max_val=99):
    while True:
        try:
            val = input(prompt).strip()
            if val == '':
                print("  (campo requerido, ingresa un número)")
                continue
            v = int(val)
            if v < min_val or v > max_val:
                print(f"  (debe ser entre {min_val} y {max_val})")
                continue
            return v
        except ValueError:
            print("  (ingresa solo números, sin letras)")

def ask_yn(prompt):
    while True:
        r = input(prompt).strip().lower()
        if r in ('s', 'si', 'sí', 'y', 'yes'):
            return True
        if r in ('n', 'no', ''):
            return False
        print("  (ingresa s o n)")

def login():
    data = json.dumps({'username': 'jose', 'password': 'catalina'}).encode()
    req = urllib.request.Request(f'{BASE}/api/v1/auth/login', data=data,
                                  headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']

def get_bracket(token):
    req = urllib.request.Request(f'{BASE}/api/v1/bets/bracket-real/2',
                                  headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def main():
    print("=" * 50)
    print("  Finalizar partido KO (emergencia)")
    print("=" * 50)

    # Parsear args o pedir interactivamente
    if len(sys.argv) >= 4:
        numero_fifa = int(sys.argv[1])
        gl = int(sys.argv[2])
        gv = int(sys.argv[3])
        pen_l = int(sys.argv[4]) if len(sys.argv) > 4 else None
        pen_v = int(sys.argv[5]) if len(sys.argv) > 5 else None
    else:
        print()
        numero_fifa = ask_int("Numero del partido (ej: 90 para P90): ", 73, 104)

        print()
        print("Score al final (tiempo reglamentario o prorroga):")
        gl = ask_int("  Goles LOCAL: ", 0, 30)
        gv = ask_int("  Goles VISITANTE: ", 0, 30)

        pen_l = pen_v = None
        if gl == gv:
            print()
            if ask_yn("Termino empatado -> hubo tanda de penales? (s/n): "):
                pen_l = ask_int("  Penales LOCAL (tanda): ", 0, 20)
                pen_v = ask_int("  Penales VISITANTE (tanda): ", 0, 20)

    print()
    print("Conectando al servidor...")
    try:
        token = login()
    except Exception as e:
        print(f"ERROR login: {e}")
        print("Verificar que uvicorn este activo en puerto 8000.")
        sys.exit(1)
    print("Login OK")

    try:
        bracket = get_bracket(token)
    except Exception as e:
        print(f"ERROR obteniendo bracket: {e}")
        sys.exit(1)

    partido = next((p for p in bracket if p.get('numero_fifa') == numero_fifa), None)
    if not partido:
        # Buscar en todos (incluyendo grupos por si acaso)
        print(f"ERROR: No se encontro partido con numero_fifa={numero_fifa}")
        print("Partidos KO disponibles:")
        for p in sorted(bracket, key=lambda x: x.get('numero_fifa') or 0):
            nf = p.get('numero_fifa')
            if nf and nf >= 73:
                print(f"  P{nf}: {p.get('equipo_local','?')} vs {p.get('equipo_visitante','?')} [{p.get('estado','?')}]")
        sys.exit(1)

    pid      = partido['id']
    local    = partido.get('equipo_local', '?')
    visitante= partido.get('equipo_visitante', '?')
    estado   = partido.get('estado', '?')
    gl_bd    = partido.get('goles_local')
    gv_bd    = partido.get('goles_visitante')

    print()
    print(f"Partido encontrado: P{numero_fifa} -- {local} vs {visitante}")
    print(f"  Estado actual BD: {gl_bd}-{gv_bd} [{estado}]")
    print(f"  Score a guardar:  {gl}-{gv}" + (f"  (penales {pen_l}-{pen_v})" if pen_l is not None else ""))
    print()

    if not ask_yn("Confirmar? (s/n): "):
        print("Cancelado.")
        sys.exit(0)

    qs = f'?goles_local={gl}&goles_visitante={gv}'
    if pen_l is not None:
        qs += f'&penales_local={pen_l}&penales_visitante={pen_v}'

    try:
        req3 = urllib.request.Request(
            f'{BASE}/api/v1/bets/finalizar-partido/{pid}{qs}',
            method='POST',
            headers={'Authorization': 'Bearer ' + token, 'Content-Length': '0'}
        )
        with urllib.request.urlopen(req3, timeout=60) as r:
            res = json.loads(r.read())
    except Exception as e:
        print(f"ERROR al finalizar: {e}")
        sys.exit(1)

    print()
    print(f"Partido finalizado exitosamente!")
    print(f"  Bracket avanzado: {res.get('bracket_ok', '?')}")
    print(f"  Puntajes OK:      {res.get('puntajes_ok', '?')}")
    if res.get('puntajes'):
        p = res['puntajes']
        print(f"  Plenos: {p.get('plenos')} | Aciertos: {p.get('aciertos')}")
    print()

if __name__ == '__main__':
    main()
