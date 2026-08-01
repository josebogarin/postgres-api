"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { TorneoActivo } from "@/lib/types";

// ─────────────────────────────────────────────────────────────────────────────
// Secuencia: LOGIN (elegir apostador + PIN) → ELEGIR TORNEO → Live.
// La identidad queda en sesión; "Cambiar torneo" no re-pide PIN, "Cerrar sesión" sí.
// Admin: PIN 1964 → entra en solo lectura (no puede modificar apuestas).
// ─────────────────────────────────────────────────────────────────────────────

function normalizeTorneos(raw: unknown): TorneoActivo[] {
  const box = raw as { torneos?: unknown[]; activas?: unknown[] } | unknown[];
  const arr: unknown[] = Array.isArray(box)
    ? box
    : Array.isArray((box as { torneos?: unknown[] })?.torneos)
    ? (box as { torneos: unknown[] }).torneos
    : Array.isArray((box as { activas?: unknown[] })?.activas)
    ? (box as { activas: unknown[] }).activas
    : [];
  return arr
    .map((x) => {
      const t = x as Record<string, unknown>;
      const estado = (t.estado as string) ?? null;
      const cerrado = Boolean(t.cerrado ?? t.terminado) || estado === "finalizado";
      return {
        id: Number(t.id ?? t.torneo_id),
        nombre: String(t.nombre ?? t.titulo ?? t.competicion ?? `Torneo ${t.id ?? ""}`),
        anio: t.anio != null ? Number(t.anio) : undefined,
        api_league_id: t.api_league_id != null ? Number(t.api_league_id) : undefined,
        estado,
        cerrado,
        tipo: (t.tipo as string) ?? null,
        emoji: (t.emoji as string) ?? null,
        categoria: (t.categoria as string) ?? null,
        tiene_tercer_puesto: t.tiene_tercer_puesto as boolean | undefined,
        datos_cargados: t.datos_cargados as boolean | undefined,
        total_partidos: t.total_partidos as number | undefined,
        partidos_grupos: t.partidos_grupos as number | undefined,
        partidos_ko: t.partidos_ko as number | undefined,
        fecha_inicio: (t.fecha_inicio as string) ?? null,
        fecha_fin: (t.fecha_fin as string) ?? null,
        estado_juego: (t.estado_juego as string) ?? undefined,
        estado_label: (t.estado_label as string) ?? undefined,
      } as TorneoActivo;
    })
    .filter((t) => Number.isFinite(t.id));
}

const RE_SELECCIONES = /mundial|world\s*cup|copa\s*del\s*mundo|eurocopa|\beuro\b|copa\s*am[eé]rica|naciones|nations/i;
const RE_CLUBES = /champions|libertadores|sudamericana|europa\s*league|club/i;
const LOGO_BY_LEAGUE: Record<number, string> = {
  1: "mundial", 2: "champions", 3: "europa-league", 4: "eurocopa",
  9: "copa-america", 11: "sudamericana", 13: "libertadores",
};
const LOGO_EXTS = ["png", "svg", "webp", "jpg"];
const EMOJI_BY_LEAGUE: Record<number, string> = {};
function esTorneoClubes(t: TorneoActivo): boolean {
  const tipo = (t.tipo ?? t.categoria ?? "").toLowerCase();
  if (tipo === "clubes" || tipo === "club") return true;
  if (tipo === "paises" || tipo === "selecciones") return false;
  const s = t.nombre;
  if (RE_SELECCIONES.test(s)) return false;
  return RE_CLUBES.test(s);
}

type Apostador = { id: number; username: string; alias: string; nombre: string };
type Session = { id: number; nombre: string; apodo: string; isAdmin: boolean };

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const id = Number(localStorage.getItem("becbuc_apostador_id") || 0);
    if (id) {
      setSession({
        id,
        nombre: localStorage.getItem("becbuc_apostador_nombre") || "",
        apodo: localStorage.getItem("becbuc_apostador_apodo") || "",
        isAdmin: localStorage.getItem("becbuc_is_admin") === "1",
      });
    }
    setReady(true);
  }, []);

  const onLogin = (s: Session) => {
    localStorage.setItem("becbuc_apostador_id", String(s.id));
    localStorage.setItem("becbuc_apostador_nombre", s.nombre);
    localStorage.setItem("becbuc_apostador_apodo", s.apodo);
    localStorage.setItem("becbuc_is_admin", s.isAdmin ? "1" : "0");
    setSession(s);
  };
  const logout = () => {
    ["becbuc_apostador_id","becbuc_apostador_nombre","becbuc_apostador_apodo","becbuc_is_admin",
     "becbuc_torneo","becbuc_torneo_nombre","becbuc_torneo_ro","becbuc_torneo_tercero"]
      .forEach((k) => localStorage.removeItem(k));
    setSession(null);
  };

  if (!ready) return <main className="mx-auto w-full max-w-md px-4 py-10 text-center text-sm text-muted">Cargando…</main>;
  return session
    ? <TorneoSelector session={session} onLogout={logout} />
    : <Login onLogin={onLogin} />;
}

