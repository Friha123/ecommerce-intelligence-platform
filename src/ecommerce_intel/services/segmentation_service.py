"""Modèle 3 : segments de clients, grille d'actions et listes de ciblage."""
from __future__ import annotations

import pandas as pd

TIER_ORDER = ["valeur faible", "valeur moyenne", "valeur élevée"]


def overview(segments: pd.DataFrame) -> pd.DataFrame:
    g = segments.groupby("segment_experience").agg(
        clients=("customer_unique_id", "count"), note_moyenne=("avg_review_score", "mean"),
        livraison_j=("avg_delivery_days", "mean"), part_retard=("late_share", "mean"),
        montant_median=("monetary_total", "median"), recence_mediane_j=("recency_days", "median")).reset_index()
    g["part_clients"] = g["clients"] / g["clients"].sum() * 100
    return g.sort_values("clients", ascending=False).reset_index(drop=True)


def filter_customers(segments: pd.DataFrame, regions=None, tiers=None, segs=None) -> pd.DataFrame:
    out = segments
    if regions:
        out = out[out["region"].isin(regions)]
    if tiers:
        out = out[out["value_tier"].isin(tiers)]
    if segs:
        out = out[out["segment_experience"].isin(segs)]
    return out


def priority_customers(segments: pd.DataFrame, max_note: float = 2.0, late_only: bool = False) -> pd.DataFrame:
    """Clients de valeur élevée insatisfaits (note moyenne <= max_note), éventuellement touchés par un retard."""
    out = segments[(segments["value_tier"] == "valeur élevée") & (segments["avg_review_score"] <= max_note)]
    if late_only:
        out = out[out["late_share"] > 0]
    return out.sort_values(["avg_review_score", "monetary_total"], ascending=[True, False])


def lookup_customer(segments: pd.DataFrame, customer_id: str) -> pd.Series | None:
    row = segments[segments["customer_unique_id"].astype(str) == str(customer_id).strip()]
    return row.iloc[0] if len(row) else None


def region_mix(segments: pd.DataFrame) -> pd.DataFrame:
    return (pd.crosstab(segments["region"], segments["segment_experience"], normalize="index") * 100).round(1)


def grid_long(counts: pd.DataFrame, notes: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    c = counts.reset_index().melt(id_vars="segment_experience", var_name="value_tier", value_name="clients")
    n = notes.reset_index().melt(id_vars="segment_experience", var_name="value_tier", value_name="note")
    out = c.merge(n, on=["segment_experience", "value_tier"]).merge(actions.drop(columns=["clients"]), on=["segment_experience", "value_tier"], how="left")
    out["value_tier"] = pd.Categorical(out["value_tier"], TIER_ORDER, ordered=True)
    return out.sort_values(["segment_experience", "value_tier"]).reset_index(drop=True)
