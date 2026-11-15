"""Construction d'une ligne de variables pour le modèle, à partir des quelques informations saisies à l'écran.

Les modèles utilisent ~37 variables (distance, historique du trajet, calendrier...). L'utilisateur n'en saisit qu'une
dizaine ; le reste est complété ainsi :

* **géographie** : distance de Haversine entre les centroïdes des états du vendeur et du client (ou valeur saisie) ;
* **historique du trajet** (durée moyenne, taux de retard passés) : dernière valeur observée pour l'état vendeur → état client ;
* **historique du vendeur** et variables non saisies : médianes du jeu d'entraînement (`feature_defaults.json`).
"""
from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd

from ecommerce_intel.data import loaders
from ecommerce_intel.utils.geo import haversine_km

LOG_SOURCES = {"log_total_price": "total_price", "log_total_freight": "total_freight",
               "log_total_weight_g": "total_weight_g", "log_total_volume_cm3": "total_volume_cm3",
               "log_distance_km": "distance_km"}
ROUTE_COLS = ["route_n_past", "route_mean_days", "route_late_rate"]


class FeatureBuilder:
    def __init__(self, features: list[str], categorical: list[str], levels: dict[str, list[str]],
                 defaults: dict, centroids: pd.DataFrame, routes: pd.DataFrame):
        self.features = list(features)
        self.categorical = [c for c in categorical if c in self.features]
        self.levels = levels
        self.modes = defaults.get("__modes__", {})
        self.intra_km = float(defaults.get("__intra_state_distance_km__", 60.0))
        self.defaults = {k: v for k, v in defaults.items() if not k.startswith("__")}
        self.centroids = {r.state: (float(r.lat), float(r.lng)) for r in centroids.itertuples()}
        self.routes = {(r.seller_state, r.customer_state): {c: float(getattr(r, c)) for c in ROUTE_COLS if hasattr(r, c)}
                       for r in routes.itertuples()}

    # -- constructeurs --------------------------------------------------------------------------------------
    @classmethod
    def for_model1(cls) -> FeatureBuilder:
        cfg = loaders.load_m1_features()
        return cls(cfg["features"], cfg["categorical"], loaders.load_m1_levels(), loaders.load_feature_defaults(),
                   loaders.load_state_centroids(), loaders.load_route_stats())

    @classmethod
    def for_model2(cls) -> FeatureBuilder:
        cfg = loaders.load_m2_config()
        return cls(cfg["features"], list(cfg["levels"]), cfg["levels"], loaders.load_feature_defaults(),
                   loaders.load_state_centroids(), loaders.load_route_stats())

    # -- API ------------------------------------------------------------------------------------------------
    @property
    def known_states(self) -> list[str]:
        return sorted(set(self.levels.get("customer_state", [])) | set(self.centroids))

    def level_options(self, col: str) -> list[str]:
        return list(self.levels.get(col, []))

    def default_for(self, col: str, fallback: float = 0.0) -> float:
        v = self.defaults.get(col, fallback)
        return float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else fallback

    def build(self, inputs: dict) -> pd.DataFrame:
        inp = {k: v for k, v in inputs.items() if v is not None}
        v: dict = dict(self.defaults)
        for c in self.categorical:
            v[c] = inp.get(c, self.modes.get(c))
        v.update({k: x for k, x in inp.items() if k in self.features})

        dt = inp.get("purchase_datetime")
        if isinstance(dt, datetime):
            v.update(purchase_dow=dt.weekday(), purchase_hour=dt.hour, purchase_month=dt.month, is_weekend=int(dt.weekday() >= 5))

        cs, ss = inp.get("customer_state"), inp.get("seller_state")
        if cs in self.centroids:
            v["customer_lat"], v["customer_lng"] = self.centroids[cs]
        if ss in self.centroids:
            v["seller_lat"], v["seller_lng"] = self.centroids[ss]
        if cs and ss:
            v["same_state"] = int(cs == ss)
            if inp.get("distance_km") is not None:
                v["distance_km"], v["distance_imputed"] = float(inp["distance_km"]), 0
            elif cs == ss:
                v["distance_km"], v["distance_imputed"] = self.intra_km, 1
            elif cs in self.centroids and ss in self.centroids:
                (a, b), (c, d) = self.centroids[ss], self.centroids[cs]
                v["distance_km"], v["distance_imputed"] = haversine_km(a, b, c, d), 1
            v.update(self.routes.get((ss, cs), {}))

        price, freight = float(v.get("total_price", 0.0) or 0.0), float(v.get("total_freight", 0.0) or 0.0)
        v["freight_ratio"] = freight / max(price, 1.0)
        for log_col, src in LOG_SOURCES.items():
            if v.get(src) is not None:
                v[log_col] = math.log1p(max(float(v[src]), 0.0))

        row = {f: v.get(f, np.nan) for f in self.features}
        df = pd.DataFrame([row])
        for c in self.features:
            if c in self.categorical:
                values = df[c].astype(str)
                df[c] = pd.Categorical(values.where(values.isin(self.levels[c]), None), categories=self.levels[c])   # modalité inconnue -> NaN
            else:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
        return df
