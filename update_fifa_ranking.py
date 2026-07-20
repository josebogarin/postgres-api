"""
update_fifa_ranking.py
Actualiza equipo.fifa_ranking en la BD con el ranking FIFA oficial (11 junio 2026, antes del Mundial)
Fuente: ESPN / FIFA - https://www.espn.com/soccer/story/_/id/46664763/fifa-mens-top-50-world-rankings
"""
import asyncio
import asyncpg

DB_DSN = "postgresql://app_user@localhost:5432/becbuc"

# Ranking FIFA oficial junio 2026 (nombre como aparece en la BD → rank)
# Usamos variantes comunes del nombre para hacer el match
FIFA_RANKING = [
    (1,   ["Argentina"]),
    (2,   ["Spain", "España"]),
    (3,   ["France", "Francia"]),
    (4,   ["England", "Inglaterra"]),
    (5,   ["Portugal"]),
    (6,   ["Brazil", "Brasil"]),
    (7,   ["Morocco", "Marruecos"]),
    (8,   ["Netherlands", "Países Bajos", "Holanda"]),
    (9,   ["Belgium", "Bélgica", "BELGICA"]),
    (10,  ["Germany", "Alemania"]),
    (11,  ["Croatia", "Croacia", "CROACIA"]),
    (12,  ["Italy", "Italia"]),
    (13,  ["Colombia"]),
    (14,  ["Mexico", "México", "MEXICO"]),
    (15,  ["Senegal", "SENEGAL"]),
    (16,  ["Uruguay"]),
    (17,  ["USA", "United States", "Estados Unidos", "ESTADOS UNIDOS"]),
    (18,  ["Japan", "Japón", "JAPON"]),
    (19,  ["Switzerland", "Suiza", "SUIZA"]),
    (20,  ["Iran", "Irán", "IRAN"]),
    (21,  ["Denmark", "Dinamarca"]),
    (22,  ["Türkiye", "Turkey", "Turquía", "TURKIYE"]),
    (23,  ["Ecuador", "ECUADOR"]),
    (24,  ["Austria"]),
    (25,  ["South Korea", "Korea Republic", "Corea del Sur", "COREA DEL SUR"]),
    (26,  ["Nigeria"]),
    (27,  ["Australia"]),
    (28,  ["Algeria", "Argelia", "ALGERIA"]),
    (29,  ["Egypt", "Egipto"]),
    (30,  ["Canada"]),
    (31,  ["Norway", "Noruega", "NORWAY"]),
    (32,  ["Ukraine", "Ucrania"]),
    (33,  ["Ivory Coast", "Côte d'Ivoire", "Costa de Marfil"]),
    (34,  ["Panama", "Panamá", "PANAMA"]),
    (35,  ["Russia", "Rusia"]),
    (36,  ["Poland", "Polonia"]),
    (37,  ["Wales", "Gales"]),
    (38,  ["Sweden", "Suecia", "SWEDEN"]),
    (39,  ["Hungary", "Hungría"]),
    (40,  ["Czechia", "Czech Republic", "República Checa"]),
    (41,  ["Paraguay", "PARAGUAY"]),
    (42,  ["Scotland", "Escocia", "SCOTLAND"]),
    (43,  ["Serbia"]),
    (44,  ["Cameroon", "Camerún"]),
    (45,  ["Tunisia", "Túnez"]),
    (46,  ["Congo DR", "DR Congo", "Congo DRC", "Democratic Republic of the Congo"]),
    (47,  ["Slovakia", "Eslovaquia"]),
    (48,  ["Greece", "Grecia"]),
    (49,  ["Venezuela"]),
    (50,  ["Uzbekistan"]),
    # Fuera del top 50 pero en el Mundial:
    (56,  ["Qatar"]),
    (57,  ["Iraq"]),
    (60,  ["South Africa", "Sudáfrica"]),
    (61,  ["Saudi Arabia", "Arabia Saudita"]),
    (63,  ["Jordan", "Jordania"]),
    (64,  ["Bosnia and Herzegovina", "Bosnia y Herzegovina", "BOSNIA Y HERZEGOVINA"]),
    (67,  ["Cape Verde", "Cape Verde Islands", "Cabo Verde"]),
    (73,  ["Ghana"]),
    (82,  ["Curaçao", "Curacao", "CURACAO"]),
    (83,  ["Haiti", "Haití"]),
    (85,  ["New Zealand", "Nueva Zelanda"]),
]


async def main():
    conn = await asyncpg.connect(DB_DSN)
    try:
        # Cargar todos los equipos de la BD
        rows = await conn.fetch("SELECT id, nombre, nombre_es FROM equipo ORDER BY nombre")
        equipos = [(r["id"], r["nombre"] or "", r["nombre_es"] or "") for r in rows]

        actualizados = []
        sin_match = []

        for rank, nombres in FIFA_RANKING:
            matched_id = None
            for eid, nombre, nombre_es in equipos:
                for n in nombres:
                    if (n.strip().lower() == nombre.strip().lower() or
                            n.strip().lower() == nombre_es.strip().lower()):
                        matched_id = eid
                        break
                if matched_id:
                    break

            if matched_id:
                await conn.execute(
                    "UPDATE equipo SET fifa_ranking = $1 WHERE id = $2",
                    rank, matched_id
                )
                actualizados.append((rank, nombres[0]))
            else:
                sin_match.append((rank, nombres))

        print(f"\n✅ Actualizados: {len(actualizados)} equipos")
        for rank, nombre in sorted(actualizados):
            print(f"   #{rank:3d}  {nombre}")

        if sin_match:
            print(f"\n⚠️  Sin match ({len(sin_match)}) — verificar nombres en BD:")
            for rank, nombres in sin_match:
                print(f"   #{rank:3d}  {nombres}")

        # Mostrar equipos que quedaron con fifa_ranking=NULL
        nulls = await conn.fetch(
            "SELECT nombre, nombre_es FROM equipo WHERE fifa_ranking IS NULL ORDER BY nombre"
        )
        if nulls:
            print(f"\nEquipos aún sin ranking ({len(nulls)}):")
            for r in nulls:
                print(f"   {r['nombre']} / {r['nombre_es']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
