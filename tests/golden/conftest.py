# conftest.py — aisla los tests golden del conftest async de backend/tests/.
# Agrega backend/ al sys.path para poder importar el paquete `app`.
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
