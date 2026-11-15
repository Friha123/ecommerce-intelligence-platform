"""Modèle 2 : pilotage des alertes de retard, fiabilité du score et évaluation d'une commande."""
from __future__ import annotations

from typing import Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ecommerce_intel.api import store
from ecommerce_intel.api.deps import require_api_key, validate_states
from ecommerce_intel.api.schemas import CurvePoint, OrderInput, RiskScoreOut, SteeringOut
from ecommerce_intel.api.serializers import M2_MONTHLY_LIFT, M2_ROLLING, M2_ROLLING_SUMMARY, frame_with_index, to_records, topk_columns
from ecommerce_intel.services import risk_service as rs

router = APIRouter(prefix="/api/v1/risk", tags=["Modèle 2 · Risque de retard"], dependencies=[Depends(require_api_key)])

Capacity = Query(0.10, ge=0.005, le=0.5, description="Part des commandes signalées (0,10 = 10 %)")


@router.get("/steering", response_model=SteeringOut, summary="Pilotage : métriques et bénéfice net pour une capacité et des coûts donnés")
def steering(capacity: float = Capacity,
             cost_fn: float = Query(5.0, gt=0, le=1000, description="Coût d'un retard non traité"),
             cost_fp: float = Query(1.0, gt=0, le=1000, description="Coût d'une fausse alerte"),
             prevent: float = Query(1.0, gt=0, le=1, description="Part des retards alertés réellement évités")) -> SteeringOut:
    scores = store.m2_scores()
    y, s = scores["is_late"].values, scores["score"].values
    m = rs.capacity_metrics(y, s, capacity)
    net = rs.net_benefit(m["tp"], m["fp"], cost_fn, cost_fp, prevent)
    be = rs.breakeven_precision(cost_fn, cost_fp, prevent)
    curve = rs.benefit_curve(y, s, np.linspace(0.01, 0.30, 30), cost_fn, cost_fp, prevent)
    best = rs.best_capacity(curve)
    points = [CurvePoint(capacity_pct=float(r["capacité (%)"]), net_benefit=float(r["bénéfice net"]), precision=float(r["précision"]),
                         recall=float(r["rappel"]), lift=float(r["gain"])) for _, r in curve.iterrows()]
    return SteeringOut(capacity=capacity, cost_fn=cost_fn, cost_fp=cost_fp, prevent_rate=prevent, n_orders=len(y), n_late=int(y.sum()),
                       n_flagged=m["n_flagged"], true_positives=m["tp"], false_positives=m["fp"], precision=m["precision"], recall=m["recall"],
                       lift=m["lift"], base_rate=m["base_rate"], net_benefit=net, breakeven_precision=be, profitable=net > 0,
                       best_capacity_pct=float(best["capacité (%)"]), best_net_benefit=float(best["bénéfice net"]), curve=points)


@router.get("/top-orders", summary="Commandes à surveiller en priorité (JSON ou CSV)")
def top_orders(capacity: float = Capacity, limit: int = Query(200, ge=1, le=100_000),
               format: Literal["json", "csv"] = "json"):
    top = rs.top_orders(store.m2_scores(), capacity, n=limit)
    out = top.assign(percentile=(top["rang_percentile"] * 100).round(2))[["order_id", "month", "score", "percentile", "is_late"]]
    if format == "csv":
        return Response(out.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=commandes_a_surveiller.csv"})
    return to_records(out)


@router.get("/reliability", summary="Fiabilité du score dans le temps et comparaison des approches")
def reliability(capacity: float = Capacity) -> dict:
    static = frame_with_index(store.m2_static(), "approche")
    return {"approach": store.m2_manifest().get("final_approach"),
            "monthly": to_records(rs.monthly_lift(store.m2_scores(), capacity), rename=M2_MONTHLY_LIFT),
            "rolling": to_records(store.m2_rolling(), rename=M2_ROLLING),
            "summary": to_records(frame_with_index(store.m2_rolling_summary(), "approche"), rename=M2_ROLLING_SUMMARY),
            "static_topk": to_records(static, rename=topk_columns(static))}


@router.post("/score", response_model=RiskScoreOut, summary="Score de risque d'une commande",
             responses={422: {"description": "Saisie invalide ou état inconnu"}, 503: {"description": "Modèle non disponible"}})
def score(order: OrderInput) -> RiskScoreOut:
    scorer = store.risk_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="Score unitaire indisponible (modèle de risque non installé ou approche non régressive).")
    validate_states(order.customer_state, order.seller_state)
    r = scorer.score(order.to_features())
    level, tone = rs.risk_level(r["score"], scorer.thresholds)
    return RiskScoreOut(**r, level=level, tone=tone, thresholds={k: float(v) for k, v in scorer.thresholds.items()})
