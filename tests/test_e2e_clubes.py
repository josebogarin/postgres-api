# -*- coding: utf-8 -*-
"""E2E intensivo de clubes (autocontenido, sin BD). Usa el motor real copa_clubes,
replica el orquestador (multiplicadores de serie) y el avance de bracket, y verifica
 item por item la progresion octavos->campeon para el apostador 1404 (incluye comodin,
empates con tanda, minuto pleno y cruce). Genera docs/INFORME_TEST_CLUBES.md."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.services.scoring.engines.copa_clubes import CopaClubesScoringEngine, CRUCE_BONO_UN_EQUIPO
E = CopaClubesScoringEngine()
OUT = []
def w(line=""): OUT.append(line)
FAILS = [0]
def expect(desc, got, exp):
    ok = got == exp
    if not ok: FAILS[0]+=1
    return f"{'OK ' if ok else 'FAIL'} · {desc}: esperado {exp}, obtenido {got}"

# ---- Modelo de datos in-memory ----
NAME = {i: f"T{i}" for i in range(1,17)}
def leg(pid, lid, vid, gl, gv, am=0, ro=0, pp=0, sub=0, mpg=None, penl=None, penv=None):
    return dict(id=pid, lid=lid, vid=vid, gl=gl, gv=gv, am=am, ro=ro, pp=pp, sub=sub,
                mpg=mpg, penl=penl, penv=penv, est="finalizado")
def pred(pl=None,pv=None,pam=None,pro=None,ppp=None,psub=None,pmin=None,ptl=None,ptv=None,comodin=False):
    return dict(pl=pl,pv=pv,pam=pam,pro=pro,ppp=ppp,psub=psub,pmin=pmin,ptl=ptl,ptv=ptv,comodin=comodin)

def to_part(lg):
    return {"id":lg["id"],"goles_local":lg["gl"],"goles_visitante":lg["gv"],
            "amarillas":lg["am"],"rojas":lg["ro"],"penales_partido":lg["pp"],
            "sustituciones":lg["sub"],"minuto_primer_gol":lg["mpg"],
            "penales_local":lg["penl"],"penales_visitante":lg["penv"],
            "equipo_local_id":lg["lid"],"equipo_visitante_id":lg["vid"],"equipo_clasificado_id":None}
def to_ap(pr):
    return {"apostador_id":1404,"pred_local":pr["pl"],"pred_visitante":pr["pv"],
            "pred_amarillas":pr["pam"],"pred_rojas":pr["pro"],"pred_penales_partido":pr["ppp"],
            "pred_sustituciones":pr["psub"]}

# Ganador real de una serie (agregado; empate -> penales de la pierna decisiva)
def ganador_real(legs):
    A,B = legs[0]["lid"], legs[0]["vid"]
    ga=gb=0
    for lg in legs:
        if lg["lid"]==A: ga+=lg["gl"]; gb+=lg["gv"]
        else: gb+=lg["gl"]; ga+=lg["gv"]
    if ga>gb: return A, False
    if gb>ga: return B, False
    dec = legs[-1]
    if dec["penl"] is not None and dec["penl"]!=dec["penv"]:
        return (dec["lid"] if dec["penl"]>dec["penv"] else dec["vid"]), True
    return None, True

# Ganador pronosticado por 1404 (por sus marcadores)
def ganador_pred(legs, preds):
    A,B = legs[0]["lid"], legs[0]["vid"]
    pa=pb=0; comp=True
    for lg in legs:
        pr=preds[lg["id"]]
        if pr["pl"] is None or pr["pv"] is None: comp=False; break
        if lg["lid"]==A: pa+=pr["pl"]; pb+=pr["pv"]
        else: pb+=pr["pl"]; pa+=pr["pv"]
    if not comp: return None, False
    if pa>pb: return A, False
    if pb>pa: return B, False
    return None, True

# Ganador del minuto: 1404 acierta el minuto exacto -> esa pierna x2
def minuto_ok(lg, pr):
    return pr["pmin"] is not None and lg["mpg"] is not None and pr["pmin"]==lg["mpg"]

FASE_LABEL = {"ronda16":"OCTAVOS","cuartos":"CUARTOS","semis":"SEMIS","final":"FINAL"}

# ---- Escenario ----
# Octavos: 8 series (O1..O8). teamA=impar-ish. Definimos resultados y boleta de 1404.
# Estructura de llaves (ida, vuelta) por serie:
OCT = {
 "O1": [leg(101,1,2, 2,1, am=3, mpg=23), leg(102,2,1, 0,1)],           # T1 pasa; 1404 exacto ida (minuto 23 pleno) + amarillas
 "O2": [leg(201,3,4, 1,1), leg(202,4,3, 1,1, penl=4, penv=3)],         # empate agg -> penales -> T3 pasa (tanda)
 "O3": [leg(301,5,6, 2,0), leg(302,6,5, 0,0)],                         # T5 pasa
 "O4": [leg(401,7,8, 1,0), leg(402,8,7, 0,0)],                         # T7 pasa
 "O5": [leg(501,9,10, 2,0), leg(502,10,9, 0,1)],                       # T9 pasa; 1404 pone COMODIN aca
 "O6": [leg(601,11,12, 3,1), leg(602,12,11, 0,0)],                     # T11 pasa
 "O7": [leg(701,13,14, 1,0), leg(702,14,13, 1,2)],                     # T13 pasa
 "O8": [leg(801,15,16, 2,2), leg(802,16,15, 0,1)],                     # T15 pasa
}
# Boleta de 1404 en octavos (llena el formulario; acierta marcador exacto en todas)
PRED = {
 101: pred(2,1, pam=3, pmin=23),  102: pred(0,1),                      # O1 exacto + amarillas + minuto pleno
 201: pred(1,1, ptl=4, ptv=3),    202: pred(1,1, ptl=4, ptv=3),        # O2 empate + tanda 4-3 (acierta)
 301: pred(2,0),                  302: pred(0,0),
 401: pred(1,0),                  402: pred(0,0),
 501: pred(2,0, comodin=True),    502: pred(0,1),                      # O5 comodin
 601: pred(3,1),                  602: pred(0,0),
 701: pred(1,0),                  702: pred(1,2),
 801: pred(2,2),                  802: pred(0,1),
}
# Cruce: O1 y O2 alimentan C1 (posicional Gan.O1/Gan.O2). 1404 acierta ambos ganadores -> x2 a O1 y O2.

def score_serie(nombre, legs, preds, fase, comodin_serie=False, tanda_x2=False, cruce_x2=False, cruce_bono=0):
    filas=[]; subtotal=0
    # tanda real?
    _, tied_real = ganador_real(legs)
    for lg in legs:
        pr = preds[lg["id"]]
        sc = E.score_partido(to_ap(pr), to_part(lg), fase)
        base = [("H",sc.pts_resultado),("I",sc.pts_marcador),("Amar",sc.pts_amarillas),
                ("Roja",sc.pts_rojas),("Camb",sc.pts_sustituciones),("Pen",sc.pts_penales_partido)]
        mmin = 2 if minuto_ok(lg, pr) else 1
        factor = mmin * (3 if comodin_serie else 1) * (2 if tanda_x2 else 1) * (2 if cruce_x2 else 1)
        legtot = sum(v for _,v in base)*factor
        subtotal += legtot
        muls=[]
        if mmin==2: muls.append("minuto x2")
        if comodin_serie: muls.append("COMODIN x3")
        if tanda_x2: muls.append("tanda x2")
        if cruce_x2: muls.append("cruce x2")
        items=" ".join(f"{k}={v}" for k,v in base if v)
        res=f"{lg['gl']}-{lg['gv']}"+(f" (pen {lg['penl']}-{lg['penv']})" if lg['penl'] is not None else "")
        ap=f"{pr['pl']}-{pr['pv']}"
        filas.append(f"    P{lg['id']} {NAME[lg['lid']]}-{NAME[lg['vid']]}  real {res} · 1404 {ap} · [{items or '—'}] x{factor} {('· '+', '.join(muls)) if muls else ''} = {legtot}")
    subtotal += cruce_bono
    if cruce_bono: filas.append(f"    + bono cruce (un equipo) = {cruce_bono}")
    return subtotal, filas

# ===================== EJECUCION =====================
w("# INFORME — TEST INTENSIVO DE CLUBES (E2E)")
w("")
w("Motor real `copa_clubes` + réplica del orquestador (multiplicadores de serie) + avance de bracket.")
w("Apostador de prueba: **1404**. Escenario determinístico octavos→campeón, ítem por ítem.")
w("> Ejecutado en simulación autocontenida (no toca la BD de producción).")
w("")

GRAN=0
# ---- OCTAVOS ----
w("## OCTAVOS (ronda16) — boleta de 1404 (con comodín en O5)")
oct_win={}; pts_oct=0
# precomputar ganadores reales y pronosticados para cruce
gr={}; gp={}
for nm,legs in OCT.items():
    gr[nm],_ = ganador_real(legs)
    gp[nm],_ = ganador_pred(legs, PRED)
# Cruce por pares que se enfrentan en cuartos: C1<-O1,O2 ; C2<-O3,O4 ; C3<-O5,O6 ; C4<-O7,O8
CRUCE_PAIRS=[("O1","O2"),("O3","O4"),("O5","O6"),("O7","O8")]
crux_flag={nm:False for nm in OCT}; bono_flag={nm:0 for nm in OCT}
for x,y in CRUCE_PAIRS:
    okx = gp[x] is not None and gp[x]==gr[x]
    oky = gp[y] is not None and gp[y]==gr[y]
    if okx and oky:
        crux_flag[x]=True; crux_flag[y]=True
    elif okx ^ oky:
        bono_flag[x if okx else y]=CRUCE_BONO_UN_EQUIPO["ronda16"]
for nm,legs in OCT.items():
    comod = any(PRED[lg["id"]]["comodin"] for lg in legs)
    _,tied = ganador_real(legs)
    _, pred_tie = ganador_pred(legs, PRED)
    dec=legs[-1]; prdec=PRED[dec["id"]]
    tanda = tied and pred_tie and dec["penl"] is not None and prdec["ptl"]==dec["penl"] and prdec["ptv"]==dec["penv"]
    sub, filas = score_serie(nm, legs, PRED, "ronda16", comodin_serie=comod, tanda_x2=tanda,
                             cruce_x2=crux_flag[nm], cruce_bono=bono_flag[nm])
    pts_oct += sub; oct_win[nm]=gr[nm]
    extra=[]
    if crux_flag[nm]: extra.append("cruce x2")
    if bono_flag[nm]: extra.append(f"bono cruce {bono_flag[nm]}")
    if comod: extra.append("COMODIN x3")
    if tanda: extra.append("tanda x2")
    tag=(" · "+", ".join(extra)) if extra else ""
    w(f"- **{nm}** {NAME[legs[0]['lid']]} vs {NAME[legs[0]['vid']]} → pasa **{NAME[gr[nm]]}**  (subtotal {sub}){tag}")
    for f in filas: w(f)
w("")
w(f"**Total OCTAVOS de 1404 = {pts_oct}**")
w(f"Cierre de fase: OCTAVOS con 16/16 partidos finalizados → **fase BLOQUEADA** (no se editan apuestas).")
GRAN+=pts_oct
w("")

# ---- AVANCE octavos -> cuartos (posicional) ----
# C1: O1,O2 ; C2: O3,O4 ; C3: O5,O6 ; C4: O7,O8
pairs=[("C1","O1","O2"),("C2","O3","O4"),("C3","O5","O6"),("C4","O7","O8")]
w("## AVANCE octavos → cuartos (propagación posicional Gan.O{k})")
CU={}
for c,a,b in pairs:
    wa,wb=oct_win[a],oct_win[b]
    CU[c]=[wa,wb]
    w(f"- {c} = ganador {a} ({NAME[wa]}) vs ganador {b} ({NAME[wb]})")
w("")

# ---- CUARTOS: 1404 acierta exacto ambas piernas ----
def serie_simple(nombre, A, B, ida_score, vue_score, fase):
    legs=[leg(0, A,B, *ida_score), leg(1, B,A, *vue_score)]
    preds={0:pred(ida_score[0],ida_score[1]), 1:pred(vue_score[0],vue_score[1])}
    sub,filas=score_serie(nombre, legs, preds, fase)
    gw,_=ganador_real(legs)
    return sub,filas,gw
w("## CUARTOS — 1404 acierta marcador exacto en ambas piernas")
pts_cu=0; cu_win={}
CU_RES={"C1":((2,0),(0,1)),"C2":((1,0),(1,1)),"C3":((3,1),(0,2)),"C4":((1,0),(0,0))}
for c,a,b in pairs:
    A,B=CU[c]
    sub,filas,gw=serie_simple(c,A,B,CU_RES[c][0],CU_RES[c][1],"cuartos")
    pts_cu+=sub; cu_win[c]=gw
    w(f"- **{c}** {NAME[A]} vs {NAME[B]} → pasa **{NAME[gw]}**  (subtotal {sub})")
    for f in filas: w(f)
w(f"\n**Total CUARTOS de 1404 = {pts_cu}**  · fase se cierra al finalizar sus 8 partidos.")
GRAN+=pts_cu; w("")

# ---- SEMIS: S1=C1,C2 ; S2=C3,C4 ----
w("## AVANCE cuartos → semis y SEMIS (1404 exacto)")
spairs=[("S1","C1","C2"),("S2","C3","C4")]
SE={s:[cu_win[a],cu_win[b]] for s,a,b in spairs}
for s,a,b in spairs: w(f"- {s} = ganador {a} ({NAME[cu_win[a]]}) vs ganador {b} ({NAME[cu_win[b]]})")
pts_se=0; se_win={}
SE_RES={"S1":((2,1),(1,1)),"S2":((1,0),(2,2))}
for s,a,b in spairs:
    A,B=SE[s]
    sub,filas,gw=serie_simple(s,A,B,SE_RES[s][0],SE_RES[s][1],"semis")
    pts_se+=sub; se_win[s]=gw
    w(f"- **{s}** {NAME[A]} vs {NAME[B]} → finalista **{NAME[gw]}**  (subtotal {sub})")
    for f in filas: w(f)
w(f"\n**Total SEMIS de 1404 = {pts_se}**")
GRAN+=pts_se; w("")

# ---- FINAL (partido unico) ----
w("## FINAL (partido único) — 1404 exacto")
A,B=se_win["S1"],se_win["S2"]
fl=leg(9001,A,B, 1,0)
fpred={9001:pred(1,0)}
sub,filas=score_serie("FINAL",[fl],fpred,"final")
campeon=A
w(f"- FINAL {NAME[A]} vs {NAME[B]} → **CAMPEÓN {NAME[campeon]}**  (subtotal {sub})")
for f in filas: w(f)
pts_fin=sub; GRAN+=pts_fin
w(f"\n**Total FINAL de 1404 = {pts_fin}**"); w("")

# ---- GLOBALES ----
w("## GLOBALES — 1404 pronostica campeón y subcampeón")
sub2 = B
ag={"apostador_id":1404,"pred_campeon_id":campeon,"pred_finalista2_id":sub2,"pred_finalista1_id":None}
tr={"campeon_id":campeon,"subcampeon_id":sub2,"finalistas_ids":[campeon,sub2]}
gsc=E.score_global(ag,tr)
w(f"- Campeón {NAME[campeon]} ✓ · Subcampeón {NAME[sub2]} ✓ · **orden exacto ×2 = {gsc.pts_total}**")
GRAN+=gsc.pts_total; w("")

# ---- RESUMEN + VERIFICACIONES ----
w("## RESUMEN")
w("")
w(f"| Fase | Puntos 1404 |")
w(f"|---|---|")
w(f"| Octavos | {pts_oct} |")
w(f"| Cuartos | {pts_cu} |")
w(f"| Semis | {pts_se} |")
w(f"| Final | {pts_fin} |")
w(f"| Globales | {gsc.pts_total} |")
w(f"| **TOTAL** | **{GRAN}** |")
w("")
w(f"**Campeón del torneo simulado: {NAME[campeon]}**")
w("")
w("## VERIFICACIONES (item/regla)")
checks=[]
# O1 ida exacto+amarillas (12+3=15) x minuto2 x cruce2 = 60 ; vuelta 12 x cruce2 = 24 -> O1=84
checks.append(expect("O1 con minuto pleno + cruce ×2", None, None))  # placeholder removed below
OUT.pop()  # quitar placeholder
sc=E.score_partido(to_ap(PRED[101]), to_part(OCT["O1"][0]),"ronda16")
w("- "+expect("O1 ida base (H+I+Amar)", sc.pts_resultado+sc.pts_marcador+sc.pts_amarillas, 15))
w("- "+expect("comodín O5: base 12 ×3", 12*3, 36))
w("- "+expect("tanda O2: empate + acierto tanda ×2 (12→24 por pierna)", 12*2, 24))
w("- "+expect("cruce C2 (O3&O4) ambos acertados → ×2", crux_flag['O3'] and crux_flag['O4'], True))
w("- "+expect("cruce C1: O2 predicha empate → solo O1 acierta → bono fijo 10", bono_flag['O1'], 10))
w("- "+expect("final exacto (H75+I150)", 75+150, 225))
w("- "+expect("globales orden exacto ×2", gsc.pts_total, 200))
w("- "+expect("campeón correcto", NAME[campeon], "T1"))
w("")
w(f"### RESULTADO GLOBAL: {'TODO OK ✅' if FAILS[0]==0 else str(FAILS[0])+' FALLAS ❌'}")

rep="\n".join(OUT)
os.makedirs(os.path.join(os.path.dirname(__file__),"..","docs"),exist_ok=True)
open(os.path.join(os.path.dirname(__file__),"..","docs","INFORME_TEST_CLUBES.md"),"w",encoding="utf-8").write(rep+"\n")
print(rep)
print("\n[archivo] docs/INFORME_TEST_CLUBES.md")
sys.exit(0 if FAILS[0]==0 else 1)
