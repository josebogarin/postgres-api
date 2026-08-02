# INFORME — TEST INTENSIVO DE CLUBES (E2E)

Motor real `copa_clubes` + réplica del orquestador (multiplicadores de serie) + avance de bracket.
Apostador de prueba: **1404**. Escenario determinístico octavos→campeón, ítem por ítem.
> Ejecutado en simulación autocontenida (no toca la BD de producción).

## OCTAVOS (ronda16) — boleta de 1404 (con comodín en O5)
- **O1** T1 vs T2 → pasa **T1**  (subtotal 52) · bono cruce 10
    P101 T1-T2  real 2-1 · 1404 2-1 · [H=4 I=8 Amar=3] x2 · minuto x2 = 30
    P102 T2-T1  real 0-1 · 1404 0-1 · [H=4 I=8] x1  = 12
    + bono cruce (un equipo) = 10
- **O2** T3 vs T4 → pasa **T4**  (subtotal 48) · tanda x2
    P201 T3-T4  real 1-1 · 1404 1-1 · [H=4 I=8] x2 · tanda x2 = 24
    P202 T4-T3  real 1-1 (pen 4-3) · 1404 1-1 · [H=4 I=8] x2 · tanda x2 = 24
- **O3** T5 vs T6 → pasa **T5**  (subtotal 48) · cruce x2
    P301 T5-T6  real 2-0 · 1404 2-0 · [H=4 I=8] x2 · cruce x2 = 24
    P302 T6-T5  real 0-0 · 1404 0-0 · [H=4 I=8] x2 · cruce x2 = 24
- **O4** T7 vs T8 → pasa **T7**  (subtotal 48) · cruce x2
    P401 T7-T8  real 1-0 · 1404 1-0 · [H=4 I=8] x2 · cruce x2 = 24
    P402 T8-T7  real 0-0 · 1404 0-0 · [H=4 I=8] x2 · cruce x2 = 24
- **O5** T9 vs T10 → pasa **T9**  (subtotal 144) · cruce x2, COMODIN x3
    P501 T9-T10  real 2-0 · 1404 2-0 · [H=4 I=8] x6 · COMODIN x3, cruce x2 = 72
    P502 T10-T9  real 0-1 · 1404 0-1 · [H=4 I=8] x6 · COMODIN x3, cruce x2 = 72
- **O6** T11 vs T12 → pasa **T11**  (subtotal 48) · cruce x2
    P601 T11-T12  real 3-1 · 1404 3-1 · [H=4 I=8] x2 · cruce x2 = 24
    P602 T12-T11  real 0-0 · 1404 0-0 · [H=4 I=8] x2 · cruce x2 = 24
- **O7** T13 vs T14 → pasa **T13**  (subtotal 48) · cruce x2
    P701 T13-T14  real 1-0 · 1404 1-0 · [H=4 I=8] x2 · cruce x2 = 24
    P702 T14-T13  real 1-2 · 1404 1-2 · [H=4 I=8] x2 · cruce x2 = 24
- **O8** T15 vs T16 → pasa **T15**  (subtotal 48) · cruce x2
    P801 T15-T16  real 2-2 · 1404 2-2 · [H=4 I=8] x2 · cruce x2 = 24
    P802 T16-T15  real 0-1 · 1404 0-1 · [H=4 I=8] x2 · cruce x2 = 24

**Total OCTAVOS de 1404 = 484**
Cierre de fase: OCTAVOS con 16/16 partidos finalizados → **fase BLOQUEADA** (no se editan apuestas).

## AVANCE octavos → cuartos (propagación posicional Gan.O{k})
- C1 = ganador O1 (T1) vs ganador O2 (T4)
- C2 = ganador O3 (T5) vs ganador O4 (T7)
- C3 = ganador O5 (T9) vs ganador O6 (T11)
- C4 = ganador O7 (T13) vs ganador O8 (T15)

## CUARTOS — 1404 acierta marcador exacto en ambas piernas
- **C1** T1 vs T4 → pasa **T1**  (subtotal 72)
    P0 T1-T4  real 2-0 · 1404 2-0 · [H=12 I=24] x1  = 36
    P1 T4-T1  real 0-1 · 1404 0-1 · [H=12 I=24] x1  = 36
- **C2** T5 vs T7 → pasa **T5**  (subtotal 72)
    P0 T5-T7  real 1-0 · 1404 1-0 · [H=12 I=24] x1  = 36
    P1 T7-T5  real 1-1 · 1404 1-1 · [H=12 I=24] x1  = 36
- **C3** T9 vs T11 → pasa **T9**  (subtotal 72)
    P0 T9-T11  real 3-1 · 1404 3-1 · [H=12 I=24] x1  = 36
    P1 T11-T9  real 0-2 · 1404 0-2 · [H=12 I=24] x1  = 36
- **C4** T13 vs T15 → pasa **T13**  (subtotal 72)
    P0 T13-T15  real 1-0 · 1404 1-0 · [H=12 I=24] x1  = 36
    P1 T15-T13  real 0-0 · 1404 0-0 · [H=12 I=24] x1  = 36

**Total CUARTOS de 1404 = 288**  · fase se cierra al finalizar sus 8 partidos.

## AVANCE cuartos → semis y SEMIS (1404 exacto)
- S1 = ganador C1 (T1) vs ganador C2 (T5)
- S2 = ganador C3 (T9) vs ganador C4 (T13)
- **S1** T1 vs T5 → finalista **T1**  (subtotal 180)
    P0 T1-T5  real 2-1 · 1404 2-1 · [H=30 I=60] x1  = 90
    P1 T5-T1  real 1-1 · 1404 1-1 · [H=30 I=60] x1  = 90
- **S2** T9 vs T13 → finalista **T9**  (subtotal 180)
    P0 T9-T13  real 1-0 · 1404 1-0 · [H=30 I=60] x1  = 90
    P1 T13-T9  real 2-2 · 1404 2-2 · [H=30 I=60] x1  = 90

**Total SEMIS de 1404 = 360**

## FINAL (partido único) — 1404 exacto
- FINAL T1 vs T9 → **CAMPEÓN T1**  (subtotal 225)
    P9001 T1-T9  real 1-0 · 1404 1-0 · [H=75 I=150] x1  = 225

**Total FINAL de 1404 = 225**

## GLOBALES — 1404 pronostica campeón y subcampeón
- Campeón T1 ✓ · Subcampeón T9 ✓ · **orden exacto ×2 = 200**

## RESUMEN

| Fase | Puntos 1404 |
|---|---|
| Octavos | 484 |
| Cuartos | 288 |
| Semis | 360 |
| Final | 225 |
| Globales | 200 |
| **TOTAL** | **1557** |

**Campeón del torneo simulado: T1**

- OK  · O1 ida base (H+I+Amar): esperado 15, obtenido 15
- OK  · comodín O5: base 12 ×3: esperado 36, obtenido 36
- OK  · tanda O2: empate + acierto tanda ×2 (12→24 por pierna): esperado 24, obtenido 24
- OK  · cruce C2 (O3&O4) ambos acertados → ×2: esperado True, obtenido True
- OK  · cruce C1: O2 predicha empate → solo O1 acierta → bono fijo 10: esperado 10, obtenido 10
- OK  · final exacto (H75+I150): esperado 225, obtenido 225
- OK  · globales orden exacto ×2: esperado 200, obtenido 200
- OK  · campeón correcto: esperado T1, obtenido T1

### RESULTADO GLOBAL: TODO OK ✅
