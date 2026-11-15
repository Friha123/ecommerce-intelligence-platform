"""Modèle 1 : promesse de livraison par quantile et performance de la prédiction de durée."""
from __future__ import annotations

import re

import pandas as pd

SIM_RENAME = {"promesse": "label", "durée promise moyenne (j)": "promise_days", "taux de retard (%)": "late_pct"}
QUANTILE_TEXT = {0.8: ("Équilibrée", "environ 1 commande sur 7 en retard"),
                 0.9: ("Prudente", "environ 1 commande sur 14 en retard"),
                 0.95: ("Très prudente", "environ 1 commande sur 25 en retard")}


def parse_simulator(sim: pd.DataFrame) -> pd.DataFrame:
    df = sim.rename(columns=SIM_RENAME).copy()
    df["is_olist"] = df["label"].str.contains("Olist", case=False)
    df["quantile"] = df["label"].str.extract(r"([0-9]*\.?[0-9]+)")[0].astype(float)
    df.loc[df["is_olist"], "quantile"] = float("nan")
    return df


def quantile_options(sim: pd.DataFrame) -> list[float]:
    return sorted(parse_simulator(sim).dropna(subset=["quantile"])["quantile"].tolist())


def compare_to_olist(sim: pd.DataFrame, q: float) -> dict:
    df = parse_simulator(sim)
    olist = df[df["is_olist"]].iloc[0]
    row = df[(~df["is_olist"]) & (df["quantile"].round(3) == round(q, 3))].iloc[0]
    d_days = row["promise_days"] - olist["promise_days"]
    d_late = row["late_pct"] - olist["late_pct"]
    if d_days <= 0 and d_late <= 0:
        verdict, tone = "Promesse plus courte et moins de retards qu'Olist", "good"
    elif d_days > 0 and d_late < 0:
        verdict, tone = f"Promesse plus longue de {abs(d_days):.1f} j, mais {abs(d_late):.1f} point(s) de retards en moins", "neutral"
    elif d_days < 0 and d_late > 0:
        verdict, tone = f"Promesse plus courte de {abs(d_days):.1f} j, au prix de {d_late:.1f} point(s) de retards en plus", "neutral"
    else:
        verdict, tone = "Plus longue et plus de retards qu'Olist : niveau à écarter", "bad"
    return {"promise_days": float(row["promise_days"]), "late_pct": float(row["late_pct"]),
            "olist_promise_days": float(olist["promise_days"]), "olist_late_pct": float(olist["late_pct"]),
            "delta_days": float(d_days), "delta_days_pct": float(d_days / olist["promise_days"] * 100),
            "delta_late_pts": float(d_late), "verdict": verdict, "tone": tone}


def monthly_for_quantile(monthly: pd.DataFrame, q: float) -> pd.DataFrame:
    p = f"q{int(round(q * 100))}"
    out = pd.DataFrame({
        "mois": monthly.index.astype(str),
        "Olist : taux de retard (%)": monthly["Olist : taux de retard (%)"].values,
        "Olist : promesse (j)": monthly["Olist : promesse (j)"].values,
        "Modèle : taux de retard (%)": monthly[f"{p} : taux de retard (%)"].values,
        "Modèle : promesse (j)": monthly[f"{p} : promesse (j)"].values})
    return out


def risk_label(q: float) -> tuple[str, str]:
    return QUANTILE_TEXT.get(round(q, 2), (f"Quantile {q:.2f}", ""))


def mae_overview(summary: pd.DataFrame) -> dict:
    """Gains du modèle retenu contre la meilleure baseline et contre la promesse d'Olist (évaluation glissante)."""
    col = "MAE (tous les mois)"
    base = summary[summary["type"] == "Baseline"]
    models = summary[summary["type"] != "Baseline"]
    best_model, best_base = models.sort_values(col).iloc[0], base[base["méthode"] != "Promesse d'Olist"].sort_values(col).iloc[0]
    promise = summary[summary["méthode"] == "Promesse d'Olist"].iloc[0]
    return {"model": best_model["méthode"], "model_mae": float(best_model[col]),
            "best_baseline": best_base["méthode"], "baseline_mae": float(best_base[col]),
            "gain_vs_baseline": float(best_base[col] - best_model[col]), "gain_vs_baseline_pct": float((best_base[col] - best_model[col]) / best_base[col] * 100),
            "promise_mae": float(promise[col]), "gain_vs_promise": float(promise[col] - best_model[col]),
            "gain_vs_promise_pct": float((promise[col] - best_model[col]) / promise[col] * 100)}


def clean_method_name(name: str) -> str:
    """« C · sans proxys ni promesse » -> « Variante C : sans proxys ni promesse »."""
    m = re.match(r"^([A-E]) · (.*)$", name)
    return f"Variante {m.group(1)} : {m.group(2)}" if m else name
