"""
comparar_excel_vs_bd.py - Compara puntajes Excel TBL CHECK vs BD becbuc.
Items: H,I,J,K,L,M,N, O_tanda (Excel O_eq1 + P_eq2 = BD pts_penales_tanda).
Excluye: Q (clasificados).
"""

import sys
import psycopg2
import psycopg2.extras

TORNEO_ID = 2
DB_BECBUC = "host=localhost dbname=becbuc user=app_user password=superpassword"
DB_APP    = "host=localhost dbname=app_db  user=app_user password=superpassword"

# Datos Excel: H,I,J,K,L,M,N, O_eq1,P_eq2
EXCEL = {
    "checho":                (306,180,20,78,28,79,5,4,6),
    "seba":                  (282,188,19,80,44,69,2,0,2),
    "lav":                   (282,168,19,85,21,79,3,4,8),
    "patito":                (290,100,26,85,55,79,0,0,4),
    "vitra":                 (250,124,19,85,55,79,2,4,6),
    "fscc":                  (280,136,13,81,31,79,0,0,2),
    "hs":                    (270,128,16,85,43,70,3,0,0),
    "pato":                  (268,120,15,80,53,71,2,2,2),
    "fidelyoli":             (244,148,21,85,27,75,0,4,6),
    "alevo":                 (260,136,23,84,33,67,1,0,2),
    "oti":                   (274,112,19,85,31,79,3,0,2),
    "coco":                  (266,112,25,85,23,79,6,0,4),
    "moro":                  (256,132,19,75,28,79,4,0,0),
    "gh1s":                  (274,88,21,85,28,79,3,0,6),
    "gustav tothelighthouse":(254,80,15,85,58,79,0,4,8),
    "sanbie":                (254,128,19,82,3,76,3,4,6),
    "soni":                  (262,96,14,76,50,67,3,0,4),
    "alfaorion 99":          (276,96,11,75,42,63,5,0,0),
    "sajano freddy":         (276,96,11,75,42,63,5,0,0),
    "grillito":              (254,128,15,79,8,65,3,4,6),
    "@bs":                   (252,116,8,79,38,64,2,0,0),
    "juane":                 (262,136,15,75,11,51,0,0,0),
    "cherem":                (234,96,21,82,26,79,1,4,2),
    "hakembo":               (260,104,9,80,19,69,4,0,0),
    "luisma":                (240,120,21,77,14,65,0,4,0),
    "tony":                  (256,112,22,55,16,62,2,0,4),
    "eliasmajul":            (244,68,20,79,30,77,1,4,2),
    "kikao":                 (246,88,13,72,24,71,5,0,2),
    "pinguero":              (250,96,21,64,17,69,3,0,0),
    "coto":                  (250,72,23,76,10,80,3,0,0),
    "alejandrolegui":        (204,96,19,73,46,68,2,0,6),
    "quiroga":               (246,48,16,82,36,77,1,0,6),
    "ludie-z":               (248,80,9,57,40,68,2,0,6),
    "esyl":                  (250,104,21,78,25,24,2,0,6),
    "tim payne":             (258,52,17,63,51,57,5,0,0),
    "mono":                  (230,60,27,78,16,76,3,0,0),
    "decanita":              (216,112,15,70,12,54,3,4,4),
    "pucheta":               (244,80,16,69,18,54,4,0,2),
    "cayetano":              (238,96,22,53,4,67,4,0,2),
    "aaa":                   (264,96,10,42,5,43,7,0,2),
    "gbc":                   (252,120,17,25,0,42,1,0,0),
    "caficho":               (226,68,16,65,14,36,5,4,6),
    "monkey":                (198,132,14,18,33,19,2,4,0),
    "edgar":                 (192,56,26,47,38,36,2,4,2),
}

ITEMS = ["H","I","J","K","L","M","N","O"]

