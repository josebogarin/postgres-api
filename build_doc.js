const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  PageBreak, LevelFormat, Footer, PageNumber, TableLayoutType
} = require('docx');

const AZUL = "1F3864", AZUL2 = "2E5496", GRIS = "595959", VERDE = "2E7D32",
      ROJO = "B22222", AMBAR = "B7791F", CELLALT = "F4F7FB", CELLHEAD = "1F3864";

const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 140 },
  children: [new TextRun({ text: t, bold: true, color: AZUL, size: 30 })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 100 },
  children: [new TextRun({ text: t, bold: true, color: AZUL2, size: 25 })] });
const P = (runs, opts={}) => new Paragraph({ spacing: { after: 120, line: 276 }, ...opts,
  children: Array.isArray(runs) ? runs : [new TextRun({ text: runs, size: 21 })] });
const t = (text, o={}) => new TextRun({ text, size: 21, ...o });
const bullet = (runs, level=0) => new Paragraph({ numbering:{reference:"bl", level}, spacing:{after:70, line:270},
  children: Array.isArray(runs)?runs:[new TextRun({text:runs, size:21})] });
const num = (runs, level=0) => new Paragraph({ numbering:{reference:"nl", level}, spacing:{after:70, line:270},
  children: Array.isArray(runs)?runs:[new TextRun({text:runs, size:21})] });
const num2 = (runs, level=0) => new Paragraph({ numbering:{reference:"nl2", level}, spacing:{after:70, line:270},
  children: Array.isArray(runs)?runs:[new TextRun({text:runs, size:21})] });

function cell(text, {w, head=false, bold=false, color, alt=false, align} = {}) {
  const shade = head ? CELLHEAD : (alt ? CELLALT : "FFFFFF");
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: shade },
    margins: { top: 40, bottom: 40, left: 90, right: 90 },
    children: [new Paragraph({
      alignment: align || AlignmentType.LEFT,
      children: (Array.isArray(text)?text:[text]).map(x => new TextRun({
        text: String(x), bold: head||bold, size: head?19:20,
        color: head ? "FFFFFF" : (color||"000000")
      }))
    })]
  });
}
function table(colW, rows) {
  const total = colW.reduce((a,b)=>a+b,0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colW, layout: TableLayoutType.FIXED,
    borders: {
      top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"}, bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},
      left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"}, right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E0"}, insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E0"}
    },
    rows: rows.map((r,i)=> new TableRow({ tableHeader: i===0, children: r }))
  });
}
const SPACER = (h=80)=> new Paragraph({ spacing:{after:h}, children:[new TextRun({text:""})] });
const kids = [];

kids.push(new Paragraph({ spacing:{before:1600, after:0}, alignment:AlignmentType.CENTER,
  children:[new TextRun({text:"BECBUC", bold:true, size:64, color:AZUL})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{after:60},
  children:[new TextRun({text:"Copa del Mundo - Sistema de Pronosticos", size:26, color:GRIS})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:400, after:0},
  children:[new TextRun({text:"Propuesta de Rediseno del Sistema de Puntajes", bold:true, size:40, color:AZUL2})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:80},
  children:[new TextRun({text:"Hacia un torneo mas competitivo, con remontadas y mas diversion", italics:true, size:24, color:GRIS})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:1400},
  children:[new TextRun({text:"Documento de discusion para la Administracion de BECBUC", size:22, color:"000000"})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:120},
  children:[new TextRun({text:"Basado en los datos reales del torneo recien cerrado (44 apostadores - 104 partidos)", size:20, color:GRIS})]}));
kids.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:600},
  children:[new TextRun({text:"Julio 2026", size:22, color:GRIS})]}));
kids.push(new Paragraph({ children:[new PageBreak()] }));

