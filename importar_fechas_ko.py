"""
importar_fechas_ko.py
====================
Importa las fechas y horas OFICIALES FIFA 2026 para TODOS los partidos KO
(R32 + R16 + Cuartos + Semis + 3er puesto + Final).

Fuente: Yahoo Sports / FIFA.com (verificado 2026-06-28)
Todos los tiempos se almacenan en UTC (naive, sin timezone).

Ejecutar desde el venv del backend:
    cd "C:\proyecto FAST API\backend"
    .venv\Scripts\Activate.ps1
    python ..\importar_fechas_ko.py
"""
import asyncio
import asyncpg
from datetime import datetime, timezone, timedelta

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2

def et(month, day, hour, minute=0, year=2026):
    """Convierte hora Eastern Time (EDT = UTC-4) a UTC naive."""
    dt_et = datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(hours=-4)))
    return dt_et.astimezone(timezone.utc).replace(tzinfo=None)

# ── RONDA 32 (P73-P88) ───────────────────────────────────────────────────────
# Fuente: Yahoo Sports. Todos los tiempos en ET (EDT = UTC-4).
R32_SCHEDULE = [
    # num  datetime UTC naive                                  ciudad
    (73,  et(6, 28,  15,  0), "Los Ángeles",  "SoFi Stadium"),          # 3pm ET = 19:00 UTC
    (76,  et(6, 29,  13,  0), "Houston",       "NRG Stadium"),           # 1pm ET = 17:00 UTC
    (74,  et(6, 29,  16, 30), "Boston",        "Gillette Stadium"),      # 4:30pm ET = 20:30 UTC
    (75,  et(6, 29,  21,  0), "Monterrey",     "Estadio BBVA"),          # 9pm ET = 01:00 UTC Jun30
    (78,  et(6, 30,  13,  0), "Dallas",        "AT&T Stadium"),          # 1pm ET = 17:00 UTC
    (77,  et(6, 30,  17,  0), "Nueva York/NJ", "MetLife Stadium"),       # 5pm ET = 21:00 UTC
    (79,  et(6, 30,  21,  0), "Ciudad de México","Estadio Azteca"),      # 9pm ET = 01:00 UTC Jul1
    (81,  et(7,  1,  12,  0), "Atlanta",       "Mercedes-Benz Stadium"), # 12pm ET = 16:00 UTC
    (87,  et(7,  1,  16,  0), "Seattle",       "Lumen Field"),           # 4pm ET = 20:00 UTC
    (80,  et(7,  1,  20,  0), "San Francisco", "Levi's Stadium"),        # 8pm ET = 00:00 UTC Jul2
    (85,  et(7,  2,  15,  0), "Los Ángeles",   "SoFi Stadium"),          # 3pm ET = 19:00 UTC
    (88,  et(7,  2,  19,  0), "Toronto",       "BMO Field"),             # 7pm ET = 23:00 UTC
    (86,  et(7,  2,  23,  0), "Vancouver",     "BC Place"),              # 11pm ET = 03:00 UTC Jul3
    (83,  et(7,  3,  14,  0), "Dallas",        "AT&T Stadium"),          # 2pm ET = 18:00 UTC
    (82,  et(7,  3,  18,  0), "Miami",         "Hard Rock Stadium"),     # 6pm ET = 22:00 UTC
    (84,  et(7,  3,  21, 30), "Kansas City",   "Arrowhead Stadium"),     # 9:30pm ET = 01:30 UTC Jul4
]

# ── RONDA 16 (P89-P96) ───────────────────────────────────────────────────────
R16_SCHEDULE = [
    (89,  et(7,  4,  13,  0), "Houston",       "NRG Stadium"),           # 1pm ET = 17:00 UTC
    (90,  et(7,  4,  17,  0), "Philadelphia",  "Lincoln Financial"),     # 5pm ET = 21:00 UTC
    (91,  et(7,  5,  16,  0), "Nueva York/NJ", "MetLife Stadium"),       # 4pm ET = 20:00 UTC
    (92,  et(7,  5,  20,  0), "Ciudad de México","Estadio Azteca"),      # 8pm ET = 00:00 UTC Jul6
    (93,  et(7,  6,  15,  0), "Dallas",        "AT&T Stadium"),          # 3pm ET = 19:00 UTC
    (94,  et(7,  6,  20,  0), "Seattle",       "Lumen Field"),           # 8pm ET = 00:00 UTC Jul7
    (95,  et(7,  7,  12,  0), "Atlanta",       "Mercedes-Benz Stadium"), # 12pm ET = 16:00 UTC
    (96,  et(7,  7,  16,  0), "Vancouver",     "BC Place"),              # 4pm ET = 20:00 UTC
]

