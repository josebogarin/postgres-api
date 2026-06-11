"""
monitor/api_client.py
=====================
Cliente HTTP abstactado para API-Football v3.

Características:
- Retry con backoff exponencial ante errores de red o 5xx.
- Log automático de cada llamada en api_sync_log.
- Control de cuota diaria (100 req/día en plan gratuito).
- Métodos orientados a casos de uso del monitor (no genéricos).
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, timezone
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

_API_BASE = "https://v3.football.api-sports.io"


def _headers() -> dict[str, str]:
    return {
        "x-rapidapi-key": settings.APIFOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Resultado de llamada API
# ─────────────────────────────────────────────────────────────────────────────
class ApiResult:
    __slots__ = ("data", "status_code", "response_ms", "quota_remaining", "error")

    def __init__(
        self,
        data: list[dict] | None = None,
        status_code: int = 0,
        response_ms: int = 0,
        quota_remaining: int | None = None,
        error: str | None = None,
    ):
        self.data = data or []
        self.status_code = status_code
        self.response_ms = response_ms
        self.quota_remaining = quota_remaining
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Cliente principal
# ─────────────────────────────────────────────────────────────────────────────
class ApiFootballClient:
    """
    Envoltorio async sobre API-Football v3.
    Instanciado una sola vez en el scheduler; compartido entre todos los polls.
    """

    def __init__(
        self,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client: httpx.AsyncClient | None = None
        # Contador de llamadas del día (se resetea a medianoche UTC)
        self._calls_today: int = 0
        self._calls_date: date | None = None
        # Callback para persistir logs — se inyecta desde el scheduler
        self._log_callback: Any = None   # async def (endpoint, params, result) -> None

    async def __aenter__(self) -> "ApiFootballClient":
        self._client = httpx.AsyncClient(
            base_url=_API_BASE,
            headers=_headers(),
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def set_log_callback(self, callback: Any) -> None:
        """Inyectar función async para persistir logs en BD."""
        self._log_callback = callback

    def _check_and_count(self, max_calls: int) -> bool:
        """Retorna False si ya se superó la cuota diaria."""
        today = date.today()
        if self._calls_date != today:
            self._calls_today = 0
            self._calls_date = today
        if self._calls_today >= max_calls:
            log.warning("monitor.quota_exceeded", calls_today=self._calls_today, max=max_calls)
            return False
        self._calls_today += 1
        return True

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
        max_calls: int = 80,
        origen: str = "monitor",
    ) -> ApiResult:
        """
        GET con retry/backoff. Registra en api_sync_log vía callback.
        """
        if not self._check_and_count(max_calls):
            return ApiResult(error="cuota_diaria_superada")

        assert self._client is not None, "Usar dentro de 'async with ApiFootballClient()'"

        last_error: str = ""
        for attempt in range(self._max_retries):
            t0 = time.monotonic()
            try:
                resp = await self._client.get(endpoint, params=params)
                ms = int((time.monotonic() - t0) * 1000)
                quota = self._parse_quota(resp)

                if resp.status_code == 200:
                    body = resp.json()
                    fixtures = body.get("response", [])
                    result = ApiResult(
                        data=fixtures,
                        status_code=200,
                        response_ms=ms,
                        quota_remaining=quota,
                    )
                    await self._maybe_log(endpoint, params, result, origen)
                    return result

                last_error = f"HTTP {resp.status_code}"
                result = ApiResult(
                    status_code=resp.status_code,
                    response_ms=ms,
                    quota_remaining=quota,
                    error=last_error,
                )
                await self._maybe_log(endpoint, params, result, origen)

                if resp.status_code < 500:
                    # 4xx: no reintentar
                    return result

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                ms = int((time.monotonic() - t0) * 1000)
                last_error = f"{type(exc).__name__}: {exc}"
                log.warning("monitor.api_error", attempt=attempt + 1, error=last_error)

            # Backoff antes del siguiente intento
            if attempt < self._max_retries - 1:
                wait = self._backoff_base ** attempt
                await asyncio.sleep(wait)

        result = ApiResult(error=last_error)
        await self._maybe_log(endpoint, params, result, origen)
        return result

    # ── Métodos de negocio ───────────────────────────────────────────────────

    async def get_fixtures_today(
        self,
        league_id: int,
        season: int,
        fecha: date,
        max_calls: int = 80,
    ) -> ApiResult:
        """Obtiene todos los fixtures de una fecha (para planificación diaria)."""
        return await self._get(
            "/fixtures",
            {
                "league": league_id,
                "season": season,
                "date": fecha.isoformat(),
                "timezone": "UTC",
            },
            max_calls=max_calls,
        )

    async def get_fixture_detail(
        self,
        api_fixture_id: int,
        max_calls: int = 80,
    ) -> ApiResult:
        """
        Obtiene un fixture individual con eventos, estadísticas y scores live.
        Costoso en cuota — solo llamar cuando corresponde según intervalo.
        """
        return await self._get(
            "/fixtures",
            {
                "id": api_fixture_id,
                "timezone": "UTC",
            },
            max_calls=max_calls,
        )

    async def check_api_available(self) -> tuple[bool, str]:
        """
        Prueba de disponibilidad de la API. Usado por el panel de admin.
        Retorna (disponible: bool, mensaje: str).
        """
        try:
            t0 = time.monotonic()
            assert self._client
            resp = await self._client.get("/status", timeout=5.0)
            ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                quota = self._parse_quota(resp)
                return True, f"OK — {ms}ms — cuota restante: {quota}"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)

    # ── Helpers privados ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_quota(resp: httpx.Response) -> int | None:
        try:
            return int(resp.headers.get("x-ratelimit-requests-remaining", -1))
        except (ValueError, TypeError):
            return None

    async def _maybe_log(
        self,
        endpoint: str,
        params: dict,
        result: ApiResult,
        origen: str,
    ) -> None:
        if self._log_callback:
            try:
                await self._log_callback(endpoint, params, result, origen)
            except Exception:
                pass  # No propagar errores de logging


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de parseo del fixture JSON de API-Football
# ─────────────────────────────────────────────────────────────────────────────
def parse_fixture_summary(fix: dict) -> dict:
    """
    Extrae los campos relevantes de un objeto fixture de la API.
    Estructura API: { fixture: {...}, league: {...}, teams: {...}, goals: {...}, score: {...} }
    """
    f = fix.get("fixture", {})
    goals = fix.get("goals", {})
    score = fix.get("score", {})
    teams = fix.get("teams", {})
    status = f.get("status", {})
    elapsed = status.get("elapsed")

    return {
        "api_fixture_id":  f.get("id"),
        "api_status_raw":  status.get("short", "NS"),
        "elapsed":         elapsed,           # minuto actual
        "date_utc":        f.get("date"),     # ISO con tz
        "venue":           (f.get("venue") or {}).get("name"),
        # Goles
        "goles_local":     goals.get("home"),
        "goles_visitante": goals.get("away"),
        # Penales (tanda)
        "penales_local":   (score.get("penalty") or {}).get("home"),
        "penales_visitante": (score.get("penalty") or {}).get("away"),
        # Equipos (para verificar el mapeo)
        "api_home_id":     (teams.get("home") or {}).get("id"),
        "api_away_id":     (teams.get("away") or {}).get("id"),
        "home_winner":     (teams.get("home") or {}).get("winner"),
        "away_winner":     (teams.get("away") or {}).get("winner"),
    }
