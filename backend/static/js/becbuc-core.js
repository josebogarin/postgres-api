// becbuc-core.js - Nucleo compartido de las superficies BECBUC (Fase 4).
// Componente 1: banderas por codigo ISO / nombre de equipo.
// Cargar con <script src="/static/js/becbuc-core.js"></script> ANTES del <script> principal.

const ISO_MAP = {
  'argentina':'AR','brazil':'BR','brasil':'BR','colombia':'CO','ecuador':'EC',
  'uruguay':'UY','paraguay':'PY','chile':'CL','bolivia':'BO','peru':'PE','perú':'PE','venezuela':'VE',
  'spain':'ES','españa':'ES','france':'FR','francia':'FR','germany':'DE','alemania':'DE',
  'portugal':'PT','netherlands':'NL','países bajos':'NL','italy':'IT','italia':'IT',
  'belgium':'BE','bélgica':'BE','croatia':'HR','croacia':'HR','switzerland':'CH','suiza':'CH',
  'austria':'AT','denmark':'DK','dinamarca':'DK','serbia':'RS','turkey':'TR','türkiye':'TR',
  'turquía':'TR','czechia':'CZ','ukraine':'UA','ucrania':'UA','poland':'PL','polonia':'PL',
  'hungary':'HU','hungría':'HU','romania':'RO','rumania':'RO','norway':'NO','noruega':'NO',
  'sweden':'SE','suecia':'SE','finland':'FI','iceland':'IS','islandia':'IS','russia':'RU',
  'united states':'US','usa':'US','estados unidos':'US','mexico':'MX','méxico':'MX',
  'canada':'CA','canadá':'CA','honduras':'HN','panama':'PA','panamá':'PA',
  'costa rica':'CR','jamaica':'JM','haiti':'HT','haití':'HT','el salvador':'SV',
  'japan':'JP','japón':'JP','south korea':'KR','corea del sur':'KR','australia':'AU',
  'saudi arabia':'SA','arabia saudita':'SA','iran':'IR','qatar':'QA','iraq':'IQ',
  'morocco':'MA','marruecos':'MA','senegal':'SN','egypt':'EG','egipto':'EG',
  'nigeria':'NG','south africa':'ZA','sudáfrica':'ZA','cameroon':'CM','camerún':'CM',
  'ghana':'GH','tunisia':'TN','túnez':'TN','algeria':'DZ','argelia':'DZ',
  'new zealand':'NZ','nueva zelanda':'NZ',
  'congo':'CG','congo dr':'CD','dr congo':'CD','republic of congo':'CG','democratic republic of congo':'CD',
  'ivory coast':'CI','côte d\'ivoire':'CI','costa de marfil':'CI','cape verde':'CV',
  'trinidad and tobago':'TT','trinidad tobago':'TT','trinidad y tobago':'TT',
  'united arab emirates':'AE','uae':'AE','zimbabwe':'ZW','zambia':'ZM',
  'namibia':'NA','mozambique':'MZ','angola':'AO','tanzania':'TZ','rwanda':'RW',
  'kenya':'KE','ethiopia':'ET','libya':'LY','mali':'ML','burkina faso':'BF',
  'guinea':'GN','guinea-bissau':'GW','sierra leone':'SL','liberia':'LR',
  'togo':'TG','benin':'BJ','gabon':'GA','central african republic':'CF',
  'equatorial guinea':'GQ','guinea ecuatorial':'GQ','comoros':'KM','djibouti':'DJ',
  'eritrea':'ER','somalia':'SO','sudan':'SD','south sudan':'SS','chad':'TD',
  'niger':'NE','mauritania':'MR','western sahara':'EH','palestine':'PS',
  'lebanon':'LB','syria':'SY','jordan':'JO','kuwait':'KW','bahrain':'BH',
  'oman':'OM','yemen':'YE','armenia':'AM','georgia':'GE','azerbaijan':'AZ',
  'uzbekistan':'UZ','kazakhstan':'KZ','kyrgyzstan':'KG','tajikistan':'TJ',
  'turkmenistan':'TM','afghanistan':'AF','pakistan':'PK','bangladesh':'BD',
  'sri lanka':'LK','nepal':'NP','myanmar':'MM','cambodia':'KH','laos':'LA',
  'mongolia':'MN','north korea':'KP','taiwan':'TW','singapore':'SG','malaysia':'MY',
  'indonesia':'ID','philippines':'PH','vietnam':'VN','thailand':'TH','india':'IN',
  'china':'CN','hong kong':'HK','macau':'MO','timor-leste':'TL',
  'cuba':'CU','haiti':'HT','haití':'HT','jamaica':'JM','dominican republic':'DO',
  'trinidad':'TT','curacao':'CW','curaçao':'CW','barbados':'BB','bahamas':'BS',
  'guyana':'GY','suriname':'SR','bolivia':'BO','paraguay':'PY',
  'puerto rico':'PR','saint lucia':'LC','grenada':'GD','antigua':'AG',
  'albania':'AL','bosnia':'BA','bosnia and herzegovina':'BA','north macedonia':'MK',
  'montenegro':'ME','moldova':'MD','slovakia':'SK','eslovaquia':'SK','slovenia':'SI','eslovenia':'SI',
  'estonia':'EE','latvia':'LV','lithuania':'LT','greece':'GR','grecia':'GR',
  'cyprus':'CY','israel':'IL','malta':'MT','luxembourg':'LU','liechtenstein':'LI',
  'andorra':'AD','monaco':'MC','san marino':'SM','sweden':'SE','suecia':'SE',
  'ireland':'IE','irlanda':'IE','northern ireland':'GB-NIR',
};
const SPECIAL = { 'england':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','scotland':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','wales':'🏴󠁧󠁢󠁷󠁬󠁳󠁿','gales':'🏴󠁧󠁢󠁷󠁬󠁳󠁿' };

function isoFlag(code) {
  return code.toUpperCase().replace(/./g, c => String.fromCodePoint(127397 + c.charCodeAt(0)));
}
function flag(iso, nombre) {
  if (iso && iso.length === 2) return isoFlag(iso);
  const k = (nombre || '').toLowerCase().trim();
  if (SPECIAL[k]) return SPECIAL[k];
  const m = ISO_MAP[k];
  return m ? isoFlag(m) : '🏳';
}
