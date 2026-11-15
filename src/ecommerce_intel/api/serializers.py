"""Conversion des tables (DataFrames) en JSON : clés en anglais (snake_case), NaN → null."""
from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd


def to_records(df: pd.DataFrame, rename: dict[str, str] | None = None, columns: list[str] | None = None) -> list[dict[str, Any]]:
    """DataFrame → liste de dictionnaires JSON-compatibles (numpy → types natifs, NaN → null)."""
    out = df.rename(columns=rename or {})
    if columns:
        out = out[columns]
    return json.loads(out.to_json(orient="records", force_ascii=False))


# -- correspondance « libellé du notebook » -> clé d'API ------------------------------------------------------
M1_SUMMARY = {"méthode": "method", "type": "type", "MAE (tous les mois)": "mae_all_months", "MAE (mois du test)": "mae_test_months",
              "biais (tous)": "bias_all", "n": "n"}
M1_STATIC = {"modèle": "model", "MAE": "mae", "RMSE": "rmse", "R2": "r2", "MedAE": "medae", "Biais": "bias"}
SIM_MONTHLY = {"mois": "month", "Olist : taux de retard (%)": "olist_late_pct", "Olist : promesse (j)": "olist_promise_days",
               "Modèle : taux de retard (%)": "model_late_pct", "Modèle : promesse (j)": "model_promise_days"}
M2_ROLLING = {"mois": "month", "approche": "approach", "n": "n", "taux_retard": "late_rate", "ROC-AUC": "roc_auc", "PR-AUC": "pr_auc", "gain": "gain"}
M2_ROLLING_SUMMARY = {"approche": "approach", "ROC-AUC moyen": "roc_auc_mean", "PR-AUC moyenne": "pr_auc_mean", "gain moyen": "gain_mean",
                      "ROC-AUC min": "roc_auc_min"}
M2_MONTHLY_LIFT = {"mois": "month", "commandes": "orders", "taux_retard": "late_rate", "précision": "precision", "rappel": "recall", "gain": "gain"}
M3_OVERVIEW = {"segment_experience": "segment", "clients": "clients", "note_moyenne": "avg_review", "livraison_j": "avg_delivery_days",
               "part_retard": "late_share", "montant_median": "median_spend", "recence_mediane_j": "median_recency_days", "part_clients": "share_pct"}
M3_GRID = {"segment_experience": "segment", "value_tier": "value_tier", "clients": "clients", "note": "avg_review", "action": "action"}
M3_VARIANTS = {"variante": "variant", "description": "description", "k": "k", "silhouette": "silhouette", "davies_bouldin": "davies_bouldin",
               "stabilité_ARI": "stability_ari", "plus petit segment (%)": "smallest_segment_pct", "η² récence": "eta2_recency",
               "η² valeur": "eta2_value", "η² satisfaction": "eta2_satisfaction", "η² livraison": "eta2_delivery"}
M3_CUSTOMER = {"customer_unique_id": "customer_id", "segment_experience": "segment", "value_tier": "value_tier", "recency_tier": "recency_tier",
               "action": "action", "customer_state": "state", "region": "region", "n_orders": "n_orders", "monetary_total": "total_spent",
               "avg_order_value": "avg_order_value", "avg_review_score": "avg_review", "avg_delivery_days": "avg_delivery_days",
               "late_share": "late_share", "recency_days": "recency_days"}


def topk_columns(df: pd.DataFrame) -> dict[str, str]:
    """« précision top 10 % » -> precision_top10, « rappel top 5 % » -> recall_top5, etc."""
    m = {"approche": "approach", "ROC-AUC": "roc_auc", "PR-AUC": "pr_auc", "gain PR-AUC": "pr_auc_gain"}
    for c in df.columns:
        r = re.match(r"^(précision|rappel) top (\d+) %$", c)
        if r:
            m[c] = f"{'precision' if r.group(1) == 'précision' else 'recall'}_top{r.group(2)}"
    return m


def frame_with_index(df: pd.DataFrame, index_name: str) -> pd.DataFrame:
    out = df.copy()
    out.index.name = index_name
    return out.reset_index()
