from datetime import datetime

import numpy as np
import pytest

from ecommerce_intel.models.feature_builder import FeatureBuilder
from ecommerce_intel.models.predictors import DeliveryPredictor, RiskScorer, delivery_models_available, risk_model_available
from ecommerce_intel.utils.geo import haversine_km


def test_haversine():
    assert haversine_km(-23.55, -46.63, -23.55, -46.63) == pytest.approx(0.0)
    assert haversine_km(-23.55, -46.63, -22.91, -43.17) == pytest.approx(360, rel=0.05)     # São Paulo - Rio


@pytest.fixture(scope="module")
def builder():
    return FeatureBuilder.for_model1()


def _inputs(b, **kw):
    s = b.known_states
    base = dict(customer_state=s[0], seller_state=s[1], total_price=120.0, total_freight=25.0, total_weight_g=1500.0,
                total_volume_cm3=8000.0, nb_items=1, purchase_datetime=datetime(2018, 6, 12, 14, 30))
    base.update(kw)
    return base


def test_feature_builder_schema(builder):
    X = builder.build(_inputs(builder))
    assert list(X.columns) == builder.features and len(X) == 1
    for c in builder.categorical:
        assert str(X[c].dtype) == "category" and list(X[c].cat.categories) == builder.levels[c]
    assert X["same_state"].iloc[0] == 0 and X["distance_km"].iloc[0] > 0
    assert X["purchase_dow"].iloc[0] == datetime(2018, 6, 12).weekday()
    assert X["freight_ratio"].iloc[0] == pytest.approx(25 / 120)
    assert X["log_total_price"].iloc[0] == pytest.approx(np.log1p(120))


def test_same_state_and_distance_override(builder):
    s = builder.known_states[0]
    X = builder.build(_inputs(builder, customer_state=s, seller_state=s))
    assert X["same_state"].iloc[0] == 1
    X2 = builder.build(_inputs(builder, distance_km=1234.0))
    assert X2["distance_km"].iloc[0] == 1234.0 and X2["distance_imputed"].iloc[0] == 0


@pytest.mark.skipif(not delivery_models_available(), reason="modèles de durée absents")
def test_delivery_predictor_quantiles_monotone():
    p = DeliveryPredictor()
    out = p.predict({**_inputs(p.builder), "promised_days": 25.0})
    qs = list(out["quantiles"].values())
    assert all(a <= b + 1e-9 for a, b in zip(qs, qs[1:], strict=False)) and out["point"] >= 0


@pytest.mark.skipif(not risk_model_available(), reason="modèle de risque absent")
def test_risk_scorer_score_is_gap():
    r = RiskScorer()
    if not r.supported:
        pytest.skip("approche non régressive")
    out = r.score({**_inputs(r.builder), "promised_days": 30.0})
    assert out["score"] == pytest.approx(out["predicted_days"] - 30.0)
