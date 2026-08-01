# ESTADO — BECBUC (vivo)

> Se **sobrescribe** cada sesión. El histórico vive en git. Contrastar SIEMPRE con
> `git log --oneline -20` y `git status` antes de asumir nada.
> Última actualización: 2026-08-01 (sesión Cowork).

## Fase actual
Torneos de **clubes** activos: Copa Libertadores (torneo_id=1) y Copa Sudamericana
(torneo_id=14), en **octavos** (ronda16), apostables desde el **Live nuevo** (`/static/v2/`).
La Copa del Mundo (torneo_id=2) está **cerrada/finalizada**. El reglamento nuevo de clubes
(Opción C) está **implementado** en `engines/copa_clubes.py`, pero el cálculo de puntajes de
clubes todavía **no se validó end-to-end**.

## Última sesión (2026-08-01)
- **Engine `copa_clubes`** + orquestador `clubes_calculator.py` + endpoint
  `POST /bets/calcular-puntajes-clubes/{tid}` (H/I por fase, Cambios, comodín, cruce, tanda).
- **Boleta**: VAR → **Cambios** (un solo total) + **comodín** (único por torneo, se fija al
  jugarse su partido). Backend con `pred_sustituciones` / `pred_comodin`, validación de uso único.
- **Login por PIN** end-to-end (crear/entrar/olvidé; admin 1964 = solo lectura). Muestra nombre+apodo.
- **Popup MatchReplay** (replay minuto a minuto de cualquier partido terminado) + endpoint
  `GET /bets/partido-detalle/{id}`; en Grupos, tocar un partido terminado lo abre.
- **Fechas/horas de octavos** (Liberta + Sudamericana) corregidas desde **ESPN** (API-Football
  traía placeholders: día corrido + hora uniforme). 16/16 en cada torneo, en hora Paraguay.
- **Fix bracket**: `bracket-clubes` ordena por `p.id` (estructura fija) — antes ordenaba por
  fecha y movía llaves de lado (Olimpia saltaba de mitad).
- **Git**: commit `6d4546c` pusheado (force; el remoto `postgres-api` tenía historia no
  relacionada — quedó respaldado en rama local `remoto-viejo-postgres-api`).

## Pendientes
1. **Setear `competicion.codigo='copa_clubes'`** en torneos 1 y 14 (si no, el scoring cae al
   engine del Mundial). Correr `POST /calcular-puntajes-clubes/{tid}` y validar el ranking
   (cat_sustituciones, cruce, comodín, tanda).
2. **Test integral clubes** end-to-end: resultados → avance de bracket → apuestas → puntajes →
   ranking → vencedor.
3. **Recibo PDF** al guardar apuesta en el Live (v2).
4. **Portal → Competiciones**: UI de buscador de copas + subir reglamento PDF; ficha de competición;
   banner "torneo sin reglamento propio".
5. **Cuartos/semis/final de clubes**: inferir fecha/hora con ESPN cuando se definan los equipos
   (`inferir_fechas_espn.py`, cambiar `FASE_TIPO`).
6. **Seguridad**: rotar la API-key de API-Football (quedó en git) + repo privado; mover secretos a `.env`.
7. **Limpieza git**: quitar temporales (`~$..docx`, `_sweep_portable.py`, `_fix_portable_backend.py`).
8. **Bug conocido**: tiebreaker H2H en `bracket_service.py` (Art.13 FIFA) sin corregir.

## Próximo paso concreto
Setear `competicion.codigo='copa_clubes'` en Libertadores(1) y Sudamericana(14), correr
`POST /bets/calcular-puntajes-clubes/{tid}` y verificar en el Live que el ranking muestra
Cambios/cruce/comodín/tanda; luego el test integral de clubes.

## Decisiones abiertas
- Calibración final de valores del reglamento de clubes (Opción C): cruce / comodín / tanda / minuto.
- Flag formal para 3er puesto: ¿`competicion.categoria` ('clubes'|'selecciones') o
  `tiene_tercer_puesto` BOOL?
- Preguntas de reglamento Mundial que quedaron sin cerrar (mejores terceros, equipo clasifica
  24 vs 32, Paraguay KO doble, tanda 3P, mayor goleada con empate). Relevantes solo si se
  reutiliza el engine del Mundial (ya cerrado).
