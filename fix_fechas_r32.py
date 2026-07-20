"""
Corrige las fechas/horas de los partidos R32 (P73-P88).
El script import_fechas_ko.py tuvo errores de conversión de timezone.
Horas correctas basadas en horarios oficiales FIFA 2026 (sesion 47 + busqueda web).
CR = UTC-6 -> hora_CR + 6h = UTC
"""
import asyncio
import asyncpg
from datetime import datetime, timezone

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"

# (numero_fifa, utc_correcto, cr_display, descripcion)
FIXES = [
    # Jun 28 - P73 DB=11:00 CR, correcto=13:00 CR (noon PDT Los Angeles)
    (73,  '2026-06-28T19:00:00+00:00', '13:00 CR Jun 28', 'South Africa/Canada - Los Angeles'),
    # P74 OK: 23:30 UTC = 17:30 CR (Germany/Paraguay Boston) - no tocar
    # P75 OK: 04:00 UTC Jun30 = 22:00 CR Jun29 (Netherlands/Morocco) - no tocar
    # Jun 29 - P76 DB=14:00 CR, correcto=14:30 CR (Houston)
    (76,  '2026-06-29T20:30:00+00:00', '14:30 CR Jun 29', 'Brazil/Japan - Houston'),
    # Jun 30 URGENTES - CONFIRMADAS POR BUSQUEDA WEB (1 PM / 5 PM / 9 PM ET)
    (78,  '2026-06-30T17:00:00+00:00', '11:00 CR Jun 30', 'Ivory Coast/Norway - Dallas [1 PM ET CONF.]'),
    (77,  '2026-06-30T21:00:00+00:00', '15:00 CR Jun 30', 'France/Sweden - New York [5 PM ET CONF.]'),
    (79,  '2026-07-01T01:00:00+00:00', '19:00 CR Jun 30', 'Mexico/Ecuador - CDMX [9 PM ET CONF.]'),
    # Jul 1
    (80,  '2026-07-01T16:00:00+00:00', '10:00 CR Jul 1',  'England/Congo DR - Atlanta [noon ET]'),
    (82,  '2026-07-01T20:00:00+00:00', '14:00 CR Jul 1',  'Belgium/Senegal - Seattle [4 PM ET]'),
    (81,  '2026-07-02T00:00:00+00:00', '18:00 CR Jul 1',  'USA/Bosnia - San Francisco [8 PM ET]'),
    # Jul 2
    (84,  '2026-07-02T19:00:00+00:00', '13:00 CR Jul 2',  'Spain/Austria - Los Angeles [1 PM ET]'),
    (83,  '2026-07-02T23:00:00+00:00', '17:00 CR Jul 2',  'Portugal/Croatia - Toronto [7 PM ET]'),
    (85,  '2026-07-03T03:00:00+00:00', '21:00 CR Jul 2',  'Switzerland/Algeria - Vancouver [11 PM ET]'),
    # Jul 3
    (88,  '2026-07-03T18:00:00+00:00', '12:00 CR Jul 3',  'Australia/Egypt - Dallas [2 PM ET]'),
    (86,  '2026-07-03T22:00:00+00:00', '16:00 CR Jul 3',  'Argentina/Cape Verde - Miami [6 PM ET]'),
    (87,  '2026-07-04T01:30:00+00:00', '19:30 CR Jul 3',  'Colombia/Ghana - Kansas City [9:30 PM ET]'),
]

async def run():
    conn = await asyncpg.connect(DB_DSN)
    try:
        print("=== CORRECCIÓN FECHAS R32 FIFA 2026 ===\n")
        updated = 0
        for num, utc, cr, desc in FIXES:
            row = await conn.fetchrow(
                "SELECT numero_fifa, fecha FROM partido WHERE numero_fifa=$1", num
            )
            if not row:
                print(f"  P{num}: NO ENCONTRADO - omitido")
                continue
            old = row['fecha']
            await conn.execute(
                "UPDATE partido SET fecha=$1 WHERE numero_fifa=$2", utc, num
            )
            print(f"P{num:02d} {desc}")
            print(f"  Antes: {old}")
            print(f"  Ahora: {utc} ({cr}) ✓\n")
            updated += 1
        print(f"✅ {updated} partidos actualizados.")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