// ─────────────────────── LOGIN ───────────────────────
function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [apostadores, setApostadores] = useState<Apostador[] | null>(null);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<Apostador | null>(null);
  const [forgot, setForgot] = useState(false);

  useEffect(() => {
    api.get<Apostador[]>("/bets/apostadores")
      .then((r) => setApostadores(Array.isArray(r) ? r : []))
      .catch(() => setApostadores([]));
  }, []);

  const list = (apostadores || []).filter((a) =>
    (a.alias || a.username || "").toLowerCase().includes(q.toLowerCase()));

  return (
    <main className="mx-auto w-full max-w-md px-4 py-6">
      <header className="mb-4 flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/static/becbuc-logo.jpeg" alt="BECBUC" className="h-10 w-10 rounded-xl object-contain" />
        <div>
          <h1 className="text-lg font-bold leading-tight">BECBUC</h1>
          <p className="text-xs text-muted">Elegí tu nombre para entrar</p>
        </div>
      </header>

      {apostadores === null && <p className="py-10 text-center text-sm text-muted">Cargando apostadores…</p>}

      {apostadores !== null && (
        <>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar tu nombre…"
            className="mb-3 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm outline-none"
          />
          <div className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
            {list.map((a) => (
              <button
                key={a.id}
                onClick={() => setSel(a)}
                className="flex items-center justify-between rounded-xl border border-border bg-surface px-3 py-2.5 text-left text-sm transition active:scale-[0.99]"
              >
                <span className="min-w-0 flex-1 truncate">
                  <span className="block truncate font-medium">{a.alias || a.username}</span>
                  {a.nombre && a.nombre !== (a.alias || a.username) && (
                    <span className="block truncate text-[11px] text-muted">{a.nombre}</span>
                  )}
                </span>
                <span className="ml-2 text-muted">›</span>
              </button>
            ))}
            {list.length === 0 && <p className="py-6 text-center text-xs text-muted">Sin resultados.</p>}
          </div>
          <button onClick={() => setForgot(true)} className="mt-4 w-full text-center text-xs text-brand underline">
            Olvidé mi PIN
          </button>
        </>
      )}

      {sel && <PinModal apostador={sel} onClose={() => setSel(null)} onLogin={onLogin} />}
      {forgot && <ForgotModal onClose={() => setForgot(false)} />}
    </main>
  );
}

