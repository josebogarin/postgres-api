// Tipos de dominio BECBUC (contra las respuestas reales de la API).

export const TORNEO_ID = 2;

export interface TorneoCerrado {
  cerrado: boolean;
}

// ---- Bracket real (GET /bets/bracket-real/{tid}) ----
export interface Team {
  id: number;
  nombre: string;
  logo_url: string | null;
  iso: string;
}

export interface BracketMatch {
  num: number;
  tipo: string; // ronda32 | ronda16 | cuartos | semis | tercer_puesto | final
  finalizado: boolean;
  en_vivo: boolean;
  ganador: "local" | "visitante" | null;
  gl: number | null;
  gv: number | null;
  pen_l: number | null;
  pen_v: number | null;
  fecha: string | null; // ISO con Z
  provisional: boolean;
  local: Team | null;
  visitante: Team | null;
  sede: string | null;
  ciudad: string | null;
}

export interface BracketResponse {
  partidos: BracketMatch[];
}

// ---- Ranking (GET /bets/ranking/{tid}) -> array ----
// ---- Apostadores (GET /bets/apostadores) ----
export interface Apostador {
  id: number;
  username: string;
  alias: string;
}

// ---- Mis partidos (GET /bets/mis-partidos/{tid}?for_apostador_id=) ----
export interface MisPartidoRow {
  numero_fifa: number;
  fase_tipo: string;
  fase_nombre: string;
  fase_orden: number;
  estado: string;
  fecha: string | null;
  goles_local: number | null;
  goles_visitante: number | null;
  amarillas: number | null;
  rojas: number | null;
  decisiones_var: number | null;
  minuto_primer_gol: number | null;
  penales_local: number | null;
  penales_visitante: number | null;
  penales_partido: number | null;
  local_id: number | null;
  visit_id: number | null;
  local_nombre: string;
  visit_nombre: string;
  local_logo: string | null;
  visit_logo: string | null;
  equipo_clasificado_id: number | null;
  pred_equipo_clasifica: number | null;
  pred_local: number | null;
  pred_visitante: number | null;
  pred_amarillas: number | null;
  pred_rojas: number | null;
  pred_var: number | null;
  pred_penales_partido: number | null;
  pred_minuto_gol: number | null;
  pred_penales_local_tanda: number | null;
  pred_penales_visitante_tanda: number | null;
  pts_resultado: number | null;
  pts_marcador: number | null;
  pts_amarillas: number | null;
  pts_rojas: number | null;
  pts_var: number | null;
  pts_penales_partido: number | null;
  pts_minuto: number | null;
  pts_penales_tanda: number | null;
  pts_equipo: number | null;
  pts_total: number | null;
}

// ---- En Vivo (GET /bets/live-panel/{tid}) ----
export interface LiveEvent {
  time?: { elapsed?: number | null; extra?: number | null };
  team?: { id?: number; name?: string; logo?: string };
  player?: { id?: number; name?: string };
  assist?: { id?: number; name?: string }; // en subst: jugador que sale
  type?: string; // Goal | Card | subst | Var
  detail?: string;
}
export interface LivePartido {
  id: number;
  numero_fifa: number;
  equipo_local: string;
  equipo_visitante: string;
  bandera_local: string | null;
  bandera_visitante: string | null;
  logo_local: string | null;
  logo_visitante: string | null;
  goles_local: number | null;
  goles_visitante: number | null;
  estado: string;
  fecha: string | null;
  minuto_actual: number | null;
  minuto_primer_gol: number | null;
  amarillas: number;
  rojas: number;
  decisiones_var: number;
  penales_partido: number | null;
  penales_tanda_local: number | null;
  penales_tanda_visitante: number | null;
  equipo_clasificado_id: number | null;
  local_api_team_id: number | null;
  visita_api_team_id: number | null;
  fase_nombre: string;
  fase_tipo: string;
  es_paraguay: boolean;
  eventos_api: LiveEvent[];
}
export interface LivePanelResponse {
  partido: LivePartido | null;
  numeros_fifa?: number[];
}

export interface RankingRow {
  apostador_id: number;
  nombre?: string; // alias/username
  apostador?: string;
  username?: string;
  puntos_total: number;
  puntos_partidos_total?: number;
  pts_globales?: number;
  pts_grupos_p?: number;
  plenos?: number;
  aciertos?: number;
  fallos?: number;
  online_source?: string | null;
  cat_resultado?: number;
  cat_marcador?: number;
  cat_amarillas?: number;
  cat_rojas?: number;
  cat_var?: number;
  cat_minuto?: number;
  cat_penales_partido?: number;
  cat_penales_tanda?: number;
  cat_equipo?: number;
  fases?: { tipo: string; nombre: string; pts: number }[];
}
