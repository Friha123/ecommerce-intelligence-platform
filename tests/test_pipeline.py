import json

import numpy as np
import pandas as pd

from ecommerce_intel.pipeline import build_app_data as bad
from ecommerce_intel.pipeline.install_artifacts import destination, install


def _fake_model1(n=300, seed=0):
    rng = np.random.default_rng(seed)
    states = np.array(["SP", "RJ", "BA"])
    cs, ss = rng.choice(states, n), rng.choice(states, n)
    ts = pd.Timestamp("2017-06-01") + pd.to_timedelta(rng.integers(0, 200 * 86400, n), unit="s")
    dd = rng.gamma(4, 3, n)
    return pd.DataFrame({
        "order_id": [f"o{i}" for i in range(n)], "order_purchase_timestamp": ts, "customer_state": cs, "seller_state": ss,
        "total_price": rng.uniform(20, 300, n), "total_freight": rng.uniform(5, 50, n), "delivery_days": dd,
        "promised_days": dd + rng.normal(8, 4, n), "same_state": (cs == ss).astype(int), "is_extreme_delivery": (dd > 60).astype(int),
        "distance_km": rng.uniform(10, 2000, n), "categorie_grouped": "other", "payment_type": "credit_card",
        "customer_lat": np.where(cs == "SP", -23.5, -12.9), "customer_lng": np.where(cs == "SP", -46.6, -38.5),
        "seller_lat": np.where(ss == "SP", -23.5, -22.9), "seller_lng": np.where(ss == "SP", -46.6, -43.2),
        "route_n_past": rng.integers(0, 100, n), "route_mean_days": rng.uniform(8, 20, n), "route_late_rate": rng.uniform(0, 0.2, n),
    })


def test_build_app_data_outputs(tmp_path):
    df = _fake_model1()
    bad.build_kpi(df, tmp_path)
    bad.build_geo_and_routes(df, tmp_path)
    bad.build_defaults(df, tmp_path)
    kpi = pd.read_csv(tmp_path / "kpi_month_state.csv")
    assert kpi["orders"].sum() == len(df) and (kpi["late_orders"] <= kpi["orders"]).all()
    hist = pd.read_csv(tmp_path / "delivery_hist.csv")
    assert hist["delivered"].sum() == len(df)
    cent = pd.read_csv(tmp_path / "state_centroids.csv")
    assert set(cent.columns) == {"state", "lat", "lng"} and set(cent["state"]) == {"SP", "RJ", "BA"}
    defaults = json.loads((tmp_path / "feature_defaults.json").read_text())
    assert "__modes__" in defaults and "__intra_state_distance_km__" in defaults and "total_price" in defaults
    routes = pd.read_csv(tmp_path / "route_stats.csv")
    assert {"seller_state", "customer_state", "route_mean_days"} <= set(routes.columns)


def test_customer_kpis(tmp_path):
    m3 = pd.DataFrame({"customer_unique_id": list("abcd"), "late_share": [0, 0, 0.3, 1.0], "avg_review_score": [5, 4, 3, 1],
                       "is_repeat_customer": [0, 1, 0, 0]})
    out = bad.build_customer_kpis(m3, tmp_path)
    rv = pd.read_csv(tmp_path / "review_by_lateness.csv")
    assert out["customers"] == 4 and rv["clients"].sum() == 4
    assert rv.sort_values("note_moyenne").iloc[0]["note_moyenne"] == 1


def test_install_routes_files(tmp_path):
    assert destination("model1_point_lgbm.txt", tmp_path / "a", tmp_path / "m") == tmp_path / "m"
    assert destination("model2_components.joblib", tmp_path / "a", tmp_path / "m") == tmp_path / "m"
    assert destination("model1_features.json", tmp_path / "a", tmp_path / "m") == tmp_path / "m"
    assert destination("model1_manifest.json", tmp_path / "a", tmp_path / "m") == tmp_path / "a"
    src = tmp_path / "src"
    src.mkdir()
    for n in ["model1_point_lgbm.txt", "model1_manifest.json", "customer_segments_final.csv"]:
        (src / n).write_text("x")
    done = dict(install([src], tmp_path / "a", tmp_path / "m"))
    assert done["model1_point_lgbm.txt"] == tmp_path / "m" and done["customer_segments_final.csv"] == tmp_path / "a"
