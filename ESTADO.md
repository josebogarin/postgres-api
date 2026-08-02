# ESTADO — BECBUC (vivo)

> Se **sobrescribe** cada sesión. El histórico vive en git. Contrastar SIEMPRE con
> `git log --oneline -20` y `git status` antes de asumir nada.
> Última actualización: 2026-08-02.

## Fase actual
Torneos de **clubes** activos: Copa Libertadores (torneo_id=1) y Copa Sudamericana
(torneo_id=14), en **octavos** (ronda16), apostables desde el **Live nuevo** (`/static/v2/`).
Copa del Mundo (torneo_id=2) **cerrada**. El reglamento nuevo de clubes (Opción C) está
**implementado, testeado y todo compila**: engine `copa_clubes`, orquestador
`clubes_calculator`, avance de bracket + cierre de fase `clubes_bracket`. **Falta
desplegar** (uvicorn corre código viejo) y **validar contra la BD real**.

## Última sesión (2026-08-01/02)
- **Fechas/horas** de octavos (Liberta + Sudam) corregidas desde **ESPN** (16/16 c/u), en
  hora Paraguay. API-Football descartada (placeholders); CONMEBOL sin API usable.
- **Fix estructura**: `bracket-clubes` ordena por `p.id` (fijo), no por fecha (antes movía
  llaves de lado — Olimpia saltaba de mitad).
- **Avance de bracket de clubes** octavos→cuartos→semis→final (agregado + penales,
  posicional) — automático en cada sync + endpoint `POST /bets/avanzar-bracket-clubes/{tid}`.
- **Cierre de fase**: al finalizar TODOS sus partidos, la fase KO queda **bloqueada**
  (no se editan apuestas).
- **Test intensivo E2E** de clubes (autocontenido, sin BD): **TODO OK** — octavos→campeón,
  ítem por ítem, con comodín, empate+tanda, minuto pleno, cruce (×2 y bono). Ver
  `docs/INFORME_TEST_CLUBES.md`; reproducible en `tests/test_e2e_clubes.py` y
  `tests/test_copa_clubes_reglas.py` (21/21).
- **Doc reorganizada**: CLAUDE.md (estable) + ESTADO.md (vivo) + docs/decisiones.md +
  protocolo de sesión + regla anti-truncamiento. **FASE 0 de reorg** (inventario) hecha:
  `docs/INVENTARIO.md` + `docs/INVENTARIO_archivos.tsv` (nada movido).
- **Skills** creados: `becbuc-fechas-fases-live`, `espn-horarios-fixtures`, `comandos-powershell`.
- **Git**: `6d4546c` (clubes/PIN/replay/fechas/fix bracket) + `c0f9ab3` (docs reorg),
  ambos pusheados (force sobre remoto no relacionado). **HOY sin commitear**:
  `clubes_bracket.py`, guard de avance en `apostador_bets.py`, endpoint en
  `clubes_scoring.py`, `tests/*`, `docs/INFORME_TEST_CLUBES.md`, `docs/INVENTARIO*`.

## Pendientes
1. **Desplegar** hoy: `bat\rebuild_reiniciar.bat` (backend avance/cierre + front Cambios/
   comodín/replay/EnVivo-Cambios NO están live todavía).
2. **Setear `competicion.codigo='copa_clubes'`** en torneos 1 y 14; correr
   `POST /bets/calcular-puntajes-clubes/{tid}` y validar el ranking (Cambios/cruce/comodín/tanda).
3. **E2E contra BD real** con apostador de prueba **PIN 1404** (torneo real + reset, o torneo
   de prueba aislado).
4. **Reorganización del proyecto (FASE 1+)**: POSPUESTA. Backup por `git tag`/rama (no ZIP
   lento); empezar por scripts sueltos → `_cuarentena/`. Inventario en `docs/INVENTARIO.md`.
5. Recibo PDF al guardar apuesta (v2). Portal→Competiciones (buscador copas + subir
   reglamento PDF + banner "sin reglamento"). Cuartos/semis/final: fechas ESPN cuando se
   definan los equipos.
6. **Seguridad**: rotar API-key de API-Football (quedó en git) + repo privado; secretos a `.env`.
7. Bug conocido: tiebreaker H2H en `bracket_service.py` (Art.13 FIFA).

## Próximo paso concreto
Desplegar (`rebuild_reiniciar.bat`), setear `competicion.codigo='copa_clubes'` en 1 y 14,
correr `calcular-puntajes-clubes` y validar el ranking en el Live; después el E2E real con 1404.

## Decisiones abiertas
- **Cruce vía tanda**: ¿acreditar el cruce cuando el apostador predijo la llave EMPATADA y
  acertó la tanda? Hoy NO acredita (va bono al ganador limpio del par). Pendiente de definir.
- Calibración final de valores del reglamento de clubes (Opción C): cruce/comodín/tanda/minuto.
- Flag formal de 3er puesto: `competicion.categoria` ('clubes'|'selecciones') o `tiene_tercer_puesto`.
- Mejor forma de hacer la **reorganización** (backup por tag/rama; orden de las movidas).
