# -*- coding: utf-8 -*-
"""
tools/db_env.py — Entorno portable para los scripts auxiliares de BECBUC.

Objetivo: que los scripts NO dependan de rutas absolutas (C:\\proyecto FAST API)
ni de credenciales hardcodeadas. Todo se deriva de:
  - la ubicacion de este archivo   -> PROJECT_ROOT
  - backend/.env                   -> credenciales de BD (una sola fuente de verdad)

Uso en un script:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz
    from tools.db_env import PROJECT_ROOT, becbuc_conn, appdb_conn
    conn = becbuc_conn()          # psycopg2 a la base 'becbuc'
"""
import os
import re
from pathlib import Path

# Raiz del proyecto = carpeta que contiene 'tools/'  (portable)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"


def env(name: str, default: str | None = None) -> str | None:
    """Lee una variable de backend/.env (o del entorno del proceso como fallback)."""
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(name + "="):
                val = line.split("=", 1)[1].strip()
                # quitar comillas y comentario inline
                if val and val[0] in "\"'":
                    val = val[1:].split(val[0], 1)[0]
                else:
                    val = val.split("#", 1)[0].strip()
                return val
    return os.environ.get(name, default)


def _pg_kwargs(url: str) -> dict:
    """Convierte una URL SQLAlchemy en kwargs de psycopg2.
    Ej: postgresql+asyncpg://user:pass@host:5432/db"""
    if not url:
        raise RuntimeError("URL de BD vacia: revisar backend/.env")
    m = re.match(r"^[^:]+://([^:]+):([^@]+)@([^:/]+):?(\d+)?/([^?]+)", url)
    if not m:
        raise RuntimeError(f"No se pudo parsear la URL de BD: {url[:40]}...")
    user, pw, host, port, db = m.groups()
    return dict(dbname=db, user=user, password=pw, host=host, port=int(port or 5432))


def becbuc_conn():
    """Conexion psycopg2 a la base del torneo (becbuc), credenciales desde .env."""
    import psycopg2
    return psycopg2.connect(**_pg_kwargs(env("DATABASE_BECBUC_URL")))


def appdb_conn():
    """Conexion psycopg2 a la base de usuarios (app_db), credenciales desde .env."""
    import psycopg2
    return psycopg2.connect(**_pg_kwargs(env("DATABASE_URL")))


if __name__ == "__main__":
    # Smoke test: imprime la config resuelta (sin exponer password).
    print("PROJECT_ROOT :", PROJECT_ROOT)
    print("ENV_FILE     :", ENV_FILE, "(existe)" if ENV_FILE.exists() else "(NO existe)")
    for var in ("DATABASE_BECBUC_URL", "DATABASE_URL"):
        u = env(var) or ""
        print(f"{var:20}: {re.sub(':[^@]+@', ':***@', u)}")