function Overlay({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-t-2xl border border-border bg-surface p-5 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function PinModal({ apostador, onClose, onLogin }: {
  apostador: Apostador; onClose: () => void; onLogin: (s: Session) => void;
}) {
  const [mode, setMode] = useState<"loading" | "create" | "enter">("loading");
  const [pin, setPin] = useState("");
  const [pin2, setPin2] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const apodo = apostador.alias || apostador.username;
  const nombreCompleto = apostador.nombre || apodo;

  useEffect(() => {
    api.get<{ tiene_pin: boolean }>(`/bets/live-pin-estado/${apostador.id}`)
      .then((r) => setMode(r.tiene_pin ? "enter" : "create"))
      .catch(() => setMode("enter"));
  }, [apostador.id]);

  const doVerify = async (p: string) => {
    setBusy(true); setErr(null);
    try {
      const r = await api.post<{ ok: boolean; is_admin?: boolean; error?: string }>(
        "/bets/live-verify-pin", { apostador_id: apostador.id, pin: p });
      if (!r.ok) { setErr(r.error || "PIN incorrecto."); return; }
      onLogin({ id: apostador.id, nombre: nombreCompleto, apodo, isAdmin: !!r.is_admin });
    } finally { setBusy(false); }
  };

  const submit = async () => {
    const p = pin.trim();
    if (p === "1964") { await doVerify(p); return; } // admin
    if (mode === "create") {
      if (!/^\d{4}$/.test(p)) { setErr("El PIN debe tener 4 dígitos."); return; }
      if (p !== pin2.trim()) { setErr("Los PIN no coinciden."); return; }
      setBusy(true); setErr(null);
      try {
        const r = await api.post<{ ok: boolean; error?: string }>(
          "/bets/live-set-pin", { apostador_id: apostador.id, pin: p });
        if (!r.ok) { setErr(r.error || "No se pudo crear el PIN."); return; }
        setMode("enter"); setPin(""); setPin2("");
        setMsg("PIN creado. Ahora ingresalo para entrar.");
      } finally { setBusy(false); }
      return;
    }
    if (!/^\d{4}$/.test(p)) { setErr("Ingresá tu PIN de 4 dígitos."); return; }
    await doVerify(p);
  };

  return (
    <Overlay onClose={onClose}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-bold">{nombreCompleto}{apodo !== nombreCompleto ? ` (${apodo})` : ""}</h2>
        <button onClick={onClose} className="text-muted">✕</button>
      </div>
      {mode === "loading" && <p className="py-4 text-center text-sm text-muted">Cargando…</p>}
      {mode === "create" && (
        <>
          <p className="mb-2 text-xs text-muted">Es tu primera vez. Creá tu PIN de 4 dígitos (lo vas a usar para entrar y confirmar tus apuestas).</p>
          <PinInput value={pin} onChange={setPin} placeholder="PIN (4 dígitos)" />
          <PinInput value={pin2} onChange={setPin2} placeholder="Repetí el PIN" />
        </>
      )}
      {mode === "enter" && (
        <>
          <p className="mb-2 text-xs text-muted">Ingresá tu PIN de 4 dígitos.</p>
          <PinInput value={pin} onChange={setPin} placeholder="PIN" autoFocus />
        </>
      )}
      {msg && <p className="mt-2 text-xs text-brand">{msg}</p>}
      {err && <p className="mt-2 text-xs text-orange">{err}</p>}
      <button
        onClick={submit}
        disabled={busy || mode === "loading"}
        className="mt-4 w-full rounded-xl bg-brand py-2.5 text-sm font-bold text-black disabled:opacity-50"
      >
        {busy ? "…" : mode === "create" ? "Crear PIN" : "Entrar"}
      </button>
    </Overlay>
  );
}

function PinInput({ value, onChange, placeholder, autoFocus }: {
  value: string; onChange: (v: string) => void; placeholder?: string; autoFocus?: boolean;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 4))}
      placeholder={placeholder}
      inputMode="numeric"
      autoFocus={autoFocus}
      className="mb-2 w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-center text-lg tracking-[0.4em] outline-none"
    />
  );
}

function ForgotModal({ onClose }: { onClose: () => void }) {
  const [tel, setTel] = useState("");
  const [res, setRes] = useState<{ ok: boolean; pin?: string; apostador?: string; error?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true); setRes(null);
    try {
      const r = await api.post<{ ok: boolean; pin?: string; apostador?: string; error?: string }>(
        "/bets/live-recuperar-pin", { telefono: tel });
      setRes(r);
    } finally { setBusy(false); }
  };
  return (
    <Overlay onClose={onClose}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-bold">Recuperar PIN</h2>
        <button onClick={onClose} className="text-muted">✕</button>
      </div>
      <p className="mb-2 text-xs text-muted">Ingresá tu número de celular registrado en BECBUC y te mostramos tu PIN.</p>
      <input
        value={tel}
        onChange={(e) => setTel(e.target.value)}
        placeholder="Ej: 0981 123 456"
        inputMode="tel"
        className="w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm outline-none"
      />
      {res && res.ok && (
        <p className="mt-3 rounded-xl bg-surface-2 px-3 py-2 text-sm">
          {res.apostador ? `${res.apostador}: ` : ""}tu PIN es <b className="text-brand tracking-widest">{res.pin}</b>
        </p>
      )}
      {res && !res.ok && <p className="mt-2 text-xs text-orange">{res.error}</p>}
      <button onClick={submit} disabled={busy} className="mt-4 w-full rounded-xl bg-brand py-2.5 text-sm font-bold text-black disabled:opacity-50">
        {busy ? "…" : "Mostrar mi PIN"}
      </button>
    </Overlay>
  );
}

