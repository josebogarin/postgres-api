import type { RankingRow } from "@/lib/types";

// Etiquetas y orden de las fases KO (unificado, sesión 69).
export const FASE_LABEL: Record<string, string> = {
  ronda32: "16avos",
  ronda16: "Octavos",
  cuartos: "Cuartos",
  semis: "Semifinal",
  tercer_puesto: "3er puesto",
  tercero: "3er puesto",
  final: "Final",
};
export const FASE_ORDER = [
  "ronda32",
  "ronda16",
  "cuartos",
  "semis",
  "tercer_puesto",
  "tercero",
  "final",
];

export function faseLabel(tipo: string | null | undefined): string {
  if (!tipo) return "";
  return FASE_LABEL[tipo] ?? tipo;
}

// ISO (UTC, con Z) -> hora local del dispositivo.
export function fmtFecha(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  // Siempre hora de Paraguay (America/Asuncion), sin importar el dispositivo.
  return d.toLocaleString("es", {
    timeZone: "America/Asuncion",
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Ítems de puntuación (iconos + label completo, igual que el live actual).
export const ITEMS: { key: keyof RankingRow; icon: string; label: string }[] = [
  { key: "cat_resultado", icon: "⚽", label: "Resultado" },
  { key: "cat_marcador", icon: "🎯", label: "Marcador exacto" },
  { key: "cat_amarillas", icon: "🟨", label: "Amarillas" },
  { key: "cat_rojas", icon: "🟥", label: "Rojas" },
  { key: "cat_sustituciones", icon: "🔄", label: "Cambios" },
  { key: "cat_penales_partido", icon: "🥅", label: "Penales (juego)" },
  { key: "cat_minuto", icon: "⏱", label: "Minuto gol" },
  { key: "cat_penales_tanda", icon: "⚡", label: "Tanda penales" },
  { key: "cat_equipo", icon: "🏳️", label: "Equipo clasifica" },
];

export function alias(r: RankingRow): string {
  return r.apostador || r.username || r.nombre || "?";
}