kids.push(H1("1. Resumen ejecutivo"));
kids.push(P([t("El torneo que acaba de cerrar funciono tecnicamente sin problemas, pero los datos muestran un problema de "),
  t("competitividad", {bold:true}), t(": la diferencia entre el 1o (1.080 pts) y el ultimo (589 pts) fue de "),
  t("491 puntos", {bold:true, color:ROJO}), t(", y entre el 1o y la mediana, 281 puntos. Con el modelo actual, un apostador de mitad de tabla "),
  t("no tiene forma matematica de remontar", {bold:true}), t(" en la fase final, porque quedan pocos partidos y el lider tambien sigue sumando.")]));
kids.push(P([t("El analisis identifica tres causas y propone un modelo nuevo ("),
  t("BECBUC 2.0", {bold:true, color:AZUL2}), t(") construido sobre tres ideas: "),
  t("(a)", {bold:true}), t(" dejar de regalar puntos por el pronostico facil (el \"0\" en tarjetas y penales), "),
  t("(b)", {bold:true}), t(" premiar el acierto dificil y raro con multiplicadores, y "),
  t("(c)", {bold:true}), t(" introducir mecanicas de remontada (comodin, doble-o-nada, bonus por rareza) y premios por fase, para que el torneo se decida hasta la ultima semana.")]));
kids.push(P([t("Cambios de una linea que proponemos discutir:", {bold:true})]));
kids.push(bullet([t("El \"0\" deja de sumar por si solo; las tarjetas/penales se premian solo si hay evento y se acerto exacto, con multiplicador por cantidad y por rareza.")]));
kids.push(bullet([t("Premio por acertar los cruces de cada fase KO (desde cuartos), independiente del campeon.")]));
kids.push(bullet([t("Comodin por fase (duplicar un partido) y bonus \"contrarian\" (acertar lo que casi nadie acerto vale mas).")]));
kids.push(bullet([t("Globales mas pesados y nuevos items divertidos (props, figura del partido, puntos de confianza, survivor paralelo).")]));
kids.push(P([t("Todo es implementable sin reescribir el sistema: el motor de puntajes ya esta preparado por competencia (patron Strategy), asi que un torneo nuevo puede estrenar el modelo sin tocar el actual.", {italics:true, color:GRIS})]));

kids.push(new Paragraph({ children:[new PageBreak()] }));
kids.push(H1("2. Diagnostico con datos reales"));
kids.push(P("Todos los numeros de esta seccion salen de la base de datos del torneo recien cerrado (torneo 2): 44 apostadores, 104 partidos, mas los 7 pronosticos globales."));

kids.push(H2("2.1. La brecha es demasiado grande y se abre temprano"));
kids.push(table([2000,1450,1550,1450,2050], [
  [cell("Posicion",{w:2000,head:true}), cell("Puntos",{w:1450,head:true,align:AlignmentType.CENTER}),
   cell("De partidos",{w:1550,head:true,align:AlignmentType.CENTER}), cell("Globales",{w:1450,head:true,align:AlignmentType.CENTER}),
   cell("Brecha vs 1o",{w:2050,head:true,align:AlignmentType.CENTER})],
  [cell("1o (lider)",{w:2000,bold:true}), cell("1.080",{w:1450,align:AlignmentType.CENTER,bold:true}), cell("992",{w:1550,align:AlignmentType.CENTER}), cell("62",{w:1450,align:AlignmentType.CENTER}), cell("-",{w:2050,align:AlignmentType.CENTER})],
  [cell("2o",{w:2000,alt:true}), cell("983",{w:1450,align:AlignmentType.CENTER,alt:true}), cell("884",{w:1550,align:AlignmentType.CENTER,alt:true}), cell("72",{w:1450,align:AlignmentType.CENTER,alt:true}), cell("-97",{w:2050,align:AlignmentType.CENTER,alt:true})],
  [cell("Mediana (22o)",{w:2000}), cell("799",{w:1450,align:AlignmentType.CENTER}), cell("~725",{w:1550,align:AlignmentType.CENTER}), cell("~50",{w:1450,align:AlignmentType.CENTER}), cell("-281",{w:2050,align:AlignmentType.CENTER,color:AMBAR})],
  [cell("Ultimo (44o)",{w:2000,alt:true}), cell("589",{w:1450,align:AlignmentType.CENTER,alt:true,bold:true}), cell("520",{w:1550,align:AlignmentType.CENTER,alt:true}), cell("46",{w:1450,align:AlignmentType.CENTER,alt:true}), cell("-491",{w:2050,align:AlignmentType.CENTER,alt:true,color:ROJO})],
]));
kids.push(SPACER());
kids.push(P([t("Promedio 814, mediana 799. La brecha 1o-ultimo de 491 puntos equivale a acertar el "),
  t("marcador exacto de ~12 finales", {bold:true}), t(" - un abismo imposible de cerrar con los partidos que quedan en la fase final.")]));

