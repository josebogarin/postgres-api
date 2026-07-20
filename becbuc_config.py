"""
Configuracion global del sistema BECBUC.
Importar desde cualquier script: from becbuc_config import TORNEO_ID, BASE_URL, ...
"""

# ── Torneo activo ─────────────────────────────────────────────────────────────
TORNEO_ID   = 2                     # Copa del Mundo 2026
TORNEO_NOMBRE = "Copa del Mundo 2026"

# ── Servidor ──────────────────────────────────────────────────────────────────
BASE_URL    = "http://localhost:8000"

# ── Credenciales admin (sync, tests) ─────────────────────────────────────────
ADMIN_USER  = "Jose"
ADMIN_PASS  = "catalina"

# ── API-Football ──────────────────────────────────────────────────────────────
API_FOOTBALL_LEAGUE_ID = 1          # FIFA World Cup
API_FOOTBALL_SEASON    = 2026
