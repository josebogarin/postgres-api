"""verificar_p49.py v7 - solo ASCII en output"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2, unicodedata, os

def ascii_safe(s):
    if not s: return ''
    # Normalize to remove accents
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if ord(c) < 128)

conn = psycopg2.connect(host="localhost", port=5432, user="app_user", password="superpassword", dbname="becbuc")
cur = conn.cursor()

cur.execute("SELECT id, equipo_local_id, equipo_visitante_id FROM partido WHERE numero_fifa=49")
p49 = cur.fetchone()
p49_id, p49_leq, p49_veq = p49

cur.execute("SELECT nombre, goles_local, goles_visitante, idequipolocal, idequipovisitante FROM pronosticos_aux WHERE id_partido='P049' ORDER BY nombre")
paux49 = cur.fetchall()

cur.execute("SELECT nombre, goles_local, goles_visitante, idequipolocal, idequipovisitante FROM pronosticos_aux WHERE id_partido='P050' ORDER BY nombre")
paux50 = cur.fetchall()

cur.execute("SELECT nombre_apostador, pred_local, pred_visitante FROM apuesta WHERE partido_id=%s ORDER BY nombre_apostador", (p49_id,))
apet49 = cur.fetchall()
cur.close(); conn.close()

# Build maps with ASCII keys
paux50_map = {ascii_safe(r[0]).strip().lower(): (r[1], r[2]) for r in paux50}
apet49_map = {ascii_safe((r[0] or '')).strip().lower(): (r[1], r[2]) for r in apet49}

# Compare
ok=swap=0; diffs=[]; noap=[]; rows=[]
for nombre, (px_l, px_v) in sorted(paux50_map.items()):
    av = apet49_map.get(nombre)
    if av is None:
        for k,v in apet49_map.items():
            if k and nombre and (nombre in k or k in nombre):
                av=v; break
    bd_l = av[0] if av is not None else None
    bd_v = av[1] if av is not None else None
    if av is None:
        st='SIN_APO'; noap.append(nombre)
    elif bd_l==px_l and bd_v==px_v:
        st='OK'; ok+=1
    elif bd_l==px_v and bd_v==px_l:
        st='SWAP'; swap+=1
    else:
        st='DIFF'; diffs.append(f"{nombre}: p050={px_l}-{px_v} bd={bd_l}-{bd_v}")
    rows.append(f"  {nombre[:28]:<28} {str(px_l):>5} {str(px_v):>5} {str(bd_l):>5} {str(bd_v):>5}  {st}")

# Build output (all ASCII)
out = []
out.append("=== VERIFICACION P49 Morocco vs Haiti ===")
out.append(f"Partido P49: id={p49_id}, eq_local={p49_leq}, eq_visit={p49_veq}")
out.append(f"paux P049 eq_local={paux49[0][3] if paux49 else '?'} eq_visit={paux49[0][4] if paux49 else '?'}  <- ESCOCIA/BRASIL (NO es Morocco/Haiti)")
out.append(f"paux P050 eq_local={paux50[0][3] if paux50 else '?'} eq_visit={paux50[0][4] if paux50 else '?'}  <- MOROCCO/HAITI (correcto)")
out.append(f"Keys iguales: {sum(1 for k in paux50_map if k in apet49_map)} de {len(paux50_map)}")
out.append("")
out.append(f"{'nombre':<30} {'p50_l':>5} {'p50_v':>5} {'bd_l':>5} {'bd_v':>5}  estado")
out.append("-"*72)
out.extend(rows)
out.append("")
out.append(f"RESUMEN: OK={ok}  SWAP={swap}  DIFF={len(diffs)}  SIN_APO={len(noap)}")
for d in diffs:
    out.append(f"  DIFF: {d}")
if noap:
    out.append(f"  SIN_APO: {noap}")

text = '\n'.join(out)
outpath = _osp.path.join(_BASE, 'verificar_p49_output.txt')
with open(outpath, 'w', encoding='ascii') as f:
    f.write(text)
    f.flush()
    os.fsync(f.fileno())

print(f"LISTO: OK={ok} SWAP={swap} DIFF={len(diffs)} SIN_APO={len(noap)}")
print(text)
