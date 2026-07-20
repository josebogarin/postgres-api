"""
monitor/config.py
=================
Configuración del monitor de partidos.

Fuente de verdad: variables de entorno vía Settings.
La tabla monitor_config en BD puede sobreescribir valores en runtime
(ver MonitorConfigLoader en persistence.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Instante de arranque oficial del Mundial 2026
# 2026-06-11 13:00:00 hora Ciudad de México (UTC-6) = 19:00 UTC
# 2026-06-11 16:00:00 hora Asunción          (UTC-3) = 19:00 UTC
# ─────────────────────────────────────────────────────────────────────────────
MUNDIAL_2026_START_UTC = datetime(2026, 6, 11, 19, 0, 0, tzinfo=timezone.utc)


@dataclass
class MonitorConfig:
    """Parámetros operativos del monitor. Todos tienen default sensato."""

    # ── Timing de arranque ──────────────────────────────────────────────────
    mundial_start_utc: datetime = field(
        default_factory=lambda: MUNDIAL_2026_START_UTC
    )
    # Cuántos segundos antes del primer partido del día arrancar el ciclo
    startup_margin_seg: int = 300          # 5 minutos

    # ── Intervalos de polling (segundos) ────────────────────────────────────
    # > 60 min antes del kick-off
    interval_far_seg: int = 600            # 10 min
    # 10 – 60 min antes del kick-off
    interval_near_seg: int = 150           # 2.5 min
    # < 10 min antes del kick-off
    interval_imminent_seg: int = 45        # 45 s
    # Partido en vivo (1H / 2H / ET / P)
    interval_live_seg: int = 45            # 45 s
    # Descanso (HT / BT)
    interval_halftime_seg: int = 90        # 90 s

    # ── Fin de jornada ──────────────────────────────────────────────────────
    # Espera tras detectar todos los partidos terminales antes de verificación final
    grace_period_seg: int = 600            # 10 min
    # Intervalo del tick principal del scheduler
    tick_seg: int = 30                     # cada 30 s revisa qué partidos necesitan poll

    # ── Cuota API ───────────────────────────────────────────────────────────
    max_api_calls_dia: int = 7500          # plan pago: ~7500 calls/día

    # ── HTTP ────────────────────────────────────────────────────────────────
    api_timeout: float = 15.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0        # segundos * 2^intento

    # ── Competición ─────────────────────────────────────────────────────────
    league_id: int = 1                     # FIFA World Cup en API-Football
    season: int = 2026

    # ── Display ─────────────────────────────────────────────────────────────
    display_tz: str = "America/Asuncion"   # para logs / UI legibles

    # ── Feature flag ────────────────────────────────────────────────────────
    monitor_activo: bool = True

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        """Crea instancia desde variables de entorno MONITOR_* en Settings."""
        from app.core.config import settings
        cfg = cls()
        # Sobreescribir campos que tengan variable de entorno definida
        env_map = {
            "MONITOR_STARTUP_MARGIN_SEG": "startup_margin_seg",
            "MONITOR_INTERVAL_FAR_SEG":   "interval_far_seg",
            "MONITOR_INTERVAL_NEAR_SEG":  "interval_near_seg",
            "MONITOR_INTERVAL_IMMIN_SEG": "interval_imminent_seg",
            "MONITOR_INTERVAL_LIVE_SEG":  "interval_live_seg",
            "MONITOR_INTERVAL_HT_SEG":    "interval_halftime_seg",
            "MONITOR_GRACE_PERIOD_SEG":   "grace_period_seg",
            "MONITOR_MAX_CALLS_DIA":      "max_api_calls_dia",
            "MONITOR_ACTIVO":             "monitor_activo",
            "MONITOR_LEAGUE_ID":          "league_id",
            "MONITOR_SEASON":             "season",
        }
        for env_key, attr in env_map.items():
            val = getattr(settings, env_key, None)
            if val is not None:
                # Coercionar al tipo del campo
                current = getattr(cfg, attr)
                if isinstance(current, bool):
                    setattr(cfg, attr, str(val).lower() in ("true", "1", "yes"))
                elif isinstance(current, int):
                    setattr(cfg, attr, int(val))
                elif isinstance(current, float):
                    setattr(cfg, attr, float(val))
                else:
                    setattr(cfg, attr, val)
        return cfg

    def interval_for_minutes_to_start(self, minutos: float) -> int:
        """Intervalo en segundos según tiempo hasta el kick-off."""
        if minutos > 60:
            return self.interval_far_seg
        if minutos > 10:
            return self.interval_near_seg
        return self.interval_imminent_seg
