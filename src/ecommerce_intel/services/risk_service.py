"""Modèle 2 : pilotage des alertes de retard (capacité, coûts, rentabilité)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def capacity_metrics(y: np.ndarray, score: np.ndarray, share: float) -> dict:
    """Signale exactement la part `share` de commandes les plus risquées (rang sur le score)."""
    y, score = np.asarray(y).astype(int), np.asarray(score, float)
    n = max(int(round(len(y) * share)), 1)
    idx = np.argsort(-score, kind="stable")[:n]
    tp = int(y[idx].sum())
    base = float(y.mean()) if len(y) else 0.0
    precision = tp / n
    return {"n_flagged": n, "tp": tp, "fp": n - tp, "precision": precision,
            "recall": tp / max(int(y.sum()), 1), "lift": precision / base if base > 0 else float("nan"),
            "base_rate": base, "threshold": float(score[idx].min())}


def net_benefit(tp: int, fp: int, cost_fn: float, cost_fp: float, prevent: float) -> float:
    """Bénéfice par rapport à ne rien faire : part évitée × coût du retard manqué × TP − coût d'une fausse alerte × FP."""
    return prevent * cost_fn * tp - cost_fp * fp


def breakeven_precision(cost_fn: float, cost_fp: float, prevent: float) -> float:
    """Précision minimale pour qu'une alerte soit rentable."""
    denom = cost_fp + prevent * cost_fn
    return cost_fp / denom if denom > 0 else 1.0


def benefit_curve(y, score, shares, cost_fn, cost_fp, prevent) -> pd.DataFrame:
    rows = []
    for s in shares:
        m = capacity_metrics(y, score, s)
        rows.append({"capacité (%)": s * 100, "bénéfice net": net_benefit(m["tp"], m["fp"], cost_fn, cost_fp, prevent),
                     "précision": m["precision"], "rappel": m["recall"], "gain": m["lift"]})
    return pd.DataFrame(rows)


def best_capacity(curve: pd.DataFrame) -> pd.Series:
    return curve.loc[curve["bénéfice net"].idxmax()]


def top_orders(scores: pd.DataFrame, share: float, n: int = 200) -> pd.DataFrame:
    k = max(int(round(len(scores) * share)), 1)
    return scores.sort_values("score", ascending=False).head(min(k, n)).reset_index(drop=True)


def monthly_lift(scores: pd.DataFrame, share: float, min_orders: int = 50) -> pd.DataFrame:
    rows = []
    for month, g in scores.groupby("month"):
        if len(g) < min_orders or g["is_late"].sum() == 0:
            continue
        m = capacity_metrics(g["is_late"].values, g["score"].values, share)
        rows.append({"mois": month, "commandes": len(g), "taux_retard": m["base_rate"], "précision": m["precision"],
                     "rappel": m["recall"], "gain": m["lift"]})
    return pd.DataFrame(rows)


def risk_level(score: float, thresholds: dict) -> tuple[str, str]:
    """Niveau de risque d'une commande à partir des seuils de rang (top 5 / 10 / 20 %)."""
    if score >= thresholds["top_5"]:
        return "Critique", "bad"
    if score >= thresholds["top_10"]:
        return "Élevé", "warn"
    if score >= thresholds["top_20"]:
        return "Modéré", "neutral"
    return "Faible", "good"
