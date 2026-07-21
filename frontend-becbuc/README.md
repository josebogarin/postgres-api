# BECBUC Web (frontend-becbuc)

Reescritura incremental de las superficies BECBUC en **Next.js 16 + React 19 + Tailwind 4**,
mobile-first. Proyecto **separado y limpio**: no toca los HTML actuales de
`backend/static/` (siguen en producción como fallback hasta lograr paridad).

Superficies (en orden de migración):
1. **Playoff Live** (`/playoff-live`) — piloto (reemplaza `becbuc-live-playoffs.html`).
2. **Grupos Live** (`/grupos-live`) — reemplaza `becbuc-live.html`.

## Requisitos
- Node 18+ y npm (o pnpm).
- El backend FastAPI corriendo en `http://localhost:8000` (uvicorn).

## Desarrollo (con hot-reload + prueba en teléfono)
```bash
cd "C:\proyecto FAST API\frontend-becbuc"
npm install
npm run dev            # http://localhost:3000
```
En dev, `/api/*` se proxya al backend `:8000` (ver next.config.ts), así que el
navegador —y el teléfono— hablan con la API en el mismo origen.

**Probar en el teléfono del apostador:** exponé el puerto 3000 con ngrok:
```bash
ngrok http 3000
```
y abrí la URL en el celular. (El backend sigue en :8000; el proxy de Next lo alcanza.)

## Build para producción (servido por el mismo uvicorn/ngrok)
```bash
npm run build:export   # genera ./out con basePath /static/v2
```
Copiar `out/` a `backend/static/v2/` → queda accesible en
`http://localhost:8000/static/v2/` (mismo servidor y mismo ngrok que hoy).
El link viejo NO cambia hasta que decidas el cutover.

## Estructura
- `app/` — páginas (App Router).
- `lib/api.ts` — cliente API (JWT + ngrok-skip, mismo origen).
- `lib/types.ts` — tipos de dominio.
- `app/globals.css` — tema Bet365 oscuro (variables Tailwind 4), mobile-first.
