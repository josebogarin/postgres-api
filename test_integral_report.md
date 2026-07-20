
======================================================================
BECBUC — TEST INTEGRAL  2026-06-11 19:57:36
======================================================================

[1/8] Login admin...
  ✓ Token obtenido
══════════════════════════════════════════════════════════════════════
# TEST INTEGRAL BECBUC — Copa del Mundo
Fecha: 2026-06-11 19:57:39
══════════════════════════════════════════════════════════════════════

## 1. Torneo: ID=2

  Nombre   : Copa Mundial FIFA 2026
  Fases    : 19

[2/8] Reseteando torneo...
  Borrando apuestas y puntajes...
  Reseteando resultados de partidos...
  ✓ Torneo reseteado

[3/8] Simulando resultados de partidos...

## 2. Simulación de resultados

  Fases encontradas: 19
  ✓ [     grupo] Grupo L                        → 6 partidos simulados
  ✓ [     grupo] Grupo F                        → 6 partidos simulados
  ✓ [     grupo] Grupo G                        → 6 partidos simulados
  ✓ [     grupo] Grupo H                        → 6 partidos simulados
  ✓ [     grupo] Grupo I                        → 6 partidos simulados
  ✓ [     grupo] Grupo J                        → 6 partidos simulados
  ✓ [     grupo] Grupo K                        → 6 partidos simulados
  ✓ [     grupo] Grupo A                        → 6 partidos simulados
  ✓ [     grupo] Grupo B                        → 6 partidos simulados
  ✓ [     grupo] Grupo C                        → 6 partidos simulados
  ✓ [     grupo] Grupo D                        → 6 partidos simulados
  ✓ [     grupo] Grupo E                        → 6 partidos simulados
  ✓ [   ronda32] Ronda de 32                    → 16 partidos simulados
  ✓ [   ronda16] Octavos de Final               → 8 partidos simulados
  ✓ [   cuartos] Cuartos de Final               → 4 partidos simulados
  ✓ [     semis] Semifinales                    → 2 partidos simulados
  ✓ [tercer_puesto] Tercer Puesto                  → 1 partidos simulados
  ✓ [     final] Final                          → 1 partidos simulados

  ✓ Total partidos simulados: 104

[4/8] Verificando partidos finalizados...
  ✓ 104 partidos finalizados con goles
     grupo       : 72 partidos
     ronda32     : 16 partidos
     ronda16     : 8 partidos
     cuartos     : 4 partidos
     semis       : 2 partidos
     tercer_puesto: 1 partidos
     final       : 1 partidos

[5/8] Obteniendo apostadores...
  ✓ 26 apostadores: ['aaa', 'alejandrolegui', 'alevo', 'alfaorion 99', 'andres', 'apostador1', 'apostador2', '@bs', 'cherem', 'decanita', 'edgar', 'eliasmajul', 'fscc', 'gbc', 'gh1s', 'grillito', 'jose', 'kikao', 'ludie-z', 'moño', 'moro', 'patito', 'pato', 'pinguero', 'sajano freddy', 'tony']

[6/9] Cargando apuestas de partido...

## 3. Estrategia de apuestas

  apostador1 → marcador exacto siempre  → esperado: máx puntaje (H+I)
  apostador2 → resultado OK, marcador+1 → esperado: solo H
  andres     → siempre equivocado        → esperado: 0 pts
  jose       → random seed=42            → esperado: mezcla


  Insertando apuestas: 26 apostadores × 104 partidos...
  ✓ 2704 apuestas insertadas en BD

[7/9] Simulando apuestas globales A-G...

