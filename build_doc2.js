const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  PageBreak, LevelFormat, Footer, PageNumber, TableLayoutType
} = require('docx');

const AZUL="1F3864", AZUL2="2E5496", GRIS="595959", VERDE="2E7D32",
      ROJO="B22222", AMBAR="B7791F", CELLALT="F4F7FB", CELLHEAD="1F3864",
      VERDECLARO="E7F3E9", AMBARCLARO="FBF3E2";

const H1=(x)=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:300,after:130},children:[new TextRun({text:x,bold:true,color:AZUL,size:30})]});
const H2=(x)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:220,after:100},children:[new TextRun({text:x,bold:true,color:AZUL2,size:25})]});
const H3=(x)=>new Paragraph({heading:HeadingLevel.HEADING_3,spacing:{before:150,after:70},children:[new TextRun({text:x,bold:true,color:GRIS,size:22})]});
const P=(runs,opts={})=>new Paragraph({spacing:{after:120,line:276},...opts,children:Array.isArray(runs)?runs:[new TextRun({text:runs,size:21})]});
const t=(text,o={})=>new TextRun({text,size:21,...o});
const bullet=(runs,ref="bl",level=0)=>new Paragraph({numbering:{reference:ref,level},spacing:{after:70,line:270},children:Array.isArray(runs)?runs:[new TextRun({text:runs,size:21})]});
const SPACER=(h=80)=>new Paragraph({spacing:{after:h},children:[new TextRun({text:""})]});

function cell(text,{w,head=false,bold=false,color,fill,align}={}) {
  const shade=head?CELLHEAD:(fill||"FFFFFF");
  return new TableCell({
    width:{size:w,type:WidthType.DXA},
    shading:{type:ShadingType.CLEAR,color:"auto",fill:shade},
    margins:{top:38,bottom:38,left:80,right:80},
    children:[new Paragraph({alignment:align||AlignmentType.LEFT,
      children:(Array.isArray(text)?text:[text]).map(x=>new TextRun({text:String(x),bold:head||bold,size:head?18:19,color:head?"FFFFFF":(color||"000000")}))})]
  });
}
function table(colW,rows){
  const total=colW.reduce((a,b)=>a+b,0);
  return new Table({width:{size:total,type:WidthType.DXA},columnWidths:colW,layout:TableLayoutType.FIXED,
    borders:{top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},
      left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C4"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E0"},insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E0"}},
    rows:rows.map((r,i)=>new TableRow({tableHeader:i===0,children:r}))});
}
// caja destacada
function box(title,runs,fill=VERDECLARO,bc=VERDE){
  return new Table({width:{size:9840,type:WidthType.DXA},columnWidths:[9840],layout:TableLayoutType.FIXED,
    borders:{top:{style:BorderStyle.SINGLE,size:8,color:bc},bottom:{style:BorderStyle.SINGLE,size:8,color:bc},
      left:{style:BorderStyle.SINGLE,size:18,color:bc},right:{style:BorderStyle.SINGLE,size:8,color:bc},
      insideHorizontal:{style:BorderStyle.NONE},insideVertical:{style:BorderStyle.NONE}},
    rows:[new TableRow({children:[new TableCell({width:{size:9840,type:WidthType.DXA},
      shading:{type:ShadingType.CLEAR,color:"auto",fill},margins:{top:100,bottom:100,left:160,right:140},
      children:[
        new Paragraph({spacing:{after:60},children:[new TextRun({text:title,bold:true,size:21,color:bc})]}),
        ...(Array.isArray(runs)?runs:[new Paragraph({children:[new TextRun({text:runs,size:20})]})])
      ]})]})]});
}
const kids=[];

// PORTADA
kids.push(new Paragraph({spacing:{before:1500,after:0},alignment:AlignmentType.CENTER,children:[new TextRun({text:"BECBUC 2.0",bold:true,size:64,color:AZUL})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:60},children:[new TextRun({text:"Nuevo Sistema de Puntajes - Modelo Detallado",size:28,color:GRIS})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:360,after:0},children:[new TextRun({text:"Grupos que no deciden, playoffs que lo definen todo",bold:true,size:32,color:AZUL2})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:80},children:[new TextRun({text:"Con puntajes por fase, multiplicadores, comodin y ejemplos trabajados",italics:true,size:23,color:GRIS})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:1300},children:[new TextRun({text:"Documento tecnico para la Administracion de BECBUC",size:22})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:100},children:[new TextRun({text:"Valores propuestos y sujetos a calibracion - Julio 2026",size:20,color:GRIS})]}));
kids.push(new Paragraph({children:[new PageBreak()]}));

