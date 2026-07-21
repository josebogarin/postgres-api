"use client";

import type { BracketMatch, Team } from "@/lib/types";
import { fmtFecha } from "@/lib/format";
import PanZoom from "@/components/PanZoom";

// Layout idéntico al árbol actual (becbuc-live-playoffs.html).
const S = 136,
  CW = 128,
  CH = 68,
  GAP = 28,
  PAD_L = 14,
  PAD_T = 30;
const CP = CW + GAP; // 156
const totalH = 8 * S + PAD_T + 30;
const totalW = 9 * CP + PAD_L * 2;

const colX = (c: number) => PAD_L + c * CP;
const yCenter = (L: number, n: number) => PAD_T + Math.pow(2, L) * (n + 0.5) * S;
const yTop = (L: number, n: number) => yCenter(L, n) - CH / 2;

// Agrupación por KO_FEEDERS (izq → P101, der → P102).
const LEFT = [
  [74, 77, 73, 75, 83, 84, 81, 82],
  [89, 90, 93, 94],
  [97, 98],
  [101],
];
const RIGHT = [
  [76, 78, 79, 80, 86, 88, 85, 87],
  [91, 92, 95, 96],
  [99, 100],
  [102],
];

type Pos = { col: number; yc: number; yt: number };
const POS: Record<number, Pos> = {};
LEFT.forEach((nums, L) =>
  nums.forEach((n, i) => (POS[n] = { col: L, yc: yCenter(L, i), yt: yTop(L, i) }))
);
RIGHT.forEach((nums, L) =>
  nums.forEach((n, i) => (POS[n] = { col: 8 - L, yc: yCenter(L, i), yt: yTop(L, i) }))
);
POS[104] = { col: 4, yc: yCenter(3, 0), yt: yTop(3, 0) }; // Final
POS[103] = { col: 4, yc: yCenter(3, 0) + S * 2.5, yt: yTop(3, 0) + S * 2.5 }; // 3er puesto

const LABELS = [
  "16avos",
  "Octavos",
  "Cuartos",
  "Semifinal",
  "FINAL",
  "Semifinal",
  "Cuartos",
  "Octavos",
  "16avos",
];

const rx = (n: number) => colX(POS[n].col) + CW;
const lx = (n: number) => colX(POS[n].col);
const cy = (n: number) => POS[n].yc;

type Line = { x1: number; y1: number; x2: number; y2: number };
function buildLines(): Line[] {
  const L: Line[] = [];
  const seg = (x1: number, y1: number, x2: number, y2: number) => L.push({ x1, y1, x2, y2 });
  const pairR = (s1: number, s2: number, dst: number) => {
    if (!POS[s1] || !POS[s2] || !POS[dst]) return;
    const x1 = rx(s1), y1 = cy(s1), x2 = rx(s2), y2 = cy(s2), xd = lx(dst), yd = cy(dst);
    const mx = (x1 + xd) / 2;
    seg(x1, y1, mx, y1); seg(x2, y2, mx, y2); seg(mx, y1, mx, y2); seg(mx, yd, xd, yd);
  };
  const pairL = (s1: number, s2: number, dst: number) => {
    if (!POS[s1] || !POS[s2] || !POS[dst]) return;
    const x1 = lx(s1), y1 = cy(s1), x2 = lx(s2), y2 = cy(s2), xd = rx(dst), yd = cy(dst);
    const mx = (x1 + xd) / 2;
    seg(x1, y1, mx, y1); seg(x2, y2, mx, y2); seg(mx, y1, mx, y2); seg(mx, yd, xd, yd);
  };
  const single = (src: number, dst: number, fromRight: boolean) => {
    if (!POS[src] || !POS[dst]) return;
    seg(fromRight ? rx(src) : lx(src), cy(src), fromRight ? lx(dst) : rx(dst), cy(dst));
  };
  pairR(74, 77, 89); pairR(73, 75, 90); pairR(83, 84, 93); pairR(81, 82, 94);
  pairR(89, 90, 97); pairR(93, 94, 98); pairR(97, 98, 101); single(101, 104, true);
  pairL(76, 78, 91); pairL(79, 80, 92); pairL(86, 88, 95); pairL(85, 87, 96);
  pairL(91, 92, 99); pairL(95, 96, 100); pairL(99, 100, 102); single(102, 104, false);
  return L;
}
const LINES = buildLines();

// Próximo partido a jugarse: el no-finalizado (con equipos reales) de fecha más
// cercana. Se usa para el badge "⏭ PRÓXIMO" cuando no hay ninguno en vivo.
function nextMatchNum(ps: BracketMatch[]): number | null {
  const cand = ps.filter(
    (p) => !p.finalizado && !p.en_vivo && p.fecha && (p.local || p.visitante)
  );
  if (!cand.length) return null;
  cand.sort((a, b) => (a.fecha! < b.fecha! ? -1 : 1));
  return cand[0].num;
}