## 3b. Simulando apuestas globales A-G

  aaa            → camp=73  fin1=97/fin2=84  peor=50  goleada=4-2  py_eta=grupo py_goles=4
  alejandrolegui → camp=53  fin1=62/fin2=86  peor=80  goleada=3-1  py_eta=ronda16 py_goles=8
  alevo          → camp=92  fin1=85/fin2=77  peor=95  goleada=6-0  py_eta=semis py_goles=5
  alfaorion 99   → camp=67  fin1=54/fin2=74  peor=80  goleada=3-0  py_eta=cuartos py_goles=7
  andres         → camp=52  fin1=57/fin2=52  peor=51  goleada=6-3  py_eta=final py_goles=7
  apostador1     → camp=69  fin1=69/fin2=76  peor=91  goleada=3-0  py_eta=grupo py_goles=2
  apostador2     → camp=69  fin1=69/fin2=57  peor=93  goleada=4-0  py_eta=grupo py_goles=0
  @bs            → camp=85  fin1=75/fin2=89  peor=94  goleada=5-0  py_eta=octavos py_goles=3
  cherem         → camp=61  fin1=65/fin2=54  peor=64  goleada=3-3  py_eta=grupo py_goles=10
  decanita       → camp=86  fin1=75/fin2=51  peor=89  goleada=6-1  py_eta=octavos py_goles=8
  edgar          → camp=90  fin1=68/fin2=75  peor=90  goleada=2-2  py_eta=cuartos py_goles=1
  eliasmajul     → camp=63  fin1=76/fin2=77  peor=69  goleada=6-2  py_eta=ronda16 py_goles=3
  fscc           → camp=95  fin1=52/fin2=57  peor=91  goleada=2-1  py_eta=octavos py_goles=3
  gbc            → camp=87  fin1=51/fin2=79  peor=74  goleada=3-2  py_eta=ronda16 py_goles=2
  gh1s           → camp=78  fin1=57/fin2=51  peor=87  goleada=3-2  py_eta=octavos py_goles=9
  grillito       → camp=94  fin1=80/fin2=64  peor=54  goleada=3-2  py_eta=ronda16 py_goles=3
  jose           → camp=74  fin1=63/fin2=58  peor=65  goleada=4-0  py_eta=ronda16 py_goles=0
  kikao          → camp=60  fin1=92/fin2=71  peor=79  goleada=5-1  py_eta=octavos py_goles=5
  ludie-z        → camp=88  fin1=60/fin2=74  peor=82  goleada=2-2  py_eta=ronda16 py_goles=6
  moño           → camp=86  fin1=81/fin2=60  peor=83  goleada=4-3  py_eta=ronda16 py_goles=8
  moro           → camp=66  fin1=57/fin2=58  peor=87  goleada=5-2  py_eta=octavos py_goles=9
  patito         → camp=81  fin1=78/fin2=97  peor=91  goleada=4-2  py_eta=octavos py_goles=9
  pato           → camp=86  fin1=79/fin2=96  peor=51  goleada=2-3  py_eta=ronda16 py_goles=5
  pinguero       → camp=53  fin1=68/fin2=60  peor=51  goleada=5-3  py_eta=cuartos py_goles=2
  sajano freddy  → camp=70  fin1=62/fin2=89  peor=53  goleada=3-0  py_eta=octavos py_goles=7
  tony           → camp=89  fin1=85/fin2=63  peor=78  goleada=6-2  py_eta=semis py_goles=9
  ✓ 26 apuestas globales insertadas

[8/9] Calculando puntajes...

## 4. Cálculo de puntajes

  engine   : copa_mundo_2026
  plenos   : 139
  aciertos : 586
  fallos   : 1979
  total    : 2704 apuestas procesadas

## 5. Ranking tras simulación

  Pos  Apostador       Total  Partidos  Globales  Plenos  Aciertos
  ───  ────────────── ────── ───────── ───────── ─────── ─────────
    1  apostador1        972       900        72      72         0
    2  apostador2        346       300        46       0        72
    3  pinguero          190       184         6       5        27
    4  alfaorion 99      180       160        20       3        28
    5  gh1s              174       164        10       3        30
    6  grillito          174       164        10       5        25
    7  gbc               164       148        16       4        24
    8  pato              164       164         0       5        23
    9  alevo             162       152        10       4        25
   10  sajano freddy     156       136        20       2        26
   11  eliasmajul        150       140        10       4        22
   12  fscc              148       148         0       5        20
   13  tony              144       144         0       5        21
   14  aaa               134       128         6       2        25
   15  alejandrolegui    134       124        10       4        18
   16  cherem            128       112        16       1        25
   17  moro              120       120         0       4        18
   18  jose              118       108        10       1        23
   19  ludie-z           116       116         0       2        23
   20  moño              112       112         0       2        22
   21  kikao             104       104         0       2        19
   22  @bs                98        88        10       1        18
   23  edgar              88        88         0       1        18
   24  patito             84        84         0       1        18
   25  decanita           76        76         0       1        16
   26  andres              0         0         0       0         0

