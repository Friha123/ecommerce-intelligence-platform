"""Dépendances FastAPI : authentification optionnelle par clé d'API et validation des états."""
from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from ecommerce_intel.api import store
from ecommerce_intel.utils.geo import STATE_NAMES

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="Requise uniquement si la variable ECI_API_KEY est définie")


def require_api_key(key: str | None = Security(_api_key_header)) -> None:
    """Si `ECI_API_KEY` est définie, toutes les routes `/api/v1` exigent l'en-tête `X-API-Key`."""
    expected = os.environ.get("ECI_API_KEY")
    if expected and not (key and secrets.compare_digest(key, expected)):
        raise HTTPException(status_code=401, detail="Clé d'API absente ou invalide (en-tête X-API-Key).")


def known_state_codes() -> list[str]:
    return sorted(set(store.kpi()["customer_state"].unique()) | set(store.centroids()["state"]))


def validate_states(*states: str) -> None:
    known = set(known_state_codes())
    unknown = [s for s in states if s.upper() not in known]
    if unknown:
        raise HTTPException(status_code=422, detail=f"État inconnu : {', '.join(unknown)}. États disponibles : {', '.join(sorted(known))}.")


def state_name(code: str) -> str:
    return STATE_NAMES.get(code, code)
