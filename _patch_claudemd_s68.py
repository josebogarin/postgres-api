import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""Registrar sesion 68 (2026-07-15) en CLAUDE.md."""
import shutil, os
from datetime import datetime
B="/sessions/stoic-busy-euler/mnt/proyecto FAST API"
if not os.path.exists(B): B=_BASE
MD=B+"/CLAUDE.md"; BKP=B+"/_backups"; os.makedirs(BKP,exist_ok=True)

ENTRY = r"""2026-07-15 - Sesion Cowork (sesion 68) - CIERRE CUARTOS + SEMIS/BRACKET + EDITOR APUESTAS LIVE-PLAYOFFS + EXPORT:

  REGLA OPERATIVA CONFIRMADA (app_db compartida):
    app_db es la BD central de gestion de usuarios que comparten TODOS los proyectos
    listados en la tabla `sistema` (BECBUC, Plataforma/FastAPI Release 2 en C:\proyectos\plataforma,
    Energia en C:\Proyectos\Energia, etc.). Cualquier cambio de esquema en app_db.sistema por
    otro proyecto puede romper el arranque de BECBUC (ORM espera columnas legacy -> fix_sistema_columns.py).
    REGLA: avisar y alertar de riesgos ANTES de tocar cualquier cosa en app_db.

  1) CIERRE DE CUARTOS (cerrar_cuartos.py + run_cerrar_cuartos.bat):
     Verifica P097-P100: finalizados + items API cargados (amarillas/rojas/VAR/pen.juego/minuto;
     tanda solo si empate). Guardas de aborto si algo incompleto. Luego POST /calcular-puntajes/2
     (cuartos aun abierta) y bloquea fase Cuartos (id=142). NO abre Semis.
     Resultado: P097 France 2-0 Morocco, P098 Spain 2-1 Belgium, P099 Norway 1-2 England,
     P100 Argentina 3-1 Switzerland. plenos=39 aciertos=85 fallos=52, [cuartos] total=3153, apuestas=176.

  2) SEMIS + AVANCE DE BRACKET (sync_semis.py + run_sync_semis.bat):
     OPCION A (SIEMPRE, default del usuario): POST /sync-resultados/2?force=true ->
     auto-mapea api_fixture_id + trae resultados + avanza bracket. NO bloquea fases,
     no genera puntajes de semis (sin apuestas cargadas).
     Resultado: P101 France 0-2 Spain, P102 England 1-2 Argentina (finalizados).
     Bracket: Final (P104) = Spain vs Argentina | 3er puesto (P103) = France vs England.
     Fechas: 19-jul (P103 00:00 UTC, P104 22:00 UTC).
     Diagnostico: estado_semis_bracket.py / run_estado_semis.bat (solo lectura).
     REGLA: una fase no se cierra ni se puntua sin las apuestas cargadas.

  3) EDITOR DE APUESTAS EN "MI PRONO" (becbuc-live-playoffs.html + apostador_bets.py):
     renderMiProno delega a renderMiPronoEditor (el viejo cuerpo quedo como _renderMiProno_OLD).
     Editor con inputs por item, formato/iconos del tab Apuestas: marcador (pred_local/visitante),
     J amarillas, K rojas, L VAR, M pen.juego, N minuto, seccion "Definicion por penales"
     (Ol/Ov tanda) y P clasifica (select de los 2 equipos). Precarga desde _userPreds.
     Endpoint NUEVO: POST /api/v1/bets/live-guardar-apuestas/{torneo_id}
       body {apostador_id, pin, apuestas:[{numero_fifa, pred_*}]}. Sin auth de apostador
       (la pagina usa token admin). Guarda solo partidos 'programado' con fase NO bloqueada.
       NO calcula puntajes ni cierra fases. Upsert incluye pred_equipo_clasifica + nombre_apostador=username.
     Bracket -> Mi Prono: selectMatch() ahora hace setTab('miprono') + scroll al partido (_scrollToMpCard).

  4) PIN = PRIMER NOMBRE (no username):
     El endpoint lee users.nombre (app_db) y compara el PRIMER TOKEN en MAYUSCULAS.
     Ej: username=cherem, nombre='ANDRES BOGARIN' -> PIN valido = ANDRES. Fallback a username si nombre vacio.
     Verificado (test): PIN correcto acepta, username ya no valida.

  5) MI PRONO SOLO PENDIENTES: se quito la seccion de cotejo (finalizados). Solo partidos no jugados.

  6) RECIBO PDF (auto al guardar con exito): _mpMostrarRecibo() arma una tarjeta blanca imprimible
     con boton "Imprimir / Guardar PDF" (window.print -> en movil "Guardar como PDF"). Lista TODOS
     los partidos pendientes con sus items (desde _userPreds, sin terminados) + encabezado con
     Nombre y apellido (users.nombre, devuelto por el endpoint como "nombre") + Usuario (alias).

  7) BLOQUEO DE EDICION 4H ANTES DEL PARTIDO:
     Backend: live-guardar-apuestas rechaza si now >= fecha_partido - 4h ("Edicion cerrada...").
     Frontend: _mpLocked(m) (fecha del partido, UTC vs hora del dispositivo). Tarjeta bloqueada
     con inputs disabled + badge; si todas cerradas se oculta Guardar. Final/3er puesto (19-jul)
     siguen editables hasta 4h antes de cada uno.

  8) EXPORT PRONOSTICOS + COMPLETADOS POR FASE (Monitoreo):
     Endpoints NUEVOS:
       GET /api/v1/bets/exportar-pronosticos/{torneo_id} (admin): Excel, 1 fila por apostador x partido
         de TODAS las fases abiertas. Cols: No Partido, Fase, Usuario, Nombre, Local, Visitante,
         Resultado real, Pron.Local, Pron.Visit, Amarillas(J), Rojas(K), VAR(L), Pen.juego(M),
         Min.1er gol(N), Tanda Local(Ol), Tanda Visit(Ov), Clasifica(P). Orden: apostador -> fase -> nro partido.
         Solo rol 'apostador' activo. Filename becbuc_pronosticos_fases_abiertas_{ts}.xlsx.
       GET /api/v1/bets/pronosticos-completados/{torneo_id} (admin): por fase abierta cuantos
         apostadores completaron TODAS sus apuestas (n>=total_partidos) sobre total_apostadores.
     UI Portal (Monitoreo): card "Apuestas completas por fase abierta" (X/44 por fase) + boton
       "Exportar pronosticos" (loadCompletadosFase / exportarPronosticos).
     UI Movil (admin): seccion "Pronosticos (fases abiertas)" + boton (exportarPronosticosM /
       _loadCompletadosFaseM). REGLA UI OBLIGATORIA cumplida (portal + movil).
     Verificado (test PASS): completados Semis 0/44, 3er puesto 1/44, Final 1/44; Excel 5.7KB ok.

  ARCHIVOS MODIFICADOS:
    backend/app/api/v1/endpoints/apostador_bets.py (endpoints live-guardar-apuestas,
      exportar-pronosticos, pronosticos-completados)
    backend/static/becbuc-live-playoffs.html (editor Mi Prono, PIN, recibo, lock 4h, nav bracket)
    backend/static/BECBUC-portal.html (Monitoreo: card completados + export)
    backend/static/BECBUC-movil.html (admin: seccion completados + export)

  ARCHIVOS CREADOS (raiz): cerrar_cuartos.py, estado_semis_bracket.py, sync_semis.py, get_ngrok.py
    y sus run_*.bat; tests test_live_guardar.py / test_export_pronos.py; parches _patch_*.py
    (aplicados con backup en _backups/, verificados con node --check + ast). CREDENCIALES psycopg2
    externas: host=localhost port=5432 user=app_user password=superpassword.

  WHATSAPP a usuarios (para probar apuestas): incluye link ngrok del dia
    https://cupped-oink-thousand.ngrok-free.dev/static/becbuc-live-playoffs.html (CAMBIA al reiniciar;
    obtener con run_get_ngrok.bat), elegir USUARIO en el login, pestana Mi Prono (solo pendientes) o
    tocar el partido en el Bracket, cargar items, Guardar -> PIN = primer nombre -> recibo PDF.

  ESTADO TORNEO POST-SESION:
    Grupos + R32 + Octavos + Cuartos: finalizados y BLOQUEADOS.
    Semis: P101/P102 finalizados, fase 'semis' ABIERTA (apuestas de semis NO cargadas).
    Bracket propagado: Final (P104) Spain vs Argentina, 3er puesto (P103) France vs England (19-jul).
    PENDIENTE: cargar apuestas de Semis (y luego Final/3er puesto) para poder cerrar/puntuar esas fases."""

STATE68 = r"""  ESTADO AL CIERRE SESION 68 (2026-07-15):
    - Cuartos (P097-P100): 4/4 finalizados, fase Cuartos (id=142) BLOQUEADA. Puntajes calculados.
    - Semis (P101 France 0-2 Spain, P102 England 1-2 Argentina): finalizados. Fase 'semis' ABIERTA.
    - Bracket avanzado: Final (P104) Spain vs Argentina | 3er puesto (P103) France vs England (19-jul).
    - Apuestas de Semis NO cargadas -> fase no se puede cerrar ni puntuar todavia.
    - NUEVO: editor de apuestas en Mi Prono (live-playoffs) + PIN=primer nombre + recibo PDF +
      bloqueo 4h + export pronosticos/completados en Monitoreo. Ver historial sesion 68.
    ACCION CUANDO SE CARGUEN APUESTAS DE SEMIS:
      -> POST /calcular-puntajes/2 ; bloquear Semis (fase 'semis') ; abrir/cargar Final+3er puesto.

"""

src=open(MD,encoding='utf-8').read()
a1="Ultima actualizacion: 2026-07-05 (sesion 65)"
n1="Ultima actualizacion: 2026-07-15 (sesion 68)"
a2="2026-07-09 - Sesion Cowork (sesion 67) - CUARTOS: BLOQUEO OCTAVOS + CALCULAR PUNTAJES P097:"
n2=ENTRY+"\n\n"+a2
a3="  ESTADO AL CIERRE SESION 67:"
n3=STATE68+a3

for old,new in [(a1,n1),(a2,n2),(a3,n3)]:
    c=src.count(old)
    if c!=1: raise SystemExit(f'count={c}: {old[:60]!r}')
    src=src.replace(old,new,1)

b=os.path.join(BKP,'CLAUDE.md.'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
shutil.copy2(MD,b); open(MD,'w',encoding='utf-8').write(src)
# verificacion basica de integridad
chk=open(MD,encoding='utf-8').read()
assert "sesion 68" in chk and chk.strip().endswith("puntuar esas fases.") is False, "revisar fin"
print("OK CLAUDE.md actualizado. backup:",os.path.basename(b),"lineas:",chk.count(chr(10))+1)
