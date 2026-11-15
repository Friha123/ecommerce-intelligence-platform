"""Modèle 1 : promesse de livraison par quantile et prédiction de durée."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ecommerce_intel.api import store
from ecommerce_intel.api.deps import require_api_key, validate_states
from ecommerce_intel.api.schemas import DeliveryPredictionOut, OrderInput, PromiseComparisonOut, QuantileDays
from ecommerce_intel.api.serializers import M1_STATIC, M1_SUMMARY, SIM_MONTHLY, frame_with_index, to_records
from ecommerce_intel.services import delivery_service as ds

router = APIRouter(prefix="/api/v1/delivery", tags=["Modèle 1 · Durée de livraison"], dependencies=[Depends(require_api_key)])


@router.get("/simulator", summary="Compromis durée promise / taux de retard pour chaque quantile")
def simulator() -> dict:
    sim = ds.parse_simulator(store.m1_simulator())
    qs = ds.quantile_options(store.m1_simulator())
    return {"quantiles": qs,
            "levels": [{"quantile": q, "label": ds.risk_label(q)[0], "description": ds.risk_label(q)[1]} for q in qs],
            "points": to_records(sim, columns=["label", "quantile", "promise_days", "late_pct", "is_olist"])}


@router.get("/simulator/compare", response_model=PromiseComparisonOut, summary="Un niveau de prudence comparé à la promesse d'Olist")
def compare(quantile: float = Query(0.9, gt=0, lt=1, description="Quantile promis (ex. 0.9)")) -> PromiseComparisonOut:
    sim = store.m1_simulator()
    if round(quantile, 3) not in [round(q, 3) for q in ds.quantile_options(sim)]:
        raise HTTPException(status_code=422, detail=f"Quantile indisponible. Valeurs possibles : {ds.quantile_options(sim)}")
    c = ds.compare_to_olist(sim, quantile)
    label, desc = ds.risk_label(quantile)
    monthly = to_records(ds.monthly_for_quantile(store.m1_simulator_monthly(), quantile), rename=SIM_MONTHLY)
    return PromiseComparisonOut(quantile=quantile, risk_label=label, risk_description=desc, monthly=monthly, **c)


@router.get("/performance", summary="Erreur du modèle et des baselines (évaluation glissante et test statique)")
def performance() -> dict:
    summary, by_month = store.m1_summary(), store.m1_by_month()
    return {"overview": ds.mae_overview(summary),
            "summary": to_records(summary, rename=M1_SUMMARY),
            "by_month": {"months": [str(m) for m in by_month.index], "series": {c: [None if v != v else float(v) for v in by_month[c]] for c in by_month.columns}},
            "static_test": to_records(frame_with_index(store.m1_static(), "modèle"), rename=M1_STATIC)}


@router.post("/predict", response_model=DeliveryPredictionOut, summary="Prédire la durée de livraison d'une commande",
             responses={422: {"description": "Saisie invalide ou état inconnu"}, 503: {"description": "Modèle non installé"}})
def predict(order: OrderInput) -> DeliveryPredictionOut:
    predictor = store.delivery_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="Modèle de durée non installé (voir `make install-artifacts`).")
    validate_states(order.customer_state, order.seller_state)
    out = predictor.predict(order.to_features())
    return DeliveryPredictionOut(point_days=out["point"], variant=predictor.variant, uses_promise=predictor.uses_promise,
                                 quantiles=[QuantileDays(quantile=q, days=d) for q, d in out["quantiles"].items()])
