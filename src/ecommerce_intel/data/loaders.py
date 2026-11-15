"""Chargement des artefacts (tables agrégées, résultats d'évaluation, segments).

Chaque fonction lit un fichier produit par les notebooks 05a, 05b, 05c ou par
``ecommerce_intel.pipeline.build_app_data``. Aucun calcul lourd ici : la couche « services » transforme les tables.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ecommerce_intel.config import get_settings


class DataNotFoundError(FileNotFoundError):
    """Artefact manquant : message explicite pour l'utilisateur."""


def _path(name: str, models: bool = False) -> Path:
    s = get_settings()
    p = (s.models_dir if models else s.app_dir) / name
    if not p.exists():
        raise DataNotFoundError(
            f"Fichier introuvable : {p}. Exécutez les notebooks 05a/05b/05c puis `make install-artifacts` "
            "et `make app-data` (voir docs/DEPLOYMENT.md)."
        )
    return p


def _csv(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(_path(name), **kw)


def _json(name: str, models: bool = False) -> dict:
    return json.loads(_path(name, models).read_text(encoding="utf-8"))


def model_path(name: str) -> Path:
    return _path(name, models=True)


def models_available(*names: str) -> bool:
    d = get_settings().models_dir
    return all((d / n).exists() for n in names)


# ---- Tableaux de bord généraux (pipeline build_app_data) -------------------------------------------------
def load_kpi_month_state() -> pd.DataFrame:
    return _csv("kpi_month_state.csv")


def load_delivery_hist() -> pd.DataFrame:
    return _csv("delivery_hist.csv")


def load_state_centroids() -> pd.DataFrame:
    return _csv("state_centroids.csv")


def load_route_stats() -> pd.DataFrame:
    return _csv("route_stats.csv")


def load_feature_defaults() -> dict:
    return _json("feature_defaults.json")


def load_review_by_lateness() -> pd.DataFrame | None:
    try:
        return _csv("review_by_lateness.csv")
    except DataNotFoundError:
        return None


def load_app_manifest() -> dict:
    try:
        return _json("app_manifest.json")
    except DataNotFoundError:
        return {}


# ---- Modèle 1 -------------------------------------------------------------------------------------------
def load_m1_rolling_summary() -> pd.DataFrame:
    return _csv("model1_rolling_summary.csv")


def load_m1_mae_by_month() -> pd.DataFrame:
    return _csv("model1_mae_by_month.csv", index_col=0)


def load_m1_static() -> pd.DataFrame:
    return _csv("model1_static_test_fair.csv", index_col=0)


def load_m1_simulator() -> pd.DataFrame:
    return _csv("model1_promise_simulator.csv")


def load_m1_simulator_monthly() -> pd.DataFrame:
    return _csv("model1_promise_simulator_monthly.csv", index_col=0)


def load_m1_manifest() -> dict:
    return _json("model1_manifest.json")


def load_m1_features() -> dict:
    return _json("model1_features.json", models=True)


def load_m1_levels() -> dict:
    return _json("model1_category_levels.json", models=True)


# ---- Modèle 2 -------------------------------------------------------------------------------------------
def load_m2_scores() -> pd.DataFrame:
    return _csv("model2_test_scores.csv")


def load_m2_rolling_results() -> pd.DataFrame:
    return _csv("model2_rolling_results.csv")


def load_m2_rolling_summary() -> pd.DataFrame:
    return _csv("model2_rolling_summary.csv", index_col=0)


def load_m2_static_topk() -> pd.DataFrame:
    return _csv("model2_static_test_topk.csv", index_col=0)


def load_m2_manifest() -> dict:
    return _json("model2_manifest.json")


def load_m2_config() -> dict:
    return _json("model2_config.json", models=True)


# ---- Modèle 3 -------------------------------------------------------------------------------------------
def load_m3_segments() -> pd.DataFrame:
    return _csv("customer_segments_final.csv")


def load_m3_profiles() -> pd.DataFrame:
    return _csv("segment_profiles_final.csv")


def load_m3_action_grid() -> pd.DataFrame:
    return _csv("segment_action_grid.csv")


def load_m3_grid_counts() -> pd.DataFrame:
    return _csv("segment_grid_counts.csv", index_col=0)


def load_m3_grid_notes() -> pd.DataFrame:
    return _csv("segment_grid_notes.csv", index_col=0)


def load_m3_variants() -> pd.DataFrame:
    return _csv("segmentation_variants_comparison.csv", index_col=0)


def load_m3_manifest() -> dict:
    return _json("segmentation_manifest.json")
