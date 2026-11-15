"""Inférence : modèle de durée (point + quantiles) et score de risque de retard."""
from __future__ import annotations

import joblib
import lightgbm as lgb
import numpy as np

from ecommerce_intel.data import loaders
from ecommerce_intel.models.feature_builder import FeatureBuilder


def delivery_models_available() -> bool:
    try:
        cfg = loaders.load_m1_features()
    except loaders.DataNotFoundError:
        return False
    names = ["model1_point_lgbm.txt"] + [f"model1_quantile_{int(round(q * 100)):02d}_lgbm.txt" for q in cfg["quantiles"]]
    return loaders.models_available(*names, "model1_category_levels.json")


class DeliveryPredictor:
    """Durée de livraison prévue (jours) et quantiles associés (promesses possibles)."""

    def __init__(self) -> None:
        self.builder = FeatureBuilder.for_model1()
        cfg = loaders.load_m1_features()
        self.variant = cfg.get("variant", "")
        self.point = lgb.Booster(model_file=str(loaders.model_path("model1_point_lgbm.txt")))
        self.quantiles = {float(q): lgb.Booster(model_file=str(loaders.model_path(f"model1_quantile_{int(round(q * 100)):02d}_lgbm.txt")))
                          for q in cfg["quantiles"]}

    @property
    def uses_promise(self) -> bool:
        return "promised_days" in self.builder.features

    def predict(self, inputs: dict) -> dict:
        X = self.builder.build(inputs)
        q = {k: max(float(m.predict(X)[0]), 0.0) for k, m in sorted(self.quantiles.items())}
        vals = np.maximum.accumulate(list(q.values()))        # évite le croisement des quantiles
        return {"point": max(float(self.point.predict(X)[0]), 0.0), "quantiles": dict(zip(q.keys(), map(float, vals), strict=True))}


def risk_model_available() -> bool:
    return loaders.models_available("model2_components.joblib", "model2_config.json")


class RiskScorer:
    """Score de risque de retard : durée prédite moins promesse d'Olist (jours). Plus il est élevé, plus le risque est fort."""

    def __init__(self) -> None:
        self.builder = FeatureBuilder.for_model2()
        self.config = loaders.load_m2_config()
        comp = joblib.load(loaders.model_path("model2_components.joblib"))
        self.approach = comp.get("approach", "")
        self.reg = comp.get("reg")
        self.clf = comp.get("clf")

    @property
    def supported(self) -> bool:
        """Le score en jours (écart durée - promesse) repose sur un régresseur."""
        return self.reg is not None and self.clf is None

    @property
    def thresholds(self) -> dict:
        return self.config["thresholds_rank_on_test"]

    def score(self, inputs: dict) -> dict:
        if not self.supported:
            raise RuntimeError(f"Approche non prise en charge pour un score unitaire : {self.approach}")
        X = self.builder.build(inputs)
        promised = float(inputs.get("promised_days") or self.builder.default_for("promised_days", 20.0))
        predicted = float(self.reg.predict(X)[0])
        return {"predicted_days": predicted, "promised_days": promised, "score": predicted - promised}
