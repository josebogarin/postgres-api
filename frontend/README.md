# Web App — Panel de administración

Frontend del sistema multiplatforma. Conectado a [Postgres API](../postgres-docker).

## Stack

- **Next.js** 16 (App Router) + **TypeScript** + **Tailwind CSS** 4
- **Auth**: JWT en cookies httpOnly, refresh automático en middleware Edge Runtime
- **pnpm** como gestor de paquetes

## Requisitos

- Node.js 22+ (recomendado via nvm)
- pnpm 11+
- [Postgres API](../postgres-docker) corriendo en `http://localhost:8000`

## Setup en máquina nueva

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd web-app
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env.local
```

Editar `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### 3. Instalar dependencias

```bash
pnpm install --ignore-scripts
```

### 4. Iniciar en desarrollo

```bash
pnpm dev
```

Abrir `http://localhost:3000`.  
Credenciales por defecto: `admin@example.com` / `changeme123`

## Estructura del proyecto

```
app/
├── (auth)/login/       # Página de login (pública)
├── (dashboard)/        # Páginas protegidas con layout + sidebar
│   └── users/          # CRUD de usuarios
├── api/
│   ├── login/          # Route handler: autentica y setea cookies
│   └── logout/         # Route handler: limpia cookies
lib/
├── api.ts              # Cliente HTTP genérico (GET/POST/PATCH/DELETE)
└── auth.ts             # Lectura/escritura de cookies httpOnly
middleware.ts           # Guard de rutas + refresh automático de JWT
services/               # Capa de servicios por dominio (auth, users)
types/                  # Tipos TypeScript compartidos
components/
├── ui/                 # Button, Badge
└── layout/             # Sidebar
```

## Flujo de autenticación

1. Usuario hace login → `POST /api/login` → API llama al backend → setea cookies httpOnly
2. Cada request pasa por `middleware.ts` → valida JWT → si expiró, refresca automáticamente
3. Páginas del dashboard leen el token con `getAccessToken()` (server-side)
4. Logout → `POST /api/logout` → limpia cookies → redirige a `/login`

## Agregar una página nueva

```
app/(dashboard)/mi-seccion/page.tsx   ← servidor (fetching)
app/(dashboard)/mi-seccion/Form.tsx   ← cliente ("use client", formularios)
app/api/mi-seccion/route.ts           ← API route para mutaciones
services/mi-seccion.ts                ← llamadas al backend
```