## 6. Verificación scoring engine vs reglamento BEC BUC 2026

  ### Puntaje total por apostador (suma de puntaje_detalle)

    aaa           :      0 pts  (0 partidos en muestra)
    alejandrolegui:      0 pts  (0 partidos en muestra)
    alevo         :      0 pts  (0 partidos en muestra)
    alfaorion 99  :      0 pts  (0 partidos en muestra)
    andres        :      0 pts  (0 partidos en muestra)
    apostador1    :    900 pts  (104 partidos en muestra)
    apostador2    :    300 pts  (96 partidos en muestra)
    @bs           :      0 pts  (0 partidos en muestra)
    cherem        :      0 pts  (0 partidos en muestra)
    decanita      :      0 pts  (0 partidos en muestra)
    edgar         :      0 pts  (0 partidos en muestra)
    eliasmajul    :      0 pts  (0 partidos en muestra)
    fscc          :      0 pts  (0 partidos en muestra)
    gbc           :      0 pts  (0 partidos en muestra)
    gh1s          :      0 pts  (0 partidos en muestra)
    grillito      :      0 pts  (0 partidos en muestra)
    jose          :      0 pts  (0 partidos en muestra)
    kikao         :      0 pts  (0 partidos en muestra)
    ludie-z       :      0 pts  (0 partidos en muestra)
    moño          :      0 pts  (0 partidos en muestra)
    moro          :      0 pts  (0 partidos en muestra)
    patito        :      0 pts  (0 partidos en muestra)
    pato          :      0 pts  (0 partidos en muestra)
    pinguero      :      0 pts  (0 partidos en muestra)
    sajano freddy :      0 pts  (0 partidos en muestra)
    tony          :      0 pts  (0 partidos en muestra)

  ### Detalle apostador1 (primeros 8 partidos)

    PID     Pred     Real    FaseTipo     H     I     J     L  OK?
    143  0-0      0-0           grupo     4     8     0     0  ✓
    144  0-1      0-1           grupo     4     8     0     0  ✓
    145  1-2      1-2           grupo     4     8     0     0  ✓
    146  2-0      2-0           grupo     8    16     0     0  ⚠️(exp 4)
    147  1-3      1-3           grupo     4     8     0     0  ✓
    148  3-0      3-0           grupo     4     8     0     0  ✓
    149  0-0      0-0           grupo     4     8     0     0  ✓
    150  2-1      2-1           grupo     4     8     0     0  ✓

  ### Detalle andres (debe ser 0 en H e I)


[9/9] Exportando Excel completo...
══════════════════════════════════════════════════════════════════════

## TABLA DE PUNTAJES OFICIAL — Reglamento BEC BUC 2026

  Concepto                    GR   16   8v   4t   Se   3P   Fi
  ------------------------- ---- ---- ---- ---- ---- ---- ----
  H - Resultado                4    6    8   10   12   14   20
  I - Marcador exacto          8   12   16   20   24   28   40
  J - Amarillas                1    1    1    1    1    1    1
  K - Rojas                    1    1    1    1    1    1    1
  L - VAR                      1    1    1    1    1    1    1
  N - Minuto gol               1    1    1    1    1    1    1
  O - Penales tanda            —    2    2    2    2    2    2

  Paraguay: DOBLE PUNTAJE en todos los conceptos de partido

  Globales A-G: max 112 pts (Campeón 20, Finalistas 20, Goleador 20,
                             Peor equipo 20, Mayor goleada 20, Py 6+6)
══════════════════════════════════════════════════════════════════════

## CONCLUSIÓN

  Apostadores : 26
  Partidos    : 104
  Líder       : apostador1 — 972 pts
  Último      : andres — 0 pts
  Promedio    : 170.6 pts

  ✓ Reporte: C:\proyecto FAST API\test_integral_report.md
  ✓ Excel  : C:\proyecto FAST API\BECBUC_verificacion.xlsx

  Hojas del Excel:
    🏆 Ranking    — clasificación final con desglose
    📋 Resultados — fichas de resultado por fase
    🎯 Apuestas   — pronósticos × partido (verde=exacto, amarillo=resultado, rojo=fallo)
    📊 Puntajes   — detalle H,I,J,K,L,O × jugador × partido
    🌐 Globales   — apuestas bonus A-G vs resultado real