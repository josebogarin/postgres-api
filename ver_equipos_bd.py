import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='becbuc', user='app_user', password='superpassword')
cur = conn.cursor()
cur.execute("SELECT id, nombre, nombre_es, COALESCE(codigo_iso,'-'), COALESCE(fifa_ranking::text,'-') FROM equipo ORDER BY nombre")
rows = cur.fetchall()
conn.close()
lines = ['id | nombre | nombre_es | iso | ranking']
lines += [f'{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}' for r in rows]
txt = '\n'.join(lines)
open('equipos_bd.txt', 'w', encoding='utf-8').write(txt)
print(f'Guardado equipos_bd.txt ({len(rows)} equipos)')
