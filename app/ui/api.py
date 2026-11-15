"""Accès à l'API depuis les pages : client unique, cache Streamlit des GET, conversion en DataFrames.

* ``ECI_API_URL`` défini  -> API distante (``ECI_API_KEY`` si l'API exige une clé) ;
* sinon                   -> API intégrée (thread local), même contrat HTTP.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from ui.api_client import ApiClient, ApiError

__all__ = ["ApiError"]


def _secret(name: str) -> str | None:
    try:
        return st.secrets.get(name)
    except Exception:  # noqa: BLE001  (pas de fichier secrets.toml)
        return None


@st.cache_resource(show_spinner="Connexion à l'API…")
def client() -> ApiClient:
    url = os.environ.get("ECI_API_URL") or _secret("ECI_API_URL")
    key = os.environ.get("ECI_API_KEY") or _secret("ECI_API_KEY")
    if not url:
        from ui.embedded import start_embedded_api
        url = start_embedded_api()
    return ApiClient(url, key)


def mode() -> str:
    return "API distante" if (os.environ.get("ECI_API_URL") or _secret("ECI_API_URL")) else "API intégrée"


def _freeze(params: dict) -> tuple:
    return tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in params.items() if v is not None and v != []))


@st.cache_data(ttl=300, show_spinner=False)
def _get(path: str, params: tuple) -> Any:
    return client().get(path, **{k: list(v) if isinstance(v, tuple) else v for k, v in params})


def get(path: str, **params: Any) -> Any:
    return _get(path, _freeze(params))


@st.cache_data(ttl=300, show_spinner=False)
def _get_bytes(path: str, params: tuple) -> bytes:
    return client().get_bytes(path, **{k: list(v) if isinstance(v, tuple) else v for k, v in params})


def _df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def _payload(inputs: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in inputs.items() if v is not None}


# ---------------------------------------------------------------- Méta
@st.cache_data(ttl=30, show_spinner=False)
def health() -> dict:
    return client().get("/health")


def options() -> dict:
    return get("/api/v1/options")


# ---------------------------------------------------------------- KPI
def kpi_filters() -> dict:
    return get("/api/v1/kpi/filters")


def kpi_summary(period: tuple[str, str], states: list[str]) -> dict:
    return get("/api/v1/kpi/summary", start=period[0], end=period[1], states=list(states))


def kpi_trend(period, states) -> pd.DataFrame:
    return _df(get("/api/v1/kpi/trend", start=period[0], end=period[1], states=list(states)))


def kpi_states(period, states) -> pd.DataFrame:
    return _df(get("/api/v1/kpi/states", start=period[0], end=period[1], states=list(states)))


def kpi_insights(period, states) -> list[str]:
    return get("/api/v1/kpi/insights", start=period[0], end=period[1], states=list(states))["insights"]


def kpi_histogram() -> pd.DataFrame:
    return _df(get("/api/v1/kpi/histogram"))


def kpi_centroids() -> pd.DataFrame:
    return _df(get("/api/v1/kpi/centroids"))


def kpi_satisfaction() -> dict:
    d = get("/api/v1/kpi/satisfaction")
    return {**d, "groups": _df(d["groups"])}


# ---------------------------------------------------------------- Modèle 1
def delivery_simulator() -> dict:
    d = get("/api/v1/delivery/simulator")
    return {"quantiles": d["quantiles"], "levels": {x["quantile"]: x for x in d["levels"]}, "points": _df(d["points"])}


def delivery_compare(quantile: float) -> dict:
    d = get("/api/v1/delivery/simulator/compare", quantile=quantile)
    return {**d, "monthly": _df(d["monthly"])}


def delivery_performance() -> dict:
    d = get("/api/v1/delivery/performance")
    bm = pd.DataFrame(d["by_month"]["series"], index=d["by_month"]["months"])
    return {"overview": d["overview"], "summary": _df(d["summary"]), "by_month": bm, "static_test": _df(d["static_test"])}


def delivery_predict(inputs: dict) -> dict:
    return client().post("/api/v1/delivery/predict", _payload(inputs))


# ---------------------------------------------------------------- Modèle 2
def risk_steering(capacity: float, cost_fn: float, prevent: float, cost_fp: float = 1.0) -> dict:
    d = get("/api/v1/risk/steering", capacity=capacity, cost_fn=cost_fn, cost_fp=cost_fp, prevent=prevent)
    return {**d, "curve": _df(d["curve"])}


def risk_top_orders(capacity: float, limit: int = 200) -> pd.DataFrame:
    return _df(get("/api/v1/risk/top-orders", capacity=capacity, limit=limit))


def risk_top_orders_csv(capacity: float) -> bytes:
    return _get_bytes("/api/v1/risk/top-orders", _freeze({"capacity": capacity, "limit": 100000, "format": "csv"}))


def risk_reliability(capacity: float) -> dict:
    d = get("/api/v1/risk/reliability", capacity=capacity)
    return {"approach": d["approach"], **{k: _df(d[k]) for k in ("monthly", "rolling", "summary", "static_topk")}}


def risk_score(inputs: dict) -> dict:
    return client().post("/api/v1/risk/score", _payload(inputs))


# ---------------------------------------------------------------- Modèle 3
def segments_overview() -> dict:
    d = get("/api/v1/segments/overview")
    return {**d, "overview": _df(d["overview"]), "region_mix": _df(d["region_mix"])}


def segments_grid() -> pd.DataFrame:
    return _df(get("/api/v1/segments/grid"))


def _seg_params(region, value_tier, segment, priority, late_only, max_note) -> dict:
    return dict(region=list(region), value_tier=list(value_tier), segment=list(segment), priority=priority or None,
                late_only=late_only or None, max_note=max_note)


def segments_customers(region=(), value_tier=(), segment=(), priority=False, late_only=False, max_note=2.0, limit=500) -> dict:
    d = get("/api/v1/segments/customers", limit=limit, **_seg_params(region, value_tier, segment, priority, late_only, max_note))
    return {**d, "items": _df(d["items"])}


def segments_customers_csv(region=(), value_tier=(), segment=(), priority=False, late_only=False, max_note=2.0) -> bytes:
    p = _seg_params(region, value_tier, segment, priority, late_only, max_note)
    return _get_bytes("/api/v1/segments/customers", _freeze({**p, "format": "csv"}))


def segments_customer(customer_id: str) -> dict | None:
    try:
        return client().get(f"/api/v1/segments/customers/{customer_id.strip()}")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


def segments_methodology() -> dict:
    d = get("/api/v1/segments/methodology")
    return {**d, "variants": _df(d["variants"])}
