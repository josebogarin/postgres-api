"""
Cliente HTTP para la API REST FastAPI.
Maneja autenticación JWT automáticamente (login, refresh, retry).
"""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


class APIClient:
    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")).rstrip("/")
        self._email = email or os.getenv("ADMIN_EMAIL", "")
        self._password = password or os.getenv("ADMIN_PASSWORD", "")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._client = httpx.Client(timeout=30)

    # ── Auth ─────────────────────────────────────────────────────────────────

    def login(self, email: str | None = None, password: str | None = None) -> dict:
        """Inicia sesión y guarda los tokens."""
        resp = self._client.post(
            f"{self.base_url}/auth/login",
            json={"email": email or self._email, "password": password or self._password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        return data

    def refresh(self) -> None:
        """Renueva el access token usando el refresh token."""
        if not self._refresh_token:
            raise RuntimeError("No hay refresh token. Llama login() primero.")
        resp = self._client.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self._refresh_token},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]

    def logout(self) -> None:
        self._access_token = None
        self._refresh_token = None

    @property
    def _headers(self) -> dict:
        if not self._access_token:
            raise RuntimeError("No autenticado. Llama login() primero.")
        return {"Authorization": f"Bearer {self._access_token}"}

    # ── Request con retry automático ─────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Hace la petición. Si recibe 401 renueva el token y reintenta."""
        url = f"{self.base_url}{path}"
        resp = self._client.request(method, url, headers=self._headers, **kwargs)
        if resp.status_code == 401 and self._refresh_token:
            self.refresh()
            resp = self._client.request(method, url, headers=self._headers, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    # ── Métodos HTTP ─────────────────────────────────────────────────────────

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: dict) -> Any:
        return self._request("POST", path, json=data)

    def patch(self, path: str, data: dict) -> Any:
        return self._request("PATCH", path, json=data)

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *_):
        self._client.close()

    def close(self):
        self._client.close()
