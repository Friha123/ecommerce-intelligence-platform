"""Construit les tables légères de l'application à partir des jeux de données de modélisation.

Usage ::

    python -m ecommerce_intel.pipeline.build_app_data \\
        --model1 data/processed/model1_delivery_duration.csv \\
        --model3 data/processed/model3_customer_segmentation.csv \\
        --out data/app

Sorties (petites tables, versionnables) : ``kpi_month_state.csv``, ``delivery_hist.csv``, ``state_centroids.csv``,
``route_stats.csv``, ``feature_defaults.json``, ``review_by_lateness.csv``, ``app_manifest.json``.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

NON_FEATURES = {"order_id", "customer_unique_id", "order_purchase_timestamp", "split", "delivery_days", "log_delivery_days",
                "is_extreme_delivery", "baseline_state_median_days", "baseline_global_median_days"}
CATS = ["customer_state", "seller_state", "categorie_grouped", "payment_type"]


def build_kpi(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["month"] = pd.to_datetime(d["order_purchase_timestamp"]).dt.strftime("%Y-%m")
    d["late"] = (d["delivery_days"] > d["promised_days"]).astype(int)
    d["extreme"] = d["is_extreme_delivery"] if "is_extreme_delivery" in d else (d["delivery_days"] > 60).astype(int)
    agg = d.groupby(["month", "customer_state"]).agg(
        orders=("order_id", "count"), revenue=("total_price", "sum"), freight=("total_freight", "sum"),
        delivery_days_sum=("delivery_days", "sum"), promised_days_sum=("promised_days", "sum"),
        late_orders=("late", "sum"), extreme_orders=("extreme", "sum"), same_state_orders=("same_state", "sum")).reset_index()
    agg.to_csv(out / "kpi_month_state.csv", index=False)

    bins = np.arange(0, 61, 1)
    hist = pd.DataFrame({"day": bins[:-1],
                         "delivered": np.histogram(d["delivery_days"].clip(upper=59.99), bins=bins)[0],
                         "promised": np.histogram(d["promised_days"].clip(upper=59.99), bins=bins)[0]})
    hist.to_csv(out / "delivery_hist.csv", index=False)


def build_geo_and_routes(df: pd.DataFrame, out: Path) -> None:
    cust = df.groupby("customer_state")[["customer_lat", "customer_lng"]].median().rename(columns={"customer_lat": "lat", "customer_lng": "lng"})
    sell = df.groupby("seller_state")[["seller_lat", "seller_lng"]].median().rename(columns={"seller_lat": "lat", "seller_lng": "lng"})
    cent = cust.combine_first(sell).reset_index().rename(columns={"index": "state", "customer_state": "state"})
    cent.columns = ["state", "lat", "lng"]
    cent.to_csv(out / "state_centroids.csv", index=False)

    d = df.sort_values("order_purchase_timestamp")
    routes = d.groupby(["seller_state", "customer_state"])[["route_n_past", "route_mean_days", "route_late_rate"]].last().reset_index()
    routes.to_csv(out / "route_stats.csv", index=False)


def build_defaults(df: pd.DataFrame, out: Path) -> None:
    num = [c for c in df.select_dtypes("number").columns if c not in NON_FEATURES]
    defaults = {c: float(df[c].median()) for c in num}
    defaults["__modes__"] = {c: str(df[c].mode().iloc[0]) for c in CATS if c in df.columns}
    same = df[df["same_state"] == 1]["distance_km"]
    defaults["__intra_state_distance_km__"] = float(same.median()) if len(same) else 60.0
    (out / "feature_defaults.json").write_text(json.dumps(defaults, ensure_ascii=False, indent=1), encoding="utf-8")


def build_customer_kpis(m3: pd.DataFrame, out: Path) -> dict:
    bucket = pd.cut(m3["late_share"], [-0.001, 0.0, 0.5, 1.0], labels=["Jamais en retard", "Retard sur moins de la moitié des commandes", "Retard sur la moitié ou plus"])
    rv = m3.groupby(bucket, observed=True).agg(clients=("customer_unique_id", "count"), note_moyenne=("avg_review_score", "mean")).reset_index()
    rv.columns = ["groupe", "clients", "note_moyenne"]
    rv.to_csv(out / "review_by_lateness.csv", index=False)
    return {"customers": int(len(m3)), "repeat_rate_pct": float(m3["is_repeat_customer"].mean() * 100),
            "avg_review": float(m3["avg_review_score"].mean())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model1", required=True, type=Path, help="model1_delivery_duration.csv (sortie du notebook 03)")
    ap.add_argument("--model3", type=Path, help="model3_customer_segmentation.csv (optionnel)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--demo", action="store_true", help="marque les données comme synthétiques")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.model1, parse_dates=["order_purchase_timestamp"])
    build_kpi(df, a.out)
    build_geo_and_routes(df, a.out)
    build_defaults(df, a.out)
    manifest = {"demo": bool(a.demo), "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "orders": int(len(df)),
                "period": [str(df["order_purchase_timestamp"].min().date()), str(df["order_purchase_timestamp"].max().date())]}
    if a.model3 and a.model3.exists():
        manifest.update(build_customer_kpis(pd.read_csv(a.model3), a.out))
    (a.out / "app_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Tables écrites dans", a.out, ":", sorted(p.name for p in a.out.iterdir()))


if __name__ == "__main__":
    main()
