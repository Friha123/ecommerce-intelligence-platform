"""Schémas Pydantic (entrées validées et sorties documentées dans OpenAPI)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- Méta
class HealthOut(BaseModel):
    status: str = Field(examples=["ok"])
    version: str
    demo: bool = Field(description="True si l'API sert le jeu de démonstration synthétique")
    delivery_model: bool = Field(description="Modèle de durée (LightGBM) disponible")
    risk_model: bool = Field(description="Modèle de score de risque disponible")


class StateOut(BaseModel):
    code: str
    name: str


class OptionsOut(BaseModel):
    states: list[StateOut]
    categories: list[str]
    payment_types: list[str]
    delivery_model_available: bool
    delivery_uses_promise: bool
    risk_scoring_available: bool


class MetaOut(BaseModel):
    app: dict[str, Any]
    delivery: dict[str, Any]
    risk: dict[str, Any]
    segmentation: dict[str, Any]


# ---------------------------------------------------------------- Saisie d'une commande
class OrderInput(BaseModel):
    """Commande à évaluer. Les informations non fournies sont remplacées par des valeurs typiques."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "customer_state": "RJ", "seller_state": "SP", "categorie_grouped": "bed_bath_table", "payment_type": "credit_card",
        "total_price": 120.0, "total_freight": 25.0, "total_weight_g": 1500, "total_volume_cm3": 8000, "nb_items": 1,
        "purchase_datetime": "2018-06-12T14:30:00", "promised_days": 24}})

    customer_state: str = Field(min_length=2, max_length=2, description="Code de l'état du client (ex. RJ)")
    seller_state: str = Field(min_length=2, max_length=2, description="Code de l'état du vendeur (ex. SP)")
    categorie_grouped: str | None = Field(default=None, description="Catégorie du premier article")
    payment_type: str | None = None
    total_price: float = Field(gt=0, le=100_000, description="Prix total des articles (R$)")
    total_freight: float = Field(default=0.0, ge=0, le=10_000, description="Frais de port (R$)")
    total_weight_g: float = Field(gt=0, le=500_000, description="Poids total (g)")
    total_volume_cm3: float = Field(gt=0, le=5_000_000, description="Volume total (cm³)")
    nb_items: int = Field(default=1, ge=1, le=50)
    purchase_datetime: datetime | None = Field(default=None, description="Date d'achat (défaut : maintenant)")
    promised_days: float | None = Field(default=None, gt=0, le=365, description="Promesse actuelle d'Olist (jours)")
    distance_km: float | None = Field(default=None, gt=0, le=10_000, description="Distance vendeur-client ; sinon estimée entre états")

    def to_features(self) -> dict[str, Any]:
        d = self.model_dump(exclude_none=True)
        d["customer_state"], d["seller_state"] = d["customer_state"].upper(), d["seller_state"].upper()
        d.setdefault("purchase_datetime", datetime.now())
        return d


# ---------------------------------------------------------------- KPI
class HeadlineOut(BaseModel):
    orders: int
    revenue: float
    avg_ticket: float
    avg_delivery_days: float
    avg_promised_days: float
    late_rate: float = Field(description="Proportion de commandes livrées après la date promise (0-1)")
    on_time_rate: float
    avg_gap_days: float = Field(description="Promesse moyenne − durée réelle moyenne (positif = en avance)")


class KpiSummaryOut(BaseModel):
    period: list[str]
    current: HeadlineOut
    previous: HeadlineOut | None = Field(description="Période précédente de même longueur, si l'historique le permet")


class KpiFiltersOut(BaseModel):
    months: list[str]
    states: list[StateOut]


# ---------------------------------------------------------------- Modèle 1
class QuantileDays(BaseModel):
    quantile: float
    days: float


class DeliveryPredictionOut(BaseModel):
    point_days: float = Field(description="Durée prévue (médiane), en jours")
    quantiles: list[QuantileDays] = Field(description="Promesses possibles par niveau de prudence")
    variant: str
    uses_promise: bool


class PromiseComparisonOut(BaseModel):
    quantile: float
    risk_label: str
    risk_description: str
    promise_days: float
    late_pct: float
    olist_promise_days: float
    olist_late_pct: float
    delta_days: float
    delta_days_pct: float
    delta_late_pts: float
    verdict: str
    tone: str
    monthly: list[dict[str, Any]]


# ---------------------------------------------------------------- Modèle 2
class CurvePoint(BaseModel):
    capacity_pct: float
    net_benefit: float
    precision: float
    recall: float
    lift: float


class SteeringOut(BaseModel):
    capacity: float
    cost_fn: float
    cost_fp: float
    prevent_rate: float
    n_orders: int
    n_late: int
    n_flagged: int
    true_positives: int
    false_positives: int
    precision: float
    recall: float
    lift: float
    base_rate: float
    net_benefit: float
    breakeven_precision: float
    profitable: bool
    best_capacity_pct: float
    best_net_benefit: float
    curve: list[CurvePoint]


class RiskScoreOut(BaseModel):
    predicted_days: float
    promised_days: float
    score: float = Field(description="Durée prédite − promesse (jours) ; plus il est élevé, plus le risque est fort")
    level: str = Field(examples=["Élevé"])
    tone: str
    thresholds: dict[str, float]


# ---------------------------------------------------------------- Modèle 3
class CustomerOut(BaseModel):
    customer_id: str
    segment: str
    value_tier: str
    recency_tier: str | None = None
    action: str
    state: str | None = None
    region: str | None = None
    n_orders: int | None = None
    total_spent: float | None = None
    avg_order_value: float | None = None
    avg_review: float | None = None
    avg_delivery_days: float | None = None
    late_share: float | None = None
    recency_days: float | None = None


class CustomersPage(BaseModel):
    total: int
    offset: int
    limit: int
    median_spend: float | None
    avg_review: float | None
    items: list[CustomerOut]