def main():
    try:
        conn2 = psycopg2.connect(DB_APP)
        cur2  = conn2.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur2.execute("SELECT id, LOWER(username) AS alias, username FROM users")
        uid_to_alias = {r["id"]: (r["alias"], r["username"]) for r in cur2.fetchall()}
        cur2.close(); conn2.close()
    except Exception as e:
        print(f"ERROR conectando a app_db: {e}"); sys.exit(1)

    try:
        conn = psycopg2.connect(DB_BECBUC)
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT pd.apostador_id,
                   COALESCE(SUM(pd.pts_resultado),0)::int       AS H,
                   COALESCE(SUM(pd.pts_marcador),0)::int        AS I,
                   COALESCE(SUM(pd.pts_amarillas),0)::int       AS J,
                   COALESCE(SUM(pd.pts_rojas),0)::int           AS K,
                   COALESCE(SUM(pd.pts_var),0)::int             AS L,
                   COALESCE(SUM(pd.pts_penales_partido),0)::int AS M,
                   COALESCE(SUM(pd.pts_minuto),0)::int          AS N,
                   COALESCE(SUM(pd.pts_penales_tanda),0)::int   AS O_tanda
            FROM puntaje_detalle pd
            JOIN fase f ON f.id = pd.fase_id
            WHERE f.torneo_id = %s
            GROUP BY pd.apostador_id
        """, (TORNEO_ID,))
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        print(f"ERROR conectando a becbuc: {e}"); sys.exit(1)

    bd = {}
    for row in rows:
        uid = row["apostador_id"]
        alias_l, username = uid_to_alias.get(uid, (f"uid{uid}", f"uid{uid}"))
        bd[alias_l] = {"username":username,
                       "H":row["H"],"I":row["I"],"J":row["J"],"K":row["K"],
                       "L":row["L"],"M":row["M"],"N":row["N"],"O":row["O_tanda"]}

    diffs=0; ok=0; missing=0
    diff_lines=[]; ok_lines=[]

    for alias_key, excel_vals in sorted(EXCEL.items()):
        bd_row = bd.get(alias_key)
        if not bd_row:
            for k,v in bd.items():
                if alias_key in k or k in alias_key:
                    bd_row=v; break

        if not bd_row:
            missing+=1
            diff_lines.append(f"  NO BD: '{alias_key}'")
            continue

        ex_h,ex_i,ex_j,ex_k,ex_l,ex_m,ex_n,ex_o1,ex_o2 = excel_vals
        emap = {"H":ex_h,"I":ex_i,"J":ex_j,"K":ex_k,"L":ex_l,"M":ex_m,"N":ex_n,"O":ex_o1+ex_o2}
        etot = sum(emap.values())
        btot = sum(bd_row[k] for k in ITEMS)

        item_diffs = [(it,emap[it],bd_row[it],bd_row[it]-emap[it]) for it in ITEMS if emap[it]!=bd_row[it]]

        if not item_diffs:
            ok+=1
            ok_lines.append(f"  OK   {bd_row['username']:<28}  Excel={etot:>4}  BD={btot:>4}")
        else:
            diffs+=1
            blk = f"\n  DIFF {bd_row['username']:<28}  Excel={etot:>4}  BD={btot:>4}  ({btot-etot:>+4})"
            for it,ev,bv,d in item_diffs:
                blk += f"\n       {it}:  Excel={ev:>4}  BD={bv:>4}  diff={d:>+4}"
            diff_lines.append(blk)

    W=72
    print("="*W)
    print("DIFERENCIAS Excel TBL CHECK vs BD (sin clasificados Q)".center(W))
    print("="*W)
    for l in diff_lines: print(l)
    print("\n"+"-"*W)
    print("SIN DIFERENCIAS".center(W))
    print("-"*W)
    for l in ok_lines: print(l)
    print("\n"+"="*W)
    print(f"  {ok} OK | {diffs} con diffs | {missing} no encontrados en BD")
    print("  diff>0 = BD tiene MAS pts | diff<0 = BD tiene MENOS")
    print("="*W)

if __name__=="__main__":
    main()
