# Test de reglas del engine copa_clubes (Nivel 1, sin BD). Correr:  python tests/test_copa_clubes_reglas.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.services.scoring.engines.copa_clubes import CopaClubesScoringEngine, CRUCE_BONO_UN_EQUIPO
eng = CopaClubesScoringEngine()
def part(pid=1,gl=0,gv=0,am=0,ro=0,pp=0,sub=0,lid=10,vid=20):
    return {"id":pid,"goles_local":gl,"goles_visitante":gv,"amarillas":am,"rojas":ro,
            "penales_partido":pp,"sustituciones":sub,"minuto_primer_gol":None,
            "penales_local":None,"penales_visitante":None,"equipo_local_id":lid,
            "equipo_visitante_id":vid,"equipo_clasificado_id":None}
def ap(pl=None,pv=None,am=None,ro=None,pp=None,sub=None):
    return {"apostador_id":1,"pred_local":pl,"pred_visitante":pv,"pred_amarillas":am,
            "pred_rojas":ro,"pred_penales_partido":pp,"pred_sustituciones":sub}
def cols(s): return (s.pts_resultado,s.pts_marcador,s.pts_amarillas,s.pts_rojas,s.pts_sustituciones,s.pts_penales_partido)
def total_serie(s,mmin=1,comodin=1,tanda=1,crucex2=1,bono=0):
    f=mmin*comodin*tanda*crucex2; h,i,j,k,sub,m=cols(s); return (h+i+j+k+sub+m)*f+bono
R=[]
def chk(d,g,e):
    ok=g==e; R.append(ok); print(f"  [{'OK ' if ok else 'FAIL'}] {d:52s} esp={e:<5} got={g}")
for fase,(H,I) in [("ronda16",(4,8)),("cuartos",(12,24)),("semis",(30,60)),("final",(75,150))]:
    s=eng.score_partido(ap(2,1),part(gl=2,gv=1),fase); chk(f"{fase} exacto 2-1 H+I",s.pts_resultado+s.pts_marcador,H+I)
chk("octavos solo resultado",total_serie(eng.score_partido(ap(1,0),part(gl=2,gv=0),"ronda16")),4)
chk("octavos empate exacto",total_serie(eng.score_partido(ap(1,1),part(gl=1,gv=1),"ronda16")),12)
chk("octavos fallo total",total_serie(eng.score_partido(ap(0,2),part(gl=2,gv=0),"ronda16")),0)
chk("eventos exacto y >=1 (9)",(lambda s:s.pts_amarillas+s.pts_rojas+s.pts_penales_partido)(eng.score_partido(ap(1,0,am=4,ro=1,pp=1),part(gl=1,gv=0,am=4,ro=1,pp=1),"ronda16")),9)
chk("evento 0-0 no suma",eng.score_partido(ap(1,0,am=0),part(gl=1,gv=0,am=0),"ronda16").pts_amarillas,0)
chk("cambios exacto>=1",eng.score_partido(ap(1,0,sub=6),part(gl=1,gv=0,sub=6),"cuartos").pts_sustituciones,5)
sf=eng.score_partido(ap(1,0),part(gl=1,gv=0),"final")
chk("final exacto",total_serie(sf),225); chk("final + minuto x2",total_serie(sf,mmin=2),450)
chk("final + comodin x3",total_serie(sf,comodin=3),675); chk("final + minuto+comodin",total_serie(sf,mmin=2,comodin=3),1350)
chk("semis empate + tanda x2",total_serie(eng.score_partido(ap(1,1),part(gl=1,gv=1),"semis"),tanda=2),180)
so=eng.score_partido(ap(2,1),part(gl=2,gv=1),"ronda16")
chk("cruce un equipo (+10)",total_serie(so,bono=CRUCE_BONO_UN_EQUIPO["ronda16"]),22)
chk("cruce ambos (x2)",total_serie(so,crucex2=2),24)
def glob(pc,ps,c,s):
    return eng.score_global({"apostador_id":1,"pred_campeon_id":pc,"pred_finalista2_id":ps,"pred_finalista1_id":None},{"campeon_id":c,"subcampeon_id":s,"finalistas_ids":[c,s]}).pts_total
chk("global solo campeon",glob(7,99,7,8),50); chk("global solo sub",glob(1,8,7,8),50)
chk("global orden x2",glob(7,8,7,8),200); chk("global ninguno",glob(1,2,7,8),0)
print(f"\n==== {sum(R)}/{len(R)} OK ====")
sys.exit(0 if all(R) else 1)