export default function BracketTree({
  partidos,
  onSelectMatch,
}: {
  partidos: BracketMatch[];
  onSelectMatch?: (num: number) => void;
}) {
  const byNum: Record<number, BracketMatch> = {};
  for (const m of partidos) byNum[m.num] = m;
  const liveNum = partidos.find((p) => p.en_vivo)?.num ?? null;
  const nextNum = liveNum ? null : nextMatchNum(partidos);

  return (
    <div>
      <p className="mb-2 text-center text-[11px] text-muted">
        Arrastrá para moverte · pellizcá (o ＋／−) para zoom
      </p>
      <PanZoom contentW={totalW} contentH={totalH} focusX={colX(4) + CW / 2}>
        <div style={{ position: "relative", width: totalW, height: totalH }}>
          <svg
            style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
            width={totalW}
            height={totalH}
          >
            {LINES.map((l, i) => (
              <line
                key={i}
                x1={l.x1}
                y1={l.y1}
                x2={l.x2}
                y2={l.y2}
                stroke="#1e2850"
                strokeWidth={1.5}
                strokeLinecap="round"
              />
            ))}
          </svg>

          {LABELS.map((t, c) => (
            <div
              key={c}
              style={{ position: "absolute", left: colX(c), width: CW, top: 8 }}
              className="text-center text-[10px] font-bold uppercase tracking-wide text-[#5a6690]"
            >
              {t}
            </div>
          ))}

          <div
            style={{ position: "absolute", left: colX(4) + CW / 2 - 12, top: POS[104].yt - 26 }}
            className="text-2xl"
          >
            🏆
          </div>
          <div
            style={{ position: "absolute", left: colX(4), width: CW, top: POS[103].yt - 14 }}
            className="text-center text-[10px] font-bold text-[#5a6690]"
          >
            3er Puesto
          </div>

          {Object.keys(POS).map((k) => {
            const num = Number(k);
            return (
              <Card
                key={num}
                num={num}
                pos={POS[num]}
                m={byNum[num]}
                badge={num === liveNum ? "live" : num === nextNum ? "next" : null}
                onSelect={onSelectMatch}
              />
            );
          })}
        </div>
      </PanZoom>
    </div>
  );
}

function Card({
  num,
  pos,
  m,
  badge,
  onSelect,
}: {
  num: number;
  pos: Pos;
  m?: BracketMatch;
  badge?: "live" | "next" | null;
  onSelect?: (num: number) => void;
}) {
  const tbd = !m || (!m.local && !m.visitante);
  const border = m?.en_vivo ? "#ef4444" : m?.finalizado ? "#1a2d1a" : "#1a2550";
  const clickable = !!m && !!onSelect;
  return (
    <div
      style={{ position: "absolute", left: colX(pos.col), top: pos.yt, width: CW }}
      className="text-[11px]"
    >
      {badge && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: -10,
            transform: "translateX(-50%)",
            zIndex: 10,
            whiteSpace: "nowrap",
            background: badge === "live" ? "#ef4444" : "#3b82f6",
          }}
          className="rounded px-1.5 py-0.5 text-[8px] font-bold text-white"
        >
          {badge === "live" ? "🔴 EN VIVO" : "⏭ PRÓXIMO"}
        </div>
      )}
      <div
        onClick={clickable ? () => onSelect!(num) : undefined}
        style={{
          background: "#0f1225",
          border: `1px solid ${border}`,
          borderRadius: 8,
          cursor: clickable ? "pointer" : "default",
        }}
        className="overflow-hidden"
      >
        {tbd ? (
          <div className="flex h-[66px] items-center justify-center text-[10px] italic text-[#2a2f45]">
            Por definir
          </div>
        ) : (
          <>
            <Row team={m!.local} score={showScore(m!) ? m!.gl : null} win={m!.ganador === "local"} done={!!m!.finalizado} />
            <Row team={m!.visitante} score={showScore(m!) ? m!.gv : null} win={m!.ganador === "visitante"} done={!!m!.finalizado} />
            {m!.pen_l != null && m!.pen_v != null && (
              <div className="py-0.5 text-center text-[9px] text-[#fbbf24]">
                pen {m!.pen_l}–{m!.pen_v}
              </div>
            )}
          </>
        )}
      </div>
      {m && !m.finalizado && m.fecha && (
        <div className="truncate border-x border-b border-[#1e2850] bg-[#0f1225] px-1 pb-0.5 text-center text-[7.5px] text-[#6ee7b7]">
          {fmtFecha(m.fecha)}
        </div>
      )}
    </div>
  );
}

function showScore(m: BracketMatch) {
  return m.finalizado || m.en_vivo;
}

function Row({
  team,
  score,
  win,
  done,
}: {
  team: Team | null;
  score: number | null;
  win: boolean;
  done: boolean;
}) {
  const loser = done && !win;
  const name = team?.nombre ?? "?";
  return (
    <div
      className="flex h-[26px] items-center gap-1 px-1.5"
      style={{ borderBottom: "1px solid #080a12" }}
    >
      <TeamFlag team={team} />
      <span
        className="flex-1 truncate text-[11px]"
        style={{ color: win ? "#e8ecff" : loser ? "#2a2f45" : "#6a7090", fontWeight: win ? 600 : 500 }}
      >
        {name.length > 11 ? name.slice(0, 10) + "." : name}
      </span>
      <span
        className="w-3.5 text-right text-[12px] font-bold"
        style={{ color: win ? "#22c55e" : loser ? "#1a1f35" : "#8b9bb4" }}
      >
        {score ?? ""}
      </span>
    </div>
  );
}

function TeamFlag({ team }: { team: Team | null }) {
  if (team?.logo_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={team.logo_url} alt="" className="h-3.5 w-3.5 shrink-0 object-contain" />;
  }
  return <span className="w-4 shrink-0 text-center text-[8px] text-[#4a5170]">{team?.iso || ""}</span>;
}