// 1. OBJETIVO
kids.push(H1("1. Objetivo del rediseno"));
kids.push(P([t("Objetivo central: ",{bold:true}),t("que en la fase de grupos "),t("no se defina nada",{bold:true,color:ROJO}),t(", y que "),t("todo el torneo se juegue en los playoffs",{bold:true}),t(". El sistema debe permitir que un apostador de mitad de tabla remonte en la eliminacion directa a base de aciertos de merito.")]));
kids.push(P("Para lograrlo, el modelo se apoya en cuatro palancas concretas:"));
kids.push(bullet([t("Grupos con peso minimo: ",{bold:true}),t("los partidos de grupos valen muy poco. La ventaja acumulada al terminar grupos debe ser chica (meta: grupos < 12% de los puntos del torneo).")]));
kids.push(bullet([t("Playoffs con puntajes crecientes: ",{bold:true}),t("el marcador exacto se duplica ronda a ronda hasta semifinal, y desde semifinal vale muchisimo mas que todo lo demas.")]));
kids.push(bullet([t("Multiplicadores por acertar el cruce: ",{bold:true}),t("adivinar quien pasa una llave (como fue el caso de Paraguay) multiplica x2 los puntos de ese partido, y x3 si es una sorpresa.")]));
kids.push(bullet([t("Comodin x5: ",{bold:true}),t("cada apostador tiene un comodin que multiplica x5 sus puntos en un partido de playoff a eleccion.")]));
kids.push(box("La regla de oro","Nada se decide en grupos. La eliminacion directa vale tanto, y los multiplicadores pesan tanto, que el podio se define entre cuartos y la final. El que arriesga y acierta en playoffs, remonta.",VERDECLARO,VERDE));

// 2. QUE SE ELIMINA / MANTIENE
kids.push(H1("2. Que se elimina y que se mantiene"));
kids.push(table([2600,1700,5540],[
  [cell("Item actual",{w:2600,head:true}),cell("Decision",{w:1700,head:true,align:AlignmentType.CENTER}),cell("Motivo",{w:5540,head:true})],
  [cell("L - VAR",{w:2600}),cell("REEMPLAZAR",{w:1700,align:AlignmentType.CENTER,color:AMBAR,bold:true}),cell("No aporta (casi todos ponen 0/1). Se reemplaza por un item nuevo y divertido: CANTIDAD DE CAMBIOS del partido (ver seccion 5).",{w:5540})],
  [cell("P - Equipo que clasifica (item plano)",{w:2600,fill:CELLALT}),cell("ELIMINAR como item",{w:1700,align:AlignmentType.CENTER,color:ROJO,bold:true,fill:CELLALT}),cell("Se reemplaza por algo mejor: acertar el cruce pasa a ser un MULTIPLICADOR del puntaje del partido (ver seccion 4).",{w:5540,fill:CELLALT})],
  [cell("H - Resultado (1x2)",{w:2600}),cell("MANTENER",{w:1700,align:AlignmentType.CENTER,color:VERDE,bold:true}),cell("Base del juego. Sube fuerte por fase.",{w:5540})],
  [cell("I - Marcador exacto",{w:2600,fill:CELLALT}),cell("MANTENER++",{w:1700,align:AlignmentType.CENTER,color:VERDE,bold:true,fill:CELLALT}),cell("El corazon del playoff: se duplica por ronda hasta semis y explota en semis/final.",{w:5540,fill:CELLALT})],
  [cell("J - Amarillas / K - Rojas",{w:2600}),cell("MANTENER*",{w:1700,align:AlignmentType.CENTER,color:AMBAR,bold:true}),cell("Con regla nueva: el 0 no suma; solo puntua el acierto exacto con evento real, y multiplica por cantidad.",{w:5540})],
  [cell("M - Penales en el juego",{w:2600,fill:CELLALT}),cell("MANTENER*",{w:1700,align:AlignmentType.CENTER,color:AMBAR,bold:true,fill:CELLALT}),cell("Igual que tarjetas: 0 no suma, exacto multiplica por cantidad.",{w:5540,fill:CELLALT})],
  [cell("N - Minuto 1er gol / O - Tanda",{w:2600}),cell("REVALORIZAR",{w:1700,align:AlignmentType.CENTER,color:AMBAR,bold:true}),cell("Hoy valen ~1%. Se suben para que la pericia separe.",{w:5540})],
]));