// ─────────────────────── SELECTOR DE TORNEO ───────────────────────
function TorneoSelector({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const router = useRouter();
  const [estado, setEstado] = useState<{ fase: "cargando" } | { fase: "ok"; torneos: TorneoActivo[] } | { fase: "error" }>({ fase: "cargando" });

  useEffect(() => {
    let vivo = true;
    api.get<unknown>(`/torneo/activas?solo_live=true`)
      .then((raw) => vivo && setEstado({ fase: "ok", torneos: normalizeTorneos(raw) }))
      .catch(() => vivo && setEstado({ fase: "error" }));
    return () => { vivo = false; };
  }, []);

  const entrar = (t: TorneoActivo) => {
    localStorage.setItem("becbuc_torneo", String(t.id));
    localStorage.setItem("becbuc_torneo_nombre", t.nombre);
    const soloLectura = t.cerrado || t.estado_label === "concluido" || session.isAdmin;
    localStorage.setItem("becbuc_torneo_ro", soloLectura ? "1" : "0");
    localStorage.setItem("becbuc_torneo_tercero", esTorneoClubes(t) ? "0" : "1");
    router.push("/playoff-live");
  };

  return (
    <main className="mx-auto w-full max-w-md px-4 py-6">
      <header className="mb-4 flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/static/becbuc-logo.jpeg" alt="BECBUC" className="h-10 w-10 rounded-xl object-contain" />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-bold leading-tight">
            {session.nombre}{session.isAdmin && <span className="ml-1 rounded bg-orange/20 px-1.5 py-0.5 text-[10px] font-semibold text-orange">admin · solo lectura</span>}
          </h1>
          <p className="text-xs text-muted">Elegí un torneo</p>
        </div>
        <button onClick={onLogout} className="shrink-0 rounded-lg border border-border px-2 py-1 text-xs text-muted">Cerrar sesión</button>
      </header>

      {estado.fase === "cargando" && <p className="py-10 text-center text-sm text-muted">Cargando torneos…</p>}
      {estado.fase === "error" && <p className="py-10 text-center text-sm text-muted">Sin conexión con la API (¿uvicorn en :8000?)</p>}
      {estado.fase === "ok" && estado.torneos.length === 0 && (
        <p className="py-10 text-center text-sm text-muted">No hay torneos activos.</p>
      )}
      {estado.fase === "ok" && estado.torneos.length > 0 && (
        <div className="flex flex-col gap-3">
          {estado.torneos.map((t) => <TorneoCard key={t.id} t={t} onEnter={() => entrar(t)} />)}
        </div>
      )}
    </main>
  );
}

const ESTADO_LABEL: Record<string, { txt: string; cls: string }> = {
  en_ejecucion: { txt: "En ejecución", cls: "bg-brand/20 text-brand" },
  pendiente: { txt: "Pendiente", cls: "bg-amber-400/15 text-amber-400" },
  concluido: { txt: "Concluido", cls: "bg-surface-2 text-muted" },
};
const ESTADO_JUEGO: Record<string, string> = {
  grupos: "fase de grupos", playoffs: "playoffs", terminada: "finalizado", pendiente: "aún no arranca",
};
function fdmy(iso?: string | null): string | null {
  if (!iso) return null;
  const s = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  const d = new Date(s);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("es", { day: "2-digit", month: "2-digit", year: "2-digit" });
}
function CompLogo({ t, esClubes }: { t: TorneoActivo; esClubes: boolean }) {
  const [extIdx, setExtIdx] = useState(0);
  const lid = t.api_league_id ?? -1;
  const base = LOGO_BY_LEAGUE[lid];
  const emoji = EMOJI_BY_LEAGUE[lid] || t.emoji || (esClubes ? "🏟️" : "🏆");
  if (!base || extIdx >= LOGO_EXTS.length)
    return <span className="grid h-10 w-10 place-items-center text-2xl">{emoji}</span>;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={`/static/logos/${base}.${LOGO_EXTS[extIdx]}`} alt="" className="h-10 w-10 shrink-0 rounded-md object-contain" onError={() => setExtIdx((i) => i + 1)} />
  );
}
function TorneoCard({ t, onEnter }: { t: TorneoActivo; onEnter: () => void }) {
  const esClubes = esTorneoClubes(t);
  const label = ESTADO_LABEL[t.estado_label ?? ""] ?? ESTADO_LABEL.pendiente;
  const ini = fdmy(t.fecha_inicio); const fin = fdmy(t.fecha_fin);
  const fechas = ini && fin ? `${ini} – ${fin}` : ini || fin || null;
  return (
    <button onClick={onEnter} className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4 text-left transition active:scale-[0.99]">
      <CompLogo t={t} esClubes={esClubes} />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold">{t.nombre}</span>
        <span className="block truncate text-xs text-muted">
          {esClubes ? "Clubes" : "Selecciones"}
          {t.estado_juego ? ` · ${ESTADO_JUEGO[t.estado_juego] ?? t.estado_juego}` : ""}
        </span>
        <span className="block truncate text-[11px] text-muted">
          {t.total_partidos ? `${t.total_partidos} partidos` : "sin fixtures"}{fechas ? ` · ${fechas}` : ""}
        </span>
      </span>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${label.cls}`}>{label.txt}</span>
      <span className="ml-1 shrink-0 text-muted">›</span>
    </button>
  );
}
