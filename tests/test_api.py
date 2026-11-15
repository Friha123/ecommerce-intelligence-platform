"""Tests de l'API FastAPI (contrat, validation, erreurs, authentification) sur le jeu de démonstration."""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ecommerce_intel.api import store
from ecommerce_intel.api.main import create_app

ORDER = {"customer_state": "BA", "seller_state": "SP", "total_price": 120, "total_freight": 25, "total_weight_g": 1500,
         "total_volume_cm3": 8000, "nb_items": 1, "purchase_datetime": "2018-06-12T14:30:00", "promised_days": 24}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


# ---------------------------------------------------------------- Méta
def test_health_and_root(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["demo"] is True and h["delivery_model"] and h["risk_model"]
    assert client.get("/").json()["docs"] == "/docs"
    assert "X-Process-Time-Ms" in client.get("/health").headers


def test_openapi_contract(client):
    spec = client.get("/openapi.json").json()
    for p in ["/health", "/api/v1/kpi/summary", "/api/v1/delivery/predict", "/api/v1/risk/steering", "/api/v1/segments/customers/{customer_id}"]:
        assert p in spec["paths"]
    assert "OrderInput" in spec["components"]["schemas"]
    assert {t["name"] for t in spec["tags"]} >= {"KPI", "Santé"}


def test_options_and_meta(client):
    o = client.get("/api/v1/options").json()
    assert {"code": "SP", "name": "São Paulo"} in o["states"] and o["delivery_model_available"] and o["risk_scoring_available"]
    assert o["categories"] and o["payment_types"]
    assert set(client.get("/api/v1/meta").json()) == {"app", "delivery", "risk", "segmentation"}


# ---------------------------------------------------------------- KPI
def test_kpi_summary_and_filters(client):
    months = client.get("/api/v1/kpi/filters").json()["months"]
    s = client.get("/api/v1/kpi/summary").json()
    assert s["current"]["orders"] > 0 and 0 <= s["current"]["late_rate"] <= 1
    assert s["current"]["on_time_rate"] == pytest.approx(1 - s["current"]["late_rate"])
    assert s["previous"] is None                                         # période complète : pas d'historique antérieur
    s2 = client.get("/api/v1/kpi/summary", params={"start": months[2], "end": months[3]}).json()
    assert s2["previous"] is not None and s2["period"] == [months[2], months[3]]
    one = client.get("/api/v1/kpi/summary", params={"states": ["SP"]}).json()
    assert one["current"]["orders"] < s["current"]["orders"]


def test_kpi_tables(client):
    trend = client.get("/api/v1/kpi/trend").json()
    assert trend and {"month", "orders", "late_rate_pct"} <= set(trend[0])
    assert {"state", "state_name", "share_orders_pct"} <= set(client.get("/api/v1/kpi/states").json()[0])
    assert len(client.get("/api/v1/kpi/insights").json()["insights"]) >= 3
    assert {"day", "delivered", "promised"} <= set(client.get("/api/v1/kpi/histogram").json()[0])
    assert {"state", "lat", "lng"} <= set(client.get("/api/v1/kpi/centroids").json()[0])
    assert "groups" in client.get("/api/v1/kpi/satisfaction").json()


def test_kpi_validation_errors(client):
    assert client.get("/api/v1/kpi/summary", params={"start": "1999-01"}).status_code == 422
    r = client.get("/api/v1/kpi/summary", params={"states": ["XX"]})
    assert r.status_code == 422 and "inconnu" in r.json()["detail"]


# ---------------------------------------------------------------- Modèle 1
def test_delivery_simulator_and_compare(client):
    sim = client.get("/api/v1/delivery/simulator").json()
    q = sim["quantiles"][-1]
    assert any(p["is_olist"] for p in sim["points"]) and {lv["quantile"] for lv in sim["levels"]} == set(sim["quantiles"])
    c = client.get("/api/v1/delivery/simulator/compare", params={"quantile": q}).json()
    assert c["tone"] in {"good", "neutral", "bad"} and c["monthly"] and "model_late_pct" in c["monthly"][0]
    assert c["delta_days"] == pytest.approx(c["promise_days"] - c["olist_promise_days"])
    assert client.get("/api/v1/delivery/simulator/compare", params={"quantile": 0.123}).status_code == 422
    assert client.get("/api/v1/delivery/simulator/compare", params={"quantile": 1.5}).status_code == 422


def test_delivery_performance(client):
    p = client.get("/api/v1/delivery/performance").json()
    assert p["overview"]["gain_vs_promise"] == pytest.approx(p["overview"]["promise_mae"] - p["overview"]["model_mae"])
    assert {"method", "type", "mae_all_months"} <= set(p["summary"][0])
    assert len(p["by_month"]["months"]) > 0 and p["static_test"][0]["model"]


def test_delivery_predict(client):
    r = client.post("/api/v1/delivery/predict", json=ORDER)
    assert r.status_code == 200
    d = r.json()
    qs = [x["days"] for x in d["quantiles"]]
    assert d["point_days"] >= 0 and qs == sorted(qs)


@pytest.mark.parametrize("patch", [{"customer_state": "ZZ"}, {"total_price": -5}, {"total_weight_g": 0}, {"nb_items": 0},
                                   {"customer_state": "S"}, {"promised_days": 1000}])
def test_delivery_predict_rejects_invalid_orders(client, patch):
    r = client.post("/api/v1/delivery/predict", json={**ORDER, **patch})
    assert r.status_code == 422 and r.json()["detail"]


def test_predict_missing_required_field(client):
    body = {k: v for k, v in ORDER.items() if k != "total_price"}
    assert client.post("/api/v1/delivery/predict", json=body).status_code == 422


# ---------------------------------------------------------------- Modèle 2
def test_risk_steering_consistency(client):
    r = client.get("/api/v1/risk/steering", params={"capacity": 0.1, "cost_fn": 5, "prevent": 1.0}).json()
    assert r["n_flagged"] == pytest.approx(round(r["n_orders"] * 0.1), abs=1)
    assert r["true_positives"] + r["false_positives"] == r["n_flagged"]
    assert r["net_benefit"] == pytest.approx(5 * r["true_positives"] - r["false_positives"])
    assert r["breakeven_precision"] == pytest.approx(1 / 6) and r["profitable"] == (r["net_benefit"] > 0)
    assert len(r["curve"]) == 30 and r["best_net_benefit"] == max(p["net_benefit"] for p in r["curve"])


def test_risk_steering_validation(client):
    assert client.get("/api/v1/risk/steering", params={"capacity": 0.9}).status_code == 422
    assert client.get("/api/v1/risk/steering", params={"prevent": 0}).status_code == 422
    assert client.get("/api/v1/risk/steering", params={"cost_fn": -1}).status_code == 422


def test_risk_top_orders_json_and_csv(client):
    top = client.get("/api/v1/risk/top-orders", params={"capacity": 0.1, "limit": 5}).json()
    scores = [t["score"] for t in top]
    assert len(top) <= 5 and scores == sorted(scores, reverse=True)
    r = client.get("/api/v1/risk/top-orders", params={"capacity": 0.1, "format": "csv"})
    assert r.headers["content-type"].startswith("text/csv") and r.text.splitlines()[0] == "order_id,month,score,percentile,is_late"


def test_risk_reliability_and_score(client):
    rel = client.get("/api/v1/risk/reliability").json()
    assert rel["rolling"] and {"approach", "roc_auc_mean", "gain_mean"} <= set(rel["summary"][0])
    assert any(k.startswith("precision_top") for k in rel["static_topk"][0])
    s = client.post("/api/v1/risk/score", json=ORDER)
    assert s.status_code == 200
    d = s.json()
    assert d["score"] == pytest.approx(d["predicted_days"] - d["promised_days"]) and d["level"] in {"Critique", "Élevé", "Modéré", "Faible"}
    assert set(d["thresholds"]) == {"top_5", "top_10", "top_20"}
    assert client.post("/api/v1/risk/score", json={**ORDER, "seller_state": "QQ"}).status_code == 422


# ---------------------------------------------------------------- Modèle 3
def test_segments_overview_and_grid(client):
    o = client.get("/api/v1/segments/overview").json()
    assert o["clients"] > 0 and sum(s["share_pct"] for s in o["overview"]) == pytest.approx(100)
    assert {"region", "segment", "share_pct"} <= set(o["region_mix"][0])
    assert {"segment", "value_tier", "clients", "avg_review", "action"} <= set(client.get("/api/v1/segments/grid").json()[0])
    assert client.get("/api/v1/segments/methodology").json()["variants"]


def test_segments_customers_pagination_and_filters(client):
    p1 = client.get("/api/v1/segments/customers", params={"limit": 5}).json()
    p2 = client.get("/api/v1/segments/customers", params={"limit": 5, "offset": 5}).json()
    assert p1["total"] == p2["total"] and len(p1["items"]) == 5 and p1["items"][0]["customer_id"] != p2["items"][0]["customer_id"]
    prio = client.get("/api/v1/segments/customers", params={"priority": True, "limit": 1000}).json()
    assert all(c["value_tier"] == "valeur élevée" and c["avg_review"] <= 2 for c in prio["items"])
    tier = client.get("/api/v1/segments/customers", params={"value_tier": ["valeur faible"], "limit": 50}).json()
    assert all(c["value_tier"] == "valeur faible" for c in tier["items"])
    assert client.get("/api/v1/segments/customers", params={"limit": 5000}).status_code == 422


def test_segments_csv_and_lookup(client):
    r = client.get("/api/v1/segments/customers", params={"format": "csv"})
    assert r.headers["content-type"].startswith("text/csv") and r.text.startswith("customer_id,segment")
    cid = client.get("/api/v1/segments/customers", params={"limit": 1}).json()["items"][0]["customer_id"]
    one = client.get(f"/api/v1/segments/customers/{cid}")
    assert one.status_code == 200 and one.json()["customer_id"] == cid and one.json()["action"]
    assert client.get("/api/v1/segments/customers/inconnu-123").status_code == 404


# ---------------------------------------------------------------- Authentification et erreurs
def test_api_key_protection(monkeypatch):
    monkeypatch.setenv("ECI_API_KEY", "secret")
    with TestClient(create_app()) as c:
        assert c.get("/health").status_code == 200                                         # santé publique
        assert c.get("/api/v1/kpi/filters").status_code == 401
        assert c.get("/api/v1/kpi/filters", headers={"X-API-Key": "mauvaise"}).status_code == 401
        assert c.get("/api/v1/kpi/filters", headers={"X-API-Key": "secret"}).status_code == 200
        assert c.post("/api/v1/delivery/predict", json=ORDER).status_code == 401


def test_missing_artifact_returns_503(monkeypatch, tmp_path):
    demo = Path(__file__).resolve().parents[1] / "data" / "demo" / "app"
    shutil.copy(demo / "kpi_month_state.csv", tmp_path / "kpi_month_state.csv")          # sentinelle présente, le reste absent
    monkeypatch.setenv("ECI_APP_DIR", str(tmp_path))
    monkeypatch.setenv("ECI_MODELS_DIR", str(tmp_path / "models"))
    store.clear_caches()
    try:
        with TestClient(create_app()) as c:
            r = c.get("/api/v1/kpi/histogram")
            assert r.status_code == 503 and "introuvable" in r.json()["detail"]
            assert c.get("/api/v1/kpi/filters").status_code == 200                           # ce qui existe continue de fonctionner
            assert c.post("/api/v1/delivery/predict", json=ORDER).status_code == 503
    finally:
        monkeypatch.undo()
        store.clear_caches()
