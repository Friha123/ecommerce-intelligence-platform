"""Accès aux artefacts avec cache mémoire (les tables sont petites : chargées une fois par processus)."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ecommerce_intel.data import loaders
from ecommerce_intel.models.predictors import DeliveryPredictor, RiskScorer, delivery_models_available, risk_model_available

_CACHED = []


def _cache(fn):
    wrapped = lru_cache(maxsize=None)(fn)
    _CACHED.append(wrapped)
    return wrapped


def clear_caches() -> None:
    """Force le rechargement des artefacts (après `make install-artifacts`)."""
    for fn in _CACHED:
        fn.cache_clear()


@_cache
def kpi() -> pd.DataFrame: return loaders.load_kpi_month_state()
@_cache
def histogram() -> pd.DataFrame: return loaders.load_delivery_hist()
@_cache
def centroids() -> pd.DataFrame: return loaders.load_state_centroids()
@_cache
def review_by_lateness() -> pd.DataFrame | None: return loaders.load_review_by_lateness()
@_cache
def app_manifest() -> dict: return loaders.load_app_manifest()

@_cache
def m1_summary() -> pd.DataFrame: return loaders.load_m1_rolling_summary()
@_cache
def m1_by_month() -> pd.DataFrame: return loaders.load_m1_mae_by_month()
@_cache
def m1_static() -> pd.DataFrame: return loaders.load_m1_static()
@_cache
def m1_simulator() -> pd.DataFrame: return loaders.load_m1_simulator()
@_cache
def m1_simulator_monthly() -> pd.DataFrame: return loaders.load_m1_simulator_monthly()
@_cache
def m1_manifest() -> dict: return loaders.load_m1_manifest()

@_cache
def m2_scores() -> pd.DataFrame: return loaders.load_m2_scores()
@_cache
def m2_rolling() -> pd.DataFrame: return loaders.load_m2_rolling_results()
@_cache
def m2_rolling_summary() -> pd.DataFrame: return loaders.load_m2_rolling_summary()
@_cache
def m2_static() -> pd.DataFrame: return loaders.load_m2_static_topk()
@_cache
def m2_manifest() -> dict: return loaders.load_m2_manifest()

@_cache
def m3_segments() -> pd.DataFrame: return loaders.load_m3_segments()
@_cache
def m3_grid_counts() -> pd.DataFrame: return loaders.load_m3_grid_counts()
@_cache
def m3_grid_notes() -> pd.DataFrame: return loaders.load_m3_grid_notes()
@_cache
def m3_action_grid() -> pd.DataFrame: return loaders.load_m3_action_grid()
@_cache
def m3_variants() -> pd.DataFrame: return loaders.load_m3_variants()
@_cache
def m3_manifest() -> dict: return loaders.load_m3_manifest()


@_cache
def delivery_predictor() -> DeliveryPredictor | None:
    return DeliveryPredictor() if delivery_models_available() else None


@_cache
def risk_scorer() -> RiskScorer | None:
    if not risk_model_available():
        return None
    scorer = RiskScorer()
    return scorer if scorer.supported else None