# ── CUARTOS (P97-P100) ───────────────────────────────────────────────────────
QF_SCHEDULE = [
    (97,  et(7,  9,  16,  0), "Boston",        "Gillette Stadium"),      # 4pm ET = 20:00 UTC
    (98,  et(7, 10,  15,  0), "Los Ángeles",   "SoFi Stadium"),          # 3pm ET = 19:00 UTC
    (99,  et(7, 11,  17,  0), "Miami",         "Hard Rock Stadium"),     # 5pm ET = 21:00 UTC
    (100, et(7, 11,  21,  0), "Kansas City",   "Arrowhead Stadium"),     # 9pm ET = 01:00 UTC Jul12
]

# ── SEMIS (P101-P102) ────────────────────────────────────────────────────────
SF_SCHEDULE = [
    (101, et(7, 14,  15,  0), "Dallas",        "AT&T Stadium"),          # 3pm ET = 19:00 UTC
    (102, et(7, 15,  15,  0), "Atlanta",       "Mercedes-Benz Stadium"), # 3pm ET = 19:00 UTC
]

# ── TERCER PUESTO (P103) + FINAL (P104) ──────────────────────────────────────
FINAL_SCHEDULE = [
    (103, et(7, 18,  17,  0), "Miami",         "Hard Rock Stadium"),     # 5pm ET = 21:00 UTC
    (104, et(7, 19,  15,  0), "Nueva York/NJ", "MetLife Stadium"),       # 3pm ET = 19:00 UTC
]

ALL_SCHEDULE = R32_SCHEDULE + R16_SCHEDULE + QF_SCHEDULE + SF_SCHEDULE + FINAL_SCHEDULE


async def main():
    conn = await asyncpg.connect(DB_DSN)

    print("=" * 70)
    print("IMPORTAR FECHAS/HORAS KO FIFA 2026 — COMPLETO P73-P104")
    print("Fuente: Yahoo Sports / FIFA.com  |  Tiempos en UTC")
    print("=" * 70)

    # Obtener todos los partidos KO con sus datos actuales
    ko_rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.fecha, f.tipo,
               COALESCE(el.nombre_es, el.nombre, 'TBD') AS local,
               COALESCE(ev.nombre_es, ev.nombre, 'TBD') AS visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1 AND f.tipo <> 'grupo'
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    pid_by_num    = {r["numero_fifa"]: r["id"]        for r in ko_rows}
    fecha_by_num  = {r["numero_fifa"]: r["fecha"]     for r in ko_rows}
    tipo_by_num   = {r["numero_fifa"]: r["tipo"]      for r in ko_rows}
    local_by_num  = {r["numero_fifa"]: r["local"]     for r in ko_rows}
    visit_by_num  = {r["numero_fifa"]: r["visitante"] for r in ko_rows}

    print(f"\n{len(ko_rows)} partidos KO en BD\n")

    seccion_actual = None
    updated = 0
    missing = 0

    SECCIONES = {
        **{n: "── R32 ──" for n,*_ in R32_SCHEDULE},
        **{n: "── R16 ──" for n,*_ in R16_SCHEDULE},
        **{n: "── CUARTOS ──" for n,*_ in QF_SCHEDULE},
        **{n: "── SEMIS ──" for n,*_ in SF_SCHEDULE},
        **{n: "── 3P / FINAL ──" for n,*_ in FINAL_SCHEDULE},
    }

    for num, dt_utc, ciudad, estadio in ALL_SCHEDULE:
        sec = SECCIONES.get(num, "")
        if sec != seccion_actual:
            print(f"\n  {sec}")
            seccion_actual = sec

        pid = pid_by_num.get(num)
        if not pid:
            print(f"  P{num:<3} *** NO ENCONTRADO EN BD (revisar fix_numero_fifa_ko.py) ***")
            missing += 1
            continue

        current_fecha = fecha_by_num.get(num)
        matchup       = f"{local_by_num.get(num,'?')} vs {visit_by_num.get(num,'?')}"

        await conn.execute(
            "UPDATE partido SET fecha = $1 WHERE id = $2",
            dt_utc, pid
        )
        updated += 1

        # Display en CR (UTC-6)
        dt_cr = dt_utc + timedelta(hours=-6)
        cr_str = dt_cr.strftime("%a %d/%m %H:%M")

        prev = f"[era: {str(current_fecha)[:16]}]" if current_fecha else "[sin fecha]"
        print(f"  P{num:<3} {matchup:<38} {cr_str} CR  | {ciudad}  {prev}")

    print(f"\n{'='*70}")
    print(f"  Actualizados: {updated}  |  Sin match en BD: {missing}")
    print("=" * 70)

    await conn.close()
    print("\n✅ Listo. El bracket mostrará fechas/horas en todos los partidos KO.")


if __name__ == "__main__":
    asyncio.run(main())
