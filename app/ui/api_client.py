"""Client HTTP de l'API (httpx) : gestion d'erreurs lisibles pour l'interface."""
from __future__ import annotations

from typing import Any

import httpx


class ApiError(Exception):
    """Erreur renvoyée par l'API ou impossibilité de la joindre."""

    def __init__(self, detail: str, status_code: int | None = None):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _detail(r: httpx.Response) -> str:
    try:
        d = r.json().get("detail", r.text)
    except Exception:  # noqa: BLE001
        return r.text or f"Erreur HTTP {r.status_code}"
    if isinstance(d, list):                    # erreurs de validation Pydantic (422)
        return " ; ".join(f"{'.'.join(str(x) for x in e.get('loc', [])[1:])} : {e.get('msg', '')}" for e in d)
    return str(d)


class ApiClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 30.0):
        headers = {"X-API-Key": api_key} if api_key else {}
        self.base_url = base_url.rstrip("/")
        self._c = httpx.Client(base_url=self.base_url, timeout=timeout, headers=headers)

    def _send(self, method: str, path: str, **kw) -> httpx.Response:
        try:
            r = self._c.request(method, path, **kw)
        except httpx.HTTPError as exc:
            raise ApiError(f"API injoignable ({self.base_url}) : {exc}") from exc
        if r.status_code >= 400:
            raise ApiError(_detail(r), r.status_code)
        return r

    def get(self, path: str, **params: Any) -> Any:
        return self._send("GET", path, params={k: v for k, v in params.items() if v is not None}).json()

    def get_bytes(self, path: str, **params: Any) -> bytes:
        return self._send("GET", path, params={k: v for k, v in params.items() if v is not None}).content

    def post(self, path: str, payload: dict) -> Any:
        return self._send("POST", path, json=payload).json()
