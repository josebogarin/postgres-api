import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal, close_engines, engine
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with AsyncSessionLocal() as session:
        await init_db(session)
        await session.commit()
    # Sincronizar competiciones de fútbol si la API key está configurada
    if settings.APIFOOTBALL_KEY and settings.APIFOOTBALL_KEY != "TU_API_KEY_AQUI":
        try:
            from app.services.torneo_service import sincronizar_competiciones
            await sincronizar_competiciones(engine)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Sincronización torneos falló: %s", e)
    # Arrancar monitor de partidos
    try:
        from app.services.monitor import MonitorScheduler
        from app.services.monitor.config import MonitorConfig
        _monitor = MonitorScheduler(config=MonitorConfig.from_env())
        await _monitor.start()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Monitor no pudo arrancar: %s", e)
        _monitor = None
    yield
    # Detener monitor al salir
    if _monitor is not None:
        try:
            await _monitor.stop()
        except Exception:
            pass
    await close_engines()


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__, "trace": traceback.format_exc()},
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

import re
_MOBILE_RE = re.compile(
    r"Mobile|Android|iPhone|iPod|iPad|Windows Phone|webOS|BlackBerry|Opera Mini|IEMobile",
    re.IGNORECASE,
)

def _es_movil(request: Request) -> bool:
    ua = request.headers.get("user-agent", "")
    return bool(_MOBILE_RE.search(ua))

@app.get("/", include_in_schema=False)
async def root(request: Request):
    destino = "/static/BECBUC-movil.html" if _es_movil(request) else "/BECBUC-portal"
    return RedirectResponse(url=destino)

# ── CRUD Tester (solo en desarrollo) ─────────────────────────────────────────
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    async def login_page():
        return FileResponse(str(_static_dir / "login.html"))

    @app.get("/portal", response_class=HTMLResponse, include_in_schema=False)
    async def portal_page():
        return FileResponse(str(_static_dir / "portal.html"))

    @app.get("/tester", response_class=HTMLResponse, include_in_schema=False)
    async def crud_tester():
        return FileResponse(str(_static_dir / "tester.html"))

    @app.get("/usuarios", response_class=HTMLResponse, include_in_schema=False)
    async def usuarios_page():
        return FileResponse(str(_static_dir / "usuarios.html"))

    @app.get("/diccionario", response_class=HTMLResponse, include_in_schema=False)
    async def diccionario_page():
        return FileResponse(str(_static_dir / "diccionario.html"))

    @app.get("/tabla", response_class=HTMLResponse, include_in_schema=False)
    async def tabla_page():
        return FileResponse(str(_static_dir / "tabla.html"))

    @app.get("/api-reference", response_class=HTMLResponse, include_in_schema=False)
    async def api_reference_page():
        return FileResponse(str(_static_dir / "api-reference.html"))

    @app.get("/cabecera", response_class=HTMLResponse, include_in_schema=False)
    async def cabecera_detalle_page():
        return FileResponse(str(_static_dir / "cabecera_detalle.html"))

    @app.get("/config-cabecera", response_class=HTMLResponse, include_in_schema=False)
    async def config_cabecera_page():
        return FileResponse(str(_static_dir / "config_cabecera.html"))

    @app.get("/fixture", response_class=HTMLResponse, include_in_schema=False)
    async def fixture_page():
        return FileResponse(str(_static_dir / "fixture.html"))

    @app.get("/apostador", response_class=HTMLResponse, include_in_schema=False)
    async def apostador_page():
        return FileResponse(str(_static_dir / "apostador.html"))

    @app.get("/BECBUC-ADM", response_class=HTMLResponse, include_in_schema=False)
    async def becbuc_adm_page():
        return FileResponse(str(_static_dir / "BECBUC-ADM.html"))

    @app.get("/BECBUC-portal", response_class=HTMLResponse, include_in_schema=False)
    async def becbuc_portal_page():
        return FileResponse(str(_static_dir / "BECBUC-portal.html"))

    @app.get("/BECBUC-ADM-fases", response_class=HTMLResponse, include_in_schema=False)
    async def becbuc_adm_fases_page():
        return FileResponse(str(_static_dir / "BECBUC-ADM-fases.html"))

    @app.get("/importar-apuestas", response_class=HTMLResponse, include_in_schema=False)
    async def importar_apuestas_page():
        return FileResponse(str(_static_dir / "importar-apuestas.html"))

    @app.get("/live", response_class=HTMLResponse, include_in_schema=False)
    async def becbuc_live_page():
        """Sirve becbuc-live.html con headers no-cache para evitar problemas en mobile."""
        resp = FileResponse(str(_static_dir / "becbuc-live.html"))
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
