import type { NextConfig } from "next";

// Dos modos:
//  - DEV (npm run dev): proxy de /api -> uvicorn :8000, para que el navegador
//    (o el telefono via ngrok :3000) hable con la API en el mismo origen.
//  - EXPORT (npm run build:export): sitio estatico servido por uvicorn bajo
//    /static/v2 (mismo origen que la API -> fetch relativo a /api/v1).
const isExport = process.env.BUILD_EXPORT === "1";

const nextConfig: NextConfig = isExport
  ? {
      output: "export",
      images: { unoptimized: true },
      basePath: "/static/v2",
      assetPrefix: "/static/v2",
      trailingSlash: true,
    }
  : {
      async rewrites() {
        return [
          { source: "/api/:path*", destination: "http://localhost:8000/api/:path*" },
          // /static -> uvicorn: en dev sirve el logo real (/static/becbuc-logo.jpeg)
          // y demas assets del backend desde el mismo origen que la API.
          { source: "/static/:path*", destination: "http://localhost:8000/static/:path*" },
        ];
      },
    };

export default nextConfig;