kids.push(H2("2.2. Los puntos se reparten mal: premian lo facil, no lo dificil"));
kids.push(P("Sumando los puntos de todos los apostadores por cada item de partido, se ve donde esta \"la plata\" del sistema:"));
kids.push(table([2600,1500,1500,2700],[
  [cell("Item de partido",{w:2600,head:true}), cell("Puntos totales",{w:1500,head:true,align:AlignmentType.CENTER}), cell("% del total",{w:1500,head:true,align:AlignmentType.CENTER}), cell("Lectura",{w:2700,head:true})],
  [cell("H - Resultado (1x2)",{w:2600}), cell("14.156",{w:1500,align:AlignmentType.CENTER}), cell("42,9%",{w:1500,align:AlignmentType.CENTER}), cell("Base sana",{w:2700,color:VERDE})],
  [cell("I - Marcador exacto",{w:2600,alt:true}), cell("5.964",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("18,1%",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("Base sana",{w:2700,alt:true,color:VERDE})],
  [cell("K - Tarjetas rojas",{w:2600}), cell("3.623",{w:1500,align:AlignmentType.CENTER}), cell("11,0%",{w:1500,align:AlignmentType.CENTER}), cell("\"0 facil\": casi todos ponen 0 y aciertan",{w:2700,color:ROJO})],
  [cell("P - Equipo que clasifica",{w:2600,alt:true}), cell("3.422",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("10,4%",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("Correlaciona con el resultado",{w:2700,alt:true,color:AMBAR})],
  [cell("M - Penales en el juego",{w:2600}), cell("3.189",{w:1500,align:AlignmentType.CENTER}), cell("9,7%",{w:1500,align:AlignmentType.CENTER}), cell("\"0 facil\": casi todos ponen 0",{w:2700,color:ROJO})],
  [cell("L - VAR",{w:2600,alt:true}), cell("1.367",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("4,1%",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("Parcialmente \"0 facil\"",{w:2700,alt:true,color:AMBAR})],
  [cell("J - Tarjetas amarillas",{w:2600}), cell("877",{w:1500,align:AlignmentType.CENTER}), cell("2,7%",{w:1500,align:AlignmentType.CENTER}), cell("Dificil de acertar exacto",{w:2700})],
  [cell("O - Tanda de penales",{w:2600,alt:true}), cell("220",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("0,7%",{w:1500,align:AlignmentType.CENTER,alt:true}), cell("Irrelevante hoy",{w:2700,alt:true,color:GRIS})],
  [cell("N - Minuto del 1er gol",{w:2600}), cell("173",{w:1500,align:AlignmentType.CENTER}), cell("0,5%",{w:1500,align:AlignmentType.CENTER}), cell("Irrelevante hoy",{w:2700,color:GRIS})],
]));
kids.push(SPACER());
kids.push(P([t("Dos conclusiones fuertes: ", {bold:true}),
  t("(1) los items de tarjetas y penales (K + M = 6.812 pts, ~21% del total) reparten muchisimos puntos por poner \"0\" y acertar - no miden pericia y "),
  t("no separan", {bold:true}), t(", porque casi todos aciertan lo mismo. "),
  t("(2) los items que SI requieren pericia y podrian generar diferencias (minuto del gol N y tanda O) valen juntos apenas 393 pts (1,2%): "),
  t("hoy son decorativos.", {bold:true})]));

kids.push(H2("2.3. Medio torneo se juega en la fase de grupos"));
kids.push(table([2400,1400,1900,2100],[
  [cell("Fase",{w:2400,head:true}), cell("Partidos",{w:1400,head:true,align:AlignmentType.CENTER}), cell("Puntos totales",{w:1900,head:true,align:AlignmentType.CENTER}), cell("Puntos por partido",{w:2100,head:true,align:AlignmentType.CENTER})],
  [cell("Grupos",{w:2400}), cell("72",{w:1400,align:AlignmentType.CENTER}), cell("16.564  (50%)",{w:1900,align:AlignmentType.CENTER,bold:true}), cell("~230",{w:2100,align:AlignmentType.CENTER})],
  [cell("16avos",{w:2400,alt:true}), cell("16",{w:1400,align:AlignmentType.CENTER,alt:true}), cell("7.783",{w:1900,align:AlignmentType.CENTER,alt:true}), cell("~486",{w:2100,align:AlignmentType.CENTER,alt:true})],
  [cell("Octavos",{w:2400}), cell("8",{w:1400,align:AlignmentType.CENTER}), cell("3.353",{w:1900,align:AlignmentType.CENTER}), cell("~419",{w:2100,align:AlignmentType.CENTER})],
  [cell("Cuartos",{w:2400,alt:true}), cell("4",{w:1400,align:AlignmentType.CENTER,alt:true}), cell("3.163",{w:1900,align:AlignmentType.CENTER,alt:true}), cell("~791",{w:2100,align:AlignmentType.CENTER,alt:true})],
  [cell("Semifinal",{w:2400}), cell("2",{w:1400,align:AlignmentType.CENTER}), cell("1.105",{w:1900,align:AlignmentType.CENTER}), cell("~552",{w:2100,align:AlignmentType.CENTER})],
  [cell("Final",{w:2400,alt:true}), cell("1",{w:1400,align:AlignmentType.CENTER,alt:true}), cell("845",{w:1900,align:AlignmentType.CENTER,alt:true}), cell("845",{w:2100,align:AlignmentType.CENTER,alt:true})],
  [cell("3er puesto",{w:2400}), cell("1",{w:1400,align:AlignmentType.CENTER}), cell("178",{w:1900,align:AlignmentType.CENTER}), cell("178",{w:2100,align:AlignmentType.CENTER})],
]));
kids.push(SPACER());
kids.push(P([t("La fase de grupos reparte la mitad de todos los puntos. Cuando arranca la eliminacion directa, la brecha "),
  t("ya esta formada y practicamente congelada", {bold:true}), t(": los cuartos, semis y final juntos apenas ofrecen ~5.100 puntos, y encima el lider tambien los aprovecha. Por eso las remontadas son casi imposibles.")]));

kids.push(H2("2.4. Los globales pesan poco (y son la mejor herramienta de remontada desperdiciada)"));
kids.push(P([t("Los 7 globales sumaron 1.656 puntos en total: apenas el "), t("4,8% del torneo", {bold:true}),
  t(". Sin embargo, entre apostadores varian muchisimo (de 0 a 72 pts). Son de alta varianza y de \"apuesta a futuro\" - exactamente el tipo de item que permite a alguien de abajo dar el golpe. Hoy estan infrautilizados.")]));

kids.push(new Paragraph({ children:[new PageBreak()] }));
kids.push(H1("3. Principios de diseno (que queremos lograr)"));
kids.push(P("Tomando ideas de ligas de pronosticos y \"pools\" deportivos, un buen sistema competitivo cumple estos principios:"));
kids.push(num([t("Premiar la dificultad, no la certeza.", {bold:true}), t(" Acertar lo obvio (un 0-0 de tarjetas rojas) debe valer poco o nada; acertar lo raro debe valer mucho.")]));
kids.push(num([t("Recompensa por rareza (\"contrarian\").", {bold:true}), t(" Si pocos acertaron algo, quien lo acerto gana mas. Es el mecanismo natural de remontada: premia al valiente que arriesgo distinto.")]));
kids.push(num([t("Volatilidad creciente hacia el final.", {bold:true}), t(" Las fases finales deben pesar mas y ofrecer swings grandes, para que la ultima semana pueda cambiar el podio.")]));
kids.push(num([t("Decisiones estrategicas del jugador.", {bold:true}), t(" Comodines, doble-o-nada y puntos de confianza le dan al apostador palancas para arriesgar y remontar.")]));
kids.push(num([t("Mantener enganchado al que va perdiendo.", {bold:true}), t(" Juegos paralelos (survivor) y props divertidos para que nadie \"se baje\" a mitad de torneo.")]));
kids.push(num([t("Simplicidad de entrada, profundidad opcional.", {bold:true}), t(" Que se pueda jugar basico, pero que el que quiera estrategia la tenga.")]));

kids.push(new Paragraph({ children:[new PageBreak()] }));
kids.push(H1("4. Modelo propuesto - BECBUC 2.0"));

kids.push(H2("Pilar A - Items de partido: se acaba el \"0 gratis\", entran los multiplicadores"));
kids.push(P([t("Regla nueva para tarjetas (J amarillas, K rojas) y penales en el juego (M): ", {bold:true}),
  t("el valor 0 ya no otorga puntos por si solo.", {color:ROJO, bold:true}),
  t(" Solo se puntua si hubo evento real (valor >= 1) y el apostador acerto el numero exacto. Y cuando acierta, gana en funcion de cuan dificil era:")]));
kids.push(bullet([t("Multiplicador por cantidad: ", {bold:true}), t("puntos = base x valor_real. El que arriesgo \"4 tarjetas rojas\" y acierta gana base x 4. Premia la audacia (tu ejemplo).")]));
kids.push(bullet([t("Multiplicador por rareza: ", {bold:true}), t("si menos del 15-20% de los apostadores acerto ese valor exacto, se multiplica x2 o x3. El acierto raro te acerca de golpe.")]));
kids.push(P([t("Marcador exacto (I): ", {bold:true}), t("se mantiene el escalado por fase, pero se agrega un "),
  t("bonus contrarian", {bold:true}), t(": si ese marcador exacto lo puso <5% de la gente y acierta, x2. Premia el resultado arriesgado y poco \"cantado\".")]));
kids.push(P([t("Minuto del 1er gol (N) y tanda de penales (O): ", {bold:true}),
  t("hoy valen 0,5-0,7%. Se los revaloriza y se los vuelve escalonados por cercania (ej. N: 4 pts al mas cercano, 2 pts a +/-2 min, 1 pt a +/-5 min) para que aporten separacion real entre expertos.")]));

kids.push(H2("Pilar B - Premio por ganar la fase (desde cuartos)"));
kids.push(P([t("Un bonus ", {}), t("independiente", {bold:true}), t(" del puntaje de cada partido y del global de campeon, que premia \"leer el cuadro\". Desde cuartos, por cada cruce KO acertado (que equipo pasa a la siguiente fase), un bonus escalonado:")]));
kids.push(table([3200,2400,2400],[
  [cell("Fase",{w:3200,head:true}), cell("Bonus por cruce acertado",{w:2400,head:true,align:AlignmentType.CENTER}), cell("Bonus si acierta TODOS",{w:2400,head:true,align:AlignmentType.CENTER})],
  [cell("Cuartos (4 cruces)",{w:3200}), cell("+8",{w:2400,align:AlignmentType.CENTER}), cell("+15 extra",{w:2400,align:AlignmentType.CENTER})],
  [cell("Semifinal (2 cruces)",{w:3200,alt:true}), cell("+15",{w:2400,align:AlignmentType.CENTER,alt:true}), cell("+20 extra",{w:2400,align:AlignmentType.CENTER,alt:true})],
  [cell("Final (campeon del cuadro)",{w:3200}), cell("+25",{w:2400,align:AlignmentType.CENTER}), cell("-",{w:2400,align:AlignmentType.CENTER})],
]));
kids.push(SPACER());
kids.push(P([t("Esto crea un \"segundo torneo\" de estrategia de bracket que se define tarde y puede reordenar el ranking. Los valores son ejemplos para calibrar.", {italics:true, color:GRIS})]));

kids.push(H2("Pilar C - Globales potenciados (subir del 5% al ~12-15%)"));
kids.push(bullet([t("Subir el peso de los actuales (campeon, finalistas, goleador) y agregar "), t("bonus por rareza", {bold:true}), t(" tambien en globales: si pocos acertaron al campeon, valen mas.")]));
kids.push(bullet([t("Nuevos globales de \"sorpresa\": equipo revelacion, jugador revelacion, primer eliminado grande, pais que llega mas lejos de lo esperado.")]));
kids.push(bullet([t("Como se definen al final y son de alta varianza, son el vehiculo ideal de remontada para los de abajo.")]));

kids.push(H2("Pilar D - Mecanicas de remontada (lo mas disruptivo)"));
kids.push(P([t("Comodin / Joker por fase. ", {bold:true}), t("Cada apostador elige, antes de que empiece cada fase KO, "),
  t("un partido donde su puntaje se DUPLICA", {bold:true}), t(". Riesgo/recompensa: si acierta ese partido, salto grande; si falla, no suma extra.")]));
kids.push(P([t("Doble-o-nada opcional. ", {bold:true}), t("En un partido por fase, el apostador puede \"subir la apuesta\": si acierta el resultado, sus puntos de ese partido se duplican; si falla, pierde una parte fija. Invita a los de abajo a arriesgar.")]));
kids.push(P([t("Bonus contrarian transversal. ", {bold:true}), t("Ya descrito en A y C: acertar lo que casi nadie acerto multiplica. Es el corazon del sistema de remontadas.")]));
kids.push(P([t("(Opcional / a debatir) \"Empuje al rezagado\". ", {bold:true, color:AMBAR}), t("Los apostadores del 50% inferior reciben un pequeno multiplicador (ej. x1,1) solo en los globales de la fase final. Mecanica tipo \"rubber-banding\" de los videojuegos: mantiene todo abierto hasta el final, pero puede sentirse artificial. Lo dejamos como decision de la organizacion.")]));

kids.push(H2("Pilar E - Items nuevos, divertidos y motivadores"));
kids.push(bullet([t("Props por partido (si/no, 1-2 pts): ", {bold:true}), t("habra autogol? penal fallado? gol de tiro libre/cabeza? tarjeta al banco o al DT? Divierten y no exigen pericia tecnica.")]));
kids.push(bullet([t("Figura del partido (MVP): ", {bold:true}), t("acertar el jugador destacado. Muy comentable.")]));
kids.push(bullet([t("Puntos de confianza (confidence pool): ", {bold:true}), t("en cada fase el apostador reparte un presupuesto de \"fichas\" entre sus pronosticos; acertar donde puso mas fichas rinde mas. Agrega estrategia sin cambiar la boleta base.")]));
kids.push(bullet([t("Survivor paralelo: ", {bold:true}), t("juego secundario de eliminacion (cada ronda elegis un equipo que gane, sin repetir; si pierde, quedas fuera del survivor) con su propio premio. Mantiene enganchado al que ya no pelea el ranking principal.")]));
kids.push(bullet([t("Pronostico \"cisne negro\": ", {bold:true}), t("una prediccion especial de alto riesgo (ej. la gran sorpresa del torneo) que casi nadie acierta y paga muy alto.")]));

kids.push(new Paragraph({ children:[new PageBreak()] }));
kids.push(H1("5. Impacto esperado sobre la competitividad"));
kids.push(P([t("Con los datos actuales, el gap 1o-mediana es de 281 pts y hoy es irremontable. Veamos cuanto \"abre\" cada mecanica nueva la posibilidad de remontar:")]));
kids.push(table([3400,2600,2600],[
  [cell("Mecanica",{w:3400,head:true}), cell("Swing potencial por fase KO",{w:2600,head:true,align:AlignmentType.CENTER}), cell("Efecto",{w:2600,head:true,align:AlignmentType.CENTER})],
  [cell("Comodin (duplica un partido)",{w:3400}), cell("+40 a +80",{w:2600,align:AlignmentType.CENTER}), cell("Alto",{w:2600,align:AlignmentType.CENTER,color:VERDE})],
  [cell("Bonus contrarian (marcador raro)",{w:3400,alt:true}), cell("+20 a +40 / partido",{w:2600,align:AlignmentType.CENTER,alt:true}), cell("Alto",{w:2600,align:AlignmentType.CENTER,alt:true,color:VERDE})],
  [cell("Premio por fase (bracket)",{w:3400}), cell("+30 a +60",{w:2600,align:AlignmentType.CENTER}), cell("Medio-alto",{w:2600,align:AlignmentType.CENTER,color:VERDE})],
  [cell("Globales potenciados",{w:3400,alt:true}), cell("+30 a +60 (al final)",{w:2600,align:AlignmentType.CENTER,alt:true}), cell("Medio-alto",{w:2600,align:AlignmentType.CENTER,alt:true,color:VERDE})],
  [cell("Multiplicador por cantidad (tarjetas)",{w:3400}), cell("+5 a +20",{w:2600,align:AlignmentType.CENTER}), cell("Medio",{w:2600,align:AlignmentType.CENTER,color:AMBAR})],
]));
kids.push(SPACER());
kids.push(P([t("Sumadas, estas palancas permiten que un apostador de mitad de tabla que "),
  t("acierte lo dificil en cuartos, semis y final", {bold:true}),
  t(" recupere del orden de 150-250 puntos en la recta final - suficiente para pelear el podio. El objetivo no es regalar la remontada, sino "),
  t("hacerla posible con aciertos de merito", {bold:true}), t(", que es lo que engancha.")]));

kids.push(H1("6. Como se implementa (sin romper lo actual)"));
kids.push(P([t("El sistema ya esta preparado: el motor de puntajes usa un patron por competencia ("),
  t("Strategy + Registry", {bold:true}), t("). Cada torneo resuelve su propio \"engine\" por codigo. Por eso podemos crear un motor "),
  t("copa_playoff_2027", {italics:true}), t(" con las reglas nuevas y estrenarlo en un torneo de prueba, "),
  t("sin tocar el motor del torneo ya cerrado.", {bold:true})]));
kids.push(num2([t("Aprobacion del reglamento 2.0 ", {bold:true}), t("(esta discusion).")]));
kids.push(num2([t("Migracion de BD: ", {bold:true}), t("columnas nuevas en la apuesta (comodin, fichas de confianza, props, doble-o-nada) y tablas de bonus por fase / rareza.")]));
kids.push(num2([t("Motor de puntajes v3: ", {bold:true}), t("nuevo engine parametrizable con multiplicadores por cantidad y rareza, premio por fase y globales potenciados.")]));
kids.push(num2([t("Boleta (portal + movil): ", {bold:true}), t("inputs para comodin, props, confianza; misma experiencia base.")]));
kids.push(num2([t("Excel y transparencia: ", {bold:true}), t("reflejar los nuevos items y multiplicadores en la auditoria.")]));
kids.push(num2([t("Prueba piloto: ", {bold:true}), t("estrenar en un playoff chico, medir la nueva distribucion de puntos y ajustar los valores antes del proximo Mundial.")]));

kids.push(new Paragraph({ children:[new PageBreak()] }));
kids.push(H1("7. Decisiones para la Administracion"));
kids.push(P("Puntos concretos a votar/definir antes de arrancar los ajustes:"));
kids.push(table([600, 6600, 2000],[
  [cell("#",{w:600,head:true,align:AlignmentType.CENTER}), cell("Decision",{w:6600,head:true}), cell("Recomendacion",{w:2000,head:true,align:AlignmentType.CENTER})],
  [cell("1",{w:600,align:AlignmentType.CENTER}), cell("Eliminar el puntaje por acertar \"0\" en tarjetas y penales?",{w:6600}), cell("Si",{w:2000,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("2",{w:600,align:AlignmentType.CENTER,alt:true}), cell("Multiplicar por cantidad (x valor real) en tarjetas/penales?",{w:6600,alt:true}), cell("Si",{w:2000,align:AlignmentType.CENTER,alt:true,color:VERDE,bold:true})],
  [cell("3",{w:600,align:AlignmentType.CENTER}), cell("Agregar bonus por rareza / contrarian (acierto raro paga mas)?",{w:6600}), cell("Si",{w:2000,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("4",{w:600,align:AlignmentType.CENTER,alt:true}), cell("Premio por acertar los cruces de cada fase (desde cuartos)?",{w:6600,alt:true}), cell("Si",{w:2000,align:AlignmentType.CENTER,alt:true,color:VERDE,bold:true})],
  [cell("5",{w:600,align:AlignmentType.CENTER}), cell("Comodin (duplicar un partido) por fase KO?",{w:6600}), cell("Si",{w:2000,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("6",{w:600,align:AlignmentType.CENTER,alt:true}), cell("Cuanto subir el peso de los globales? (propuesta: 12-15%)",{w:6600,alt:true}), cell("A definir",{w:2000,align:AlignmentType.CENTER,alt:true,color:AMBAR})],
  [cell("7",{w:600,align:AlignmentType.CENTER}), cell("Sumar props divertidos (autogol, penal fallado, figura, etc.)?",{w:6600}), cell("Si",{w:2000,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("8",{w:600,align:AlignmentType.CENTER,alt:true}), cell("Puntos de confianza (repartir fichas por fase)?",{w:6600,alt:true}), cell("Probar",{w:2000,align:AlignmentType.CENTER,alt:true,color:AMBAR})],
  [cell("9",{w:600,align:AlignmentType.CENTER}), cell("Survivor paralelo como juego secundario?",{w:6600}), cell("Probar",{w:2000,align:AlignmentType.CENTER,color:AMBAR})],
  [cell("10",{w:600,align:AlignmentType.CENTER,alt:true}), cell("\"Empuje al rezagado\" (rubber-banding en globales finales)?",{w:6600,alt:true}), cell("Debatir",{w:2000,align:AlignmentType.CENTER,alt:true,color:ROJO})],
]));
kids.push(SPACER());
kids.push(P([t("Si la Administracion aprueba estos lineamientos, el siguiente paso es fijar los valores exactos (calibracion) y arrancar los ajustes tecnicos para estrenarlos en el proximo torneo playoff.", {italics:true})]));

const doc = new Document({
  creator: "BECBUC", title: "Propuesta Rediseno Puntajes BECBUC",
  numbering: { config: [
    { reference: "bl", levels: [
      { level:0, format:LevelFormat.BULLET, text:"•", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:520, hanging:260 } } } },
      { level:1, format:LevelFormat.BULLET, text:"–", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:1000, hanging:260 } } } },
    ]},
    { reference: "nl", levels: [
      { level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:520, hanging:260 } } } },
    ]},
    { reference: "nl2", levels: [
      { level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:520, hanging:260 } } } },
    ]},
  ]},
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1100, bottom: 1100, left: 1200, right: 1200 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ text:"BECBUC - Propuesta de rediseno de puntajes - ", size:16, color:GRIS }),
                  new TextRun({ children:["Pag. ", PageNumber.CURRENT], size:16, color:GRIS }) ] }) ] }) },
    children: kids
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[2] || "BECBUC_Propuesta_Puntajes.docx", buf);
  console.log("OK docx bytes:", buf.length);
});