// 3. PUNTAJES PRINCIPALES POR FASE
kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("3. Puntajes principales por fase (propuesta)"));
kids.push(P([t("El nucleo del modelo. El "),t("resultado (H)",{bold:true}),t(" y el "),t("marcador exacto (I)",{bold:true}),t(" se duplican ronda a ronda hasta semifinal; desde semifinal dan un salto para que valgan mucho mas que el resto. Grupos valen casi nada a proposito.")]));
kids.push(table([2500,1500,1800,4040],[
  [cell("Fase",{w:2500,head:true}),cell("H Resultado",{w:1500,head:true,align:AlignmentType.CENTER}),cell("I Marcador exacto",{w:1800,head:true,align:AlignmentType.CENTER}),cell("Nota",{w:4040,head:true})],
  [cell("Grupos",{w:2500}),cell("2",{w:1500,align:AlignmentType.CENTER}),cell("4",{w:1800,align:AlignmentType.CENTER}),cell("Peso minimo: grupos NO deciden.",{w:4040,color:GRIS})],
  [cell("16avos",{w:2500,fill:CELLALT}),cell("4",{w:1500,align:AlignmentType.CENTER,fill:CELLALT}),cell("8",{w:1800,align:AlignmentType.CENTER,fill:CELLALT}),cell("Arranca el playoff (x2 vs grupos).",{w:4040,fill:CELLALT})],
  [cell("Octavos",{w:2500}),cell("8",{w:1500,align:AlignmentType.CENTER}),cell("16",{w:1800,align:AlignmentType.CENTER}),cell("x2.",{w:4040})],
  [cell("Cuartos",{w:2500,fill:CELLALT}),cell("15",{w:1500,align:AlignmentType.CENTER,fill:CELLALT}),cell("30",{w:1800,align:AlignmentType.CENTER,fill:CELLALT}),cell("~x2.",{w:4040,fill:CELLALT})],
  [cell("Semifinal",{w:2500}),cell("30",{w:1500,align:AlignmentType.CENTER,bold:true,color:AZUL}),cell("60",{w:1800,align:AlignmentType.CENTER,bold:true,color:AZUL}),cell("SALTO: desde aca vale mucho mas.",{w:4040,color:AZUL,bold:true})],
  [cell("Final",{w:2500,fill:AMBARCLARO}),cell("50",{w:1500,align:AlignmentType.CENTER,bold:true,color:ROJO,fill:AMBARCLARO}),cell("100",{w:1800,align:AlignmentType.CENTER,bold:true,color:ROJO,fill:AMBARCLARO}),cell("El partido mas valioso del torneo.",{w:4040,color:ROJO,bold:true,fill:AMBARCLARO})],
  [cell("3er puesto",{w:2500}),cell("20",{w:1500,align:AlignmentType.CENTER}),cell("40",{w:1800,align:AlignmentType.CENTER}),cell("Alto, pero por debajo de semis/final.",{w:4040})],
]));
kids.push(SPACER());
kids.push(P([t("Comparacion clave: ",{bold:true}),t("un marcador exacto de la final (100) vale lo mismo que "),t("25 marcadores exactos de grupos",{bold:true}),t(" (4 c/u). Asi se garantiza que el playoff mande.")]));

