"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

// Contenedor con pan (arrastrar con el dedo/mouse) + zoom (pinch, rueda o ＋/－).
// - El contenido mantiene su tamaño real (no se reescala para "entrar").
// - Zoom mínimo = 1 (tamaño original); se puede agrandar hasta MAX.
const MIN = 1;
const MAX = 3;

export default function PanZoom({
  contentW,
  contentH,
  focusX,
  height = "70vh",
  children,
}: {
  contentW: number;
  contentH: number;
  focusX?: number;
  height?: string;
  children: ReactNode;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [t, setT] = useState({ x: 0, y: 8, s: 1 });
  const ptrs = useRef<Map<number, { x: number; y: number }>>(new Map());
  const pinch = useRef<number | null>(null);
  const startRef = useRef<{ x: number; y: number } | null>(null);
  const draggingRef = useRef(false);

  // Centrar en la columna focal (Final) al montar.
  useEffect(() => {
    const w = wrapRef.current?.clientWidth ?? 0;
    const fx = focusX ?? contentW / 2;
    setT((p) => ({ ...p, x: w / 2 - fx * p.s }));
  }, [contentW, focusX]);

  const rel = (e: { clientX: number; clientY: number }) => {
    const r = wrapRef.current!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const zoomAt = (mx: number, my: number, factor: number) =>
    setT((p) => {
      const ns = Math.min(MAX, Math.max(MIN, p.s * factor));
      const k = ns / p.s;
      return { s: ns, x: mx - (mx - p.x) * k, y: my - (my - p.y) * k };
    });

  const onDown = (e: React.PointerEvent) => {
    const p = rel(e);
    ptrs.current.set(e.pointerId, p);
    if (ptrs.current.size === 1) {
      startRef.current = p; // no capturamos aún: permite distinguir toque de arrastre
      draggingRef.current = false;
    } else if (ptrs.current.size === 2) {
      const [a, b] = [...ptrs.current.values()];
      pinch.current = Math.hypot(a.x - b.x, a.y - b.y);
      startRef.current = null;
    }
  };

  const onMove = (e: React.PointerEvent) => {
    if (!ptrs.current.has(e.pointerId)) return;
    const prev = ptrs.current.get(e.pointerId)!;
    const cur = rel(e);
    ptrs.current.set(e.pointerId, cur);

    if (ptrs.current.size === 1) {
      if (!draggingRef.current && startRef.current) {
        const d = Math.hypot(cur.x - startRef.current.x, cur.y - startRef.current.y);
        if (d > 6) {
          draggingRef.current = true;
          (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
        }
      }
      setT((p) => ({ ...p, x: p.x + (cur.x - prev.x), y: p.y + (cur.y - prev.y) }));
    } else if (ptrs.current.size === 2 && pinch.current != null) {
      const [a, b] = [...ptrs.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      zoomAt(mid.x, mid.y, dist / pinch.current);
      pinch.current = dist;
    }
  };

  const onUp = (e: React.PointerEvent) => {
    ptrs.current.delete(e.pointerId);
    if (ptrs.current.size < 2) pinch.current = null;
    if (ptrs.current.size === 0) startRef.current = null;
  };

  // Si hubo arrastre, cancelar el click para que NO navegue a Mi Prono.
  const onClickCapture = (e: React.MouseEvent) => {
    if (draggingRef.current) {
      e.stopPropagation();
      draggingRef.current = false;
    }
  };

  // Rueda del mouse (desktop): listener nativo no-pasivo para poder preventDefault.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.1 : 1 / 1.1);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const btnZoom = (factor: number) => {
    const w = wrapRef.current?.clientWidth ?? 0;
    const h = wrapRef.current?.clientHeight ?? 0;
    zoomAt(w / 2, h / 2, factor);
  };

  return (
    <div className="relative">
      <div
        ref={wrapRef}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onClickCapture={onClickCapture}
        className="overflow-hidden rounded-xl border border-border"
        style={{ height, background: "#0b0e1f", touchAction: "none", cursor: "grab" }}
      >
        <div
          style={{
            width: contentW,
            height: contentH,
            transform: `translate(${t.x}px, ${t.y}px) scale(${t.s})`,
            transformOrigin: "0 0",
          }}
        >
          {children}
        </div>
      </div>
      <div className="absolute right-2 top-2 flex flex-col gap-1">
        <button
          onClick={() => btnZoom(1.25)}
          className="grid h-8 w-8 place-items-center rounded-lg border border-border bg-surface text-lg leading-none active:bg-surface-2"
          aria-label="Acercar"
        >
          +
        </button>
        <button
          onClick={() => btnZoom(1 / 1.25)}
          className="grid h-8 w-8 place-items-center rounded-lg border border-border bg-surface text-lg leading-none active:bg-surface-2"
          aria-label="Alejar"
        >
          −
        </button>
      </div>
    </div>
  );
}