// 4. MULTIPLICADORES
kids.push(H1("4. Multiplicadores: cruce y comodin"));
kids.push(H2("4.1. Acertar el cruce (quien pasa la llave)"));
kids.push(P([t("Reemplaza al viejo item \"clasificados\". Si el apostador acerto que equipo pasa una llave KO, "),t("multiplica el puntaje de ESE partido",{bold:true}),t(":")]));
kids.push(table([4200,1900,3740],[
  [cell("Situacion",{w:4200,head:true}),cell("Multiplicador",{w:1900,head:true,align:AlignmentType.CENTER}),cell("Ejemplo",{w:3740,head:true})],
  [cell("Acerto el equipo que pasa (favorito)",{w:4200}),cell("x2",{w:1900,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("Espana elimina a Belgica y el apostador lo puso.",{w:3740})],
  [cell("Acerto una SORPRESA (pasa el no-favorito)",{w:4200,fill:CELLALT}),cell("x3",{w:1900,align:AlignmentType.CENTER,bold:true,color:ROJO,fill:CELLALT}),cell("Paraguay elimina a Alemania y el apostador se animo a ponerlo.",{w:3740,fill:CELLALT})],
]));
kids.push(SPACER());
kids.push(P([t("El favorito/sorpresa se define por el ranking FIFA (o el sembrado del cuadro). Este multiplicador premia leer el cuadro y animarse a las sorpresas - justo el tipo de acierto que permite remontar.",{italics:true,color:GRIS})]));

kids.push(H2("4.2. El comodin x5"));
kids.push(P([t("Cada apostador tiene "),t("un (1) comodin para todo el playoff",{bold:true}),t(". Lo declara ANTES de que empiece un partido de eliminacion directa a su eleccion, y "),t("ese partido le multiplica x5 sus puntos",{bold:true}),t(". Es la herramienta de remontada mas potente: bien usado (semifinal o final), da un salto enorme.")]));
kids.push(box("Como se combinan","Regla propuesta: primero se suman los puntos del partido (H + I + items secundarios), luego se aplica el multiplicador de cruce (x2/x3), y por ultimo el comodin (x5). A calibrar con la Administracion: si el comodin en la final se siente demasiado fuerte, se puede limitar a que NO se combine con el x3 de sorpresa, o habilitarlo solo desde cuartos.",AMBARCLARO,AMBAR));

// 5. ITEMS SECUNDARIOS
kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("5. Items secundarios (regla \"el 0 no suma\")"));
kids.push(P([t("Estos items ya no regalan puntos por poner \"0\". "),t("Solo puntuan si hubo evento real (valor >= 1) y el apostador acerto el numero exacto",{bold:true}),t(", y ademas multiplican por cantidad y por rareza.")]));
kids.push(table([2600,2100,5140],[
  [cell("Item",{w:2600,head:true}),cell("Puntos base",{w:2100,head:true,align:AlignmentType.CENTER}),cell("Regla",{w:5140,head:true})],
  [cell("K - Tarjetas rojas",{w:2600}),cell("3 x cantidad",{w:2100,align:AlignmentType.CENTER,bold:true}),cell("Solo si hubo >=1 roja y acerto exacto. 2 rojas exactas = 6 pts; 4 rojas exactas = 12 pts (tu ejemplo).",{w:5140})],
  [cell("M - Penales en el juego",{w:2600,fill:CELLALT}),cell("3 x cantidad",{w:2100,align:AlignmentType.CENTER,bold:true,fill:CELLALT}),cell("Igual: solo con evento real y acierto exacto.",{w:5140,fill:CELLALT})],
  [cell("J - Tarjetas amarillas",{w:2600}),cell("2 (exacto)",{w:2100,align:AlignmentType.CENTER}),cell("Solo si hubo >=1 y acerto exacto. Al ser dificil, suma bonus por rareza.",{w:5140})],
  [cell("N - Minuto del 1er gol",{w:2600,fill:CELLALT}),cell("5 / 3 / 1",{w:2100,align:AlignmentType.CENTER,fill:CELLALT}),cell("5 al exacto, 3 si esta a +/-2 min, 1 si esta a +/-5 min.",{w:5140,fill:CELLALT})],
  [cell("O - Tanda de penales (por equipo)",{w:2600}),cell("5 c/u",{w:2100,align:AlignmentType.CENTER}),cell("Solo en llaves que se definen por penales. Dos items: local y visitante.",{w:5140})],
  [cell("NUEVO - Cantidad de cambios (reemplaza VAR)",{w:2600,fill:VERDECLARO}),cell("3 (exacto)",{w:2100,align:AlignmentType.CENTER,bold:true,color:AZUL,fill:VERDECLARO}),cell("Acertar el total de sustituciones del partido (hoy hasta 5 por equipo). Dato objetivo, facil de verificar y divertido. Suma bonus por rareza si pocos aciertan.",{w:5140,fill:VERDECLARO})],
]));
kids.push(SPACER());
kids.push(P([t("Bonus por rareza (\"contrarian\"): ",{bold:true}),t("en cualquiera de estos items, si menos del 15-20% de los apostadores acerto ese valor exacto, el puntaje se multiplica x2. Premia el acierto dificil que casi nadie tuvo.")]));

// 6. GLOBALES
kids.push(H1("6. Resultados globales: duplicar o triplicar su valor"));
kids.push(P([t("Los globales pasan de valer ~5% del torneo a ser un motor de remontada. Se "),t("duplican o triplican",{bold:true}),t(" y se agregan nuevos. Como se definen al final, permiten dar el golpe.")]));
kids.push(table([3200,1600,1600,3440],[
  [cell("Global",{w:3200,head:true}),cell("Actual",{w:1600,head:true,align:AlignmentType.CENTER}),cell("Propuesto",{w:1600,head:true,align:AlignmentType.CENTER}),cell("Nota",{w:3440,head:true})],
  [cell("A - Campeon",{w:3200}),cell("20",{w:1600,align:AlignmentType.CENTER}),cell("60",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("x3.",{w:3440})],
  [cell("B - Finalistas (c/u)",{w:3200,fill:CELLALT}),cell("10",{w:1600,align:AlignmentType.CENTER,fill:CELLALT}),cell("30",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE,fill:CELLALT}),cell("x3 (60 max).",{w:3440,fill:CELLALT})],
  [cell("C - Goleador",{w:3200}),cell("20",{w:1600,align:AlignmentType.CENTER}),cell("60",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("x3.",{w:3440})],
  [cell("D - Peor equipo",{w:3200,fill:CELLALT}),cell("20",{w:1600,align:AlignmentType.CENTER,fill:CELLALT}),cell("40",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE,fill:CELLALT}),cell("x2.",{w:3440,fill:CELLALT})],
  [cell("E - Mayor goleada",{w:3200}),cell("20",{w:1600,align:AlignmentType.CENTER}),cell("40",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("x2 (20+20).",{w:3440})],
  [cell("F/G - Etapa y goles Paraguay",{w:3200,fill:CELLALT}),cell("6 / 6",{w:1600,align:AlignmentType.CENTER,fill:CELLALT}),cell("18 / 18",{w:1600,align:AlignmentType.CENTER,bold:true,color:VERDE,fill:CELLALT}),cell("x3.",{w:3440,fill:CELLALT})],
  [cell("NUEVO - Equipo revelacion",{w:3200}),cell("-",{w:1600,align:AlignmentType.CENTER}),cell("30",{w:1600,align:AlignmentType.CENTER,bold:true,color:AZUL}),cell("Innovacion.",{w:3440,color:AZUL})],
  [cell("NUEVO - Jugador revelacion",{w:3200,fill:CELLALT}),cell("-",{w:1600,align:AlignmentType.CENTER,fill:CELLALT}),cell("30",{w:1600,align:AlignmentType.CENTER,bold:true,color:AZUL,fill:CELLALT}),cell("Innovacion.",{w:3440,color:AZUL,fill:CELLALT})],
]));
kids.push(SPACER());
kids.push(P([t("Ademas, "),t("bonus por rareza en globales",{bold:true}),t(": si pocos acertaron (ej. campeon sorpresa), ese global vale x2. Es la mejor via de remontada para los de abajo.")]));

// 7. INNOVACIONES
kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("7. Innovaciones estandar (lo que usa la mayoria)"));
kids.push(P("Mecanicas comunes en las ligas de pronosticos y \"pools\" deportivos que conviene incorporar:"));
kids.push(bullet([t("Comodin / doble-o-nada (x5): ",{bold:true}),t("ya descrito. Es la mecanica de comeback mas usada.")]));
kids.push(bullet([t("Puntos de confianza: ",{bold:true}),t("en cada fase el apostador reparte un presupuesto de fichas entre sus pronosticos; acertar donde puso mas fichas rinde mas. Agrega estrategia.")]));
kids.push(bullet([t("Bonus por rareza / contrarian: ",{bold:true}),t("acertar lo que casi nadie acerto multiplica. Transversal a partidos y globales.")]));
kids.push(bullet([t("Racha (streak): ",{bold:true}),t("3 resultados acertados seguidos dan un bonus (ej. +10). Premia la regularidad.")]));
kids.push(bullet([t("Survivor paralelo: ",{bold:true}),t("juego secundario de eliminacion (cada ronda elegis un ganador sin repetir; si pierde, quedas fuera) con premio propio. Mantiene enganchado al eliminado del ranking.")]));
kids.push(bullet([t("Props por partido: ",{bold:true}),t("autogol si/no, penal fallado si/no, figura del partido (MVP). Divierten y no exigen pericia tecnica.")]));

// 8. EJEMPLOS
kids.push(H1("8. Ejemplos trabajados (con numeros)"));
kids.push(H3("Ejemplo 1 - El acierto sonado (final)"));
kids.push(P([t("El apostador acerta el marcador exacto de la final (Espana 1-0):")]));
kids.push(bullet([t("H (resultado) 50 + I (marcador exacto) 100 = "),t("150 pts",{bold:true})]));
kids.push(bullet([t("Acerto ademas que Espana pasaba la llave (cruce, x2) -> "),t("300 pts",{bold:true,color:VERDE})]));
kids.push(bullet([t("Si habia jugado su comodin en la final (x5) -> "),t("1.500 pts",{bold:true,color:ROJO}),t(" (por eso el comodin decide torneos).")]));

kids.push(H3("Ejemplo 2 - La sorpresa tipo Paraguay (16avos)"));
kids.push(P([t("El apostador se anima a poner que Paraguay elimina a Alemania, y acierta:")]));
kids.push(bullet([t("Puntaje del partido (ej. H 4 + I 8) = 12, con marcador exacto.")]));
kids.push(bullet([t("Cruce SORPRESA (x3) -> "),t("36 pts",{bold:true,color:ROJO}),t(" por un partido de 16avos. El que no se animo, saca 12 o menos.")]));

kids.push(H3("Ejemplo 3 - La remontada (entra a semis 180 pts abajo)"));
kids.push(P([t("Un apostador va 180 pts detras del lider al empezar semifinales. Juega agresivo:")]));
kids.push(bullet([t("Semifinal A: marcador exacto (H30 + I60 = 90), acerto el cruce (x2) = 180, y uso su comodin (x5) -> "),t("900 pts",{bold:true,color:ROJO})]));
kids.push(bullet([t("Semifinal B: acerto el resultado (H30), cruce (x2) = "),t("60 pts",{bold:true})]));
kids.push(bullet([t("Total semis ~ 960 pts. El lider, conservador y sin comodin, saca ~200. "),t("Remontada consumada.",{bold:true,color:VERDE})]));
kids.push(P([t("Con el modelo viejo, una semifinal exacta valia 24 pts: remontar 180 era imposible. Con el nuevo, es posible con aciertos de merito.",{italics:true,color:GRIS})]));

kids.push(H3("Ejemplo 4 - Los globales al cierre"));
kids.push(P([t("Al terminar el torneo, un apostador de abajo acerta el paquete global:")]));
kids.push(bullet([t("Campeon 60 (y como fue sorpresa, bonus rareza x2 = 120) + Goleador 60 + un Finalista 30 = "),t("210 pts",{bold:true,color:VERDE}),t(" de un saque.")]));

// 9. DISTRIBUCION OBJETIVO
kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("9. Distribucion objetivo de puntos"));
kids.push(P("Con estos valores, el peso del torneo se corre del grupo al playoff. Meta de diseno:"));
kids.push(table([3400,2200,4240],[
  [cell("Bloque",{w:3400,head:true}),cell("Peso objetivo",{w:2200,head:true,align:AlignmentType.CENTER}),cell("Hoy (referencia)",{w:4240,head:true})],
  [cell("Fase de grupos",{w:3400}),cell("< 12%",{w:2200,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("~50% (el problema actual)",{w:4240,color:ROJO})],
  [cell("Playoffs (16avos a final)",{w:3400,fill:CELLALT}),cell("~75%",{w:2200,align:AlignmentType.CENTER,bold:true,color:VERDE,fill:CELLALT}),cell("~45%",{w:4240,fill:CELLALT})],
  [cell("Globales",{w:3400}),cell("~13%",{w:2200,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("~5%",{w:4240})],
]));
kids.push(SPACER());
kids.push(P([t("Efecto directo: al terminar la fase de grupos, la diferencia entre el 1o y el ultimo sera de pocas decenas de puntos (no cientos). "),t("El torneo arranca de verdad en los playoffs.",{bold:true})]));

// 10. PARAMETROS A DECIDIR
kids.push(H1("10. Parametros a calibrar con la Administracion"));
kids.push(table([600,6800,1800],[
  [cell("#",{w:600,head:true,align:AlignmentType.CENTER}),cell("Decision / parametro",{w:6800,head:true}),cell("Propuesta",{w:1800,head:true,align:AlignmentType.CENTER})],
  [cell("1",{w:600,align:AlignmentType.CENTER}),cell("Reemplazar VAR por \"cantidad de cambios\"; eliminar el item \"equipo que clasifica\"",{w:6800}),cell("Si",{w:1800,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("2",{w:600,align:AlignmentType.CENTER,fill:CELLALT}),cell("Puntajes H/I por fase (grupos 2/4 ... final 50/100)",{w:6800,fill:CELLALT}),cell("Aprobar",{w:1800,align:AlignmentType.CENTER,color:VERDE,bold:true,fill:CELLALT})],
  [cell("3",{w:600,align:AlignmentType.CENTER}),cell("Multiplicador por cruce: x2 favorito, x3 sorpresa",{w:6800}),cell("Aprobar",{w:1800,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("4",{w:600,align:AlignmentType.CENTER,fill:CELLALT}),cell("Comodin x5 (1 por playoff). Combina con el cruce?",{w:6800,fill:CELLALT}),cell("Definir",{w:1800,align:AlignmentType.CENTER,color:AMBAR,bold:true,fill:CELLALT})],
  [cell("5",{w:600,align:AlignmentType.CENTER}),cell("Items secundarios: 0 no suma + multiplicar por cantidad",{w:6800}),cell("Si",{w:1800,align:AlignmentType.CENTER,color:VERDE,bold:true})],
  [cell("6",{w:600,align:AlignmentType.CENTER,fill:CELLALT}),cell("Globales x2/x3 + nuevos (revelacion) + bonus rareza",{w:6800,fill:CELLALT}),cell("Aprobar",{w:1800,align:AlignmentType.CENTER,color:VERDE,bold:true,fill:CELLALT})],
  [cell("7",{w:600,align:AlignmentType.CENTER}),cell("Innovaciones: confianza, racha, survivor, props",{w:6800}),cell("Elegir",{w:1800,align:AlignmentType.CENTER,color:AMBAR,bold:true})],
  [cell("8",{w:600,align:AlignmentType.CENTER,fill:CELLALT}),cell("Definir el criterio favorito/sorpresa (ranking FIFA o sembrado)",{w:6800,fill:CELLALT}),cell("Definir",{w:1800,align:AlignmentType.CENTER,color:AMBAR,bold:true,fill:CELLALT})],
]));

// 11. MEJORAS FUNCIONALES
kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("11. Mejoras funcionales de BECBUC (producto)"));
kids.push(P("Ademas del rediseno de puntajes, proponemos mejoras de producto que hacen a BECBUC mas flexible, atractivo y ordenado:"));

kids.push(H2("11.1. Torneos que arrancan directo en playoff (sin grupos)"));
kids.push(P([t("Soportar torneos "),t("sin fase de grupos",{bold:true}),t(", que arrancan en eliminacion directa - como la Copa Libertadores / Sudamericana en sus fases finales, o cualquier playoff. El sistema ya trabaja por fases configurables: alcanza con habilitar o deshabilitar la fase de grupos por torneo. Encaja perfecto con el modelo nuevo, donde los grupos casi no pesan.")]));

kids.push(H2("11.2. Apostadores gratis vs. suscriptores"));
kids.push(P([t("Permitir que jueguen "),t("apostadores gratis",{bold:true}),t(": participan del ranking y compiten por el "),t("orgullo",{bold:true}),t(", pero "),t("no acceden a premios en dinero",{bold:true}),t(". Cada apostador tiene un estado: SUSCRIPTOR (pago, elegible a premios) o LIBRE (gratis, solo ranking).")]));
kids.push(bullet([t("El ranking general muestra a todos; una marca distingue a los gratis.")]));
kids.push(bullet([t("El reparto de premios solo considera a los suscriptores: si un gratis sale 1o, el premio va al mejor suscriptor y el gratis figura como \"campeon de honor\".")]));
kids.push(bullet([t("Requiere registrar quien pago la suscripcion (campo de estado + fecha de pago).")]));

kids.push(H2("11.3. Notificaciones por correo"));
kids.push(bullet([t("Recordatorio para apostar a tiempo: ",{bold:true}),t("aviso automatico antes del cierre de cada fase a quienes no completaron su boleta.")]));
kids.push(bullet([t("Ranking por correo: ",{bold:true}),t("envio del ranking actualizado tras cada fase, con el ganador de la fase.")]));
kids.push(bullet([t("Requiere correo verificado por apostador y una plantilla simple de email.")]));

kids.push(H2("11.4. Libro de actas (quejas y reclamos)"));
kids.push(P([t("Un registro formal donde los apostadores dejan quejas, reclamos o consultas, con estado (abierto / en revision / resuelto) y respuesta de la Administracion. Da transparencia, evita discusiones informales y queda como historial del torneo.")]));

kids.push(H2("11.5. Minitorneo: premio por ganador de cada fase de playoff"));
kids.push(P([t("Ademas del premio al campeon general (el que mas suma, como siempre), se reparte "),t("un % del pozo al mayor puntaje de cada fase de playoff",{bold:true}),t(". Mantiene la emocion fase a fase y le da chances a mas gente.")]));
kids.push(P("Ejemplo de reparto del pozo (a calibrar):"));
kids.push(table([5200,2200,2440],[
  [cell("Premio",{w:5200,head:true}),cell("% del pozo",{w:2200,head:true,align:AlignmentType.CENTER}),cell("Tipo",{w:2440,head:true,align:AlignmentType.CENTER})],
  [cell("Campeon general (mayor puntaje acumulado)",{w:5200,bold:true}),cell("45%",{w:2200,align:AlignmentType.CENTER,bold:true,color:VERDE}),cell("Principal",{w:2440,align:AlignmentType.CENTER})],
  [cell("2o general",{w:5200,fill:CELLALT}),cell("12%",{w:2200,align:AlignmentType.CENTER,fill:CELLALT}),cell("Principal",{w:2440,align:AlignmentType.CENTER,fill:CELLALT})],
  [cell("3o general",{w:5200}),cell("8%",{w:2200,align:AlignmentType.CENTER}),cell("Principal",{w:2440,align:AlignmentType.CENTER})],
  [cell("Mejor puntaje 16avos",{w:5200,fill:CELLALT}),cell("4%",{w:2200,align:AlignmentType.CENTER,fill:CELLALT}),cell("Por fase",{w:2440,align:AlignmentType.CENTER,fill:CELLALT})],
  [cell("Mejor puntaje Octavos",{w:5200}),cell("5%",{w:2200,align:AlignmentType.CENTER}),cell("Por fase",{w:2440,align:AlignmentType.CENTER})],
  [cell("Mejor puntaje Cuartos",{w:5200,fill:CELLALT}),cell("6%",{w:2200,align:AlignmentType.CENTER,fill:CELLALT}),cell("Por fase",{w:2440,align:AlignmentType.CENTER,fill:CELLALT})],
  [cell("Mejor puntaje Semifinal",{w:5200}),cell("7%",{w:2200,align:AlignmentType.CENTER}),cell("Por fase",{w:2440,align:AlignmentType.CENTER})],
  [cell("Mejor puntaje Final",{w:5200,fill:CELLALT}),cell("8%",{w:2200,align:AlignmentType.CENTER,fill:CELLALT}),cell("Por fase",{w:2440,align:AlignmentType.CENTER,fill:CELLALT})],
  [cell("Survivor paralelo",{w:5200}),cell("5%",{w:2200,align:AlignmentType.CENTER}),cell("Secundario",{w:2440,align:AlignmentType.CENTER})],
]));
kids.push(SPACER());
kids.push(P([t("Total 100%. El "),t("ganador general sigue siendo el que mas puntos acumula en todo el torneo",{bold:true}),t("; los premios por fase son adicionales y menores. Los porcentajes son un ejemplo para calibrar.")]));

kids.push(H2("11.6. Dos (o mas) torneos en paralelo"));
kids.push(P([t("Poder correr "),t("varios torneos al mismo tiempo",{bold:true}),t(" (por ejemplo Libertadores y Sudamericana). En el Live, el apostador "),t("elige el torneo que quiere ver",{bold:true}),t(" y visualiza todo lo de ese torneo (bracket, ranking, sus apuestas, en vivo). Cada torneo puede tener "),t("su propio reglamento",{bold:true}),t(": separado o compartido, segun lo defina el Comite de Apuestas. El sistema ya identifica cada torneo con su id y su motor por competencia, asi que soportar varios en paralelo es natural.")]));
kids.push(bullet([t("Selector de torneo en el Live y en el portal (Libertadores / Sudamericana / Mundial ...).")]));
kids.push(bullet([t("Ranking, premios y libro de actas independientes por torneo.")]));
kids.push(bullet([t("Reglamento por torneo: se elige compartir el mismo o usar uno propio.")]));

kids.push(H2("11.7. Interfaz para definir y modificar los puntajes"));
kids.push(P([t("Un panel de administracion donde el Comite "),t("define y modifica el puntaje de cada apuesta por fase",{bold:true}),t(" (H resultado, I marcador, tarjetas, penales, cambios, minuto, tanda, multiplicador de cruce, comodin) y tambien los "),t("globales",{bold:true}),t(", por torneo - todo "),t("editable desde la pantalla, sin tocar codigo",{bold:true}),t(".")]));
kids.push(bullet([t("Tabla editable puntaje x fase; se guarda y el motor la toma en el proximo calculo.")]));
kids.push(bullet([t("Permite calibrar el modelo entre torneos y probar variantes (ej. subir el peso de la final).")]));
kids.push(bullet([t("Historial de cambios de reglamento para auditoria (quien cambio que y cuando).")]));

kids.push(new Paragraph({children:[new PageBreak()]}));
kids.push(H1("12. Implementacion (sin tocar lo actual)"));
kids.push(P([t("El motor de puntajes ya es por competencia (patron Strategy). Se crea un engine nuevo ("),t("copa_playoff_2027",{italics:true}),t(") con estas reglas y se estrena en un torneo de prueba, sin afectar el torneo ya cerrado.")]));
kids.push(bullet([t("Migracion BD: comodin, fichas de confianza, props, marca de cruce, estado de suscripcion (pago/gratis) y libro de actas.")],"nl"));
kids.push(bullet([t("Engine v3 parametrizable: puntajes por fase, multiplicador de cruce (x2/x3), comodin (x5), rareza, globales potenciados; fase de grupos opcional (torneos solo-playoff).")],"nl"));
kids.push(bullet([t("Boleta portal + movil: declarar comodin, cruces, fichas de confianza y props.")],"nl"));
kids.push(bullet([t("Notificaciones por correo, ranking por fase y reparto de premios (solo suscriptores).")],"nl"));
kids.push(bullet([t("Piloto en un playoff chico: medir la nueva distribucion (grupos <12%) y ajustar los valores antes del proximo Mundial.")],"nl"));
kids.push(SPACER());
kids.push(P([t("Si la Administracion aprueba estos lineamientos, se congelan los valores exactos y se arranca la implementacion tecnica para el proximo torneo playoff.",{italics:true})]));

const doc=new Document({
  creator:"BECBUC",title:"BECBUC 2.0 - Modelo Detallado de Puntajes",
  numbering:{config:[
    {reference:"bl",levels:[
      {level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:520,hanging:260}}}},
      {level:1,format:LevelFormat.BULLET,text:"–",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:1000,hanging:260}}}},
    ]},
    {reference:"nl",levels:[
      {level:0,format:LevelFormat.DECIMAL,text:"%1.",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:520,hanging:260}}}},
    ]},
  ]},
  styles:{default:{document:{run:{font:"Calibri",size:21}}}},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1100,bottom:1100,left:1200,right:1200}}},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,
      children:[new TextRun({text:"BECBUC 2.0 - Modelo detallado de puntajes - ",size:16,color:GRIS}),
                new TextRun({children:["Pag. ",PageNumber.CURRENT],size:16,color:GRIS})]})]})},
    children:kids
  }]
});
Packer.toBuffer(doc).then(buf=>{fs.writeFileSync(process.argv[2]||"out.docx",buf);console.log("OK docx bytes:",buf.length);});
