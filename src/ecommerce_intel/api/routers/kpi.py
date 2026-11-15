"""Indicateurs clés : synthèse, tendances, états, délais, satisfaction."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from ecommerce_intel.api import store
from ecommerce_intel.api.deps import require_api_key, state_name, validate_states
from ecommerce_intel.api.schemas import HeadlineOut, KpiFiltersOut, KpiSummaryOut, StateOut
from ecommerce_intel.api.serializers import to_records
from ecommerce_intel.services import kpi_service as kpi

router = APIRouter(prefix="/api/v1/kpi", tags=["KPI"], dependencies=[Depends(require_api_key)])

StatesQuery = Query(default=[], description="Codes d'états du client ; vide = tous")


def _period(start: str | None, end: str | None) -> tuple[str, str]:
    months = sorted(store.kpi()["month"].unique())
    s, e = start or months[0], end or months[-1]
    if s not in months or e not in months or s > e:
        raise HTTPException(status_code=422, detail=f"Période invalide. Mois disponibles : de {months[0]} à {months[-1]} (format AAAA-MM).")
    return s, e


def _headline(h: kpi.Headline) -> HeadlineOut:
    return HeadlineOut(**asdict(h), on_time_rate=h.on_time_rate, avg_gap_days=h.avg_gap_days)


def _filtered(start, end, states):
    period = _period(start, end)
    if states:
        validate_states(*states)
    df = kpi.filter_df(store.kpi(), period, [s.upper() for s in states])
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune commande pour cette sélection.")
    return period, df


@router.get("/filters", response_model=KpiFiltersOut, summary="Mois et états disponibles")
def filters() -> KpiFiltersOut:
    df = store.kpi()
    return KpiFiltersOut(months=sorted(df["month"].unique()),
                         states=[StateOut(code=c, name=state_name(c)) for c in sorted(df["customer_state"].unique())])


@router.get("/summary", response_model=KpiSummaryOut, summary="Indicateurs de la période et de la période précédente")
def summary(start: str | None = None, end: str | None = None, states: list[str] = StatesQuery) -> KpiSummaryOut:
    period, df = _filtered(start, end, states)
    prev = kpi.previous_period(store.kpi(), period, [s.upper() for s in states])
    return KpiSummaryOut(period=list(period), current=_headline(kpi.headline(df)),
                         previous=_headline(kpi.headline(prev)) if prev is not None and not prev.empty else None)


@router.get("/trend", summary="Évolution mensuelle (commandes, chiffre d'affaires, durée, retards)")
def trend(start: str | None = None, end: str | None = None, states: list[str] = StatesQuery) -> list[dict]:
    _, df = _filtered(start, end, states)
    return to_records(kpi.monthly_trend(df))


@router.get("/states", summary="Indicateurs par état du client")
def by_state(start: str | None = None, end: str | None = None, states: list[str] = StatesQuery) -> list[dict]:
    _, df = _filtered(start, end, states)
    return to_records(kpi.state_table(df), rename={"customer_state": "state"})


@router.get("/insights", summary="Constats automatiques en français")
def insights(start: str | None = None, end: str | None = None, states: list[str] = StatesQuery) -> dict:
    _, df = _filtered(start, end, states)
    return {"insights": kpi.insights(df)}


@router.get("/histogram", summary="Histogramme des durées réelle et promise (jours)")
def histogram() -> list[dict]:
    return to_records(store.histogram())


@router.get("/centroids", summary="Centroïdes géographiques des états")
def centroids() -> list[dict]:
    return to_records(store.centroids())


@router.get("/satisfaction", summary="Note moyenne selon le retard vécu")
def satisfaction() -> dict:
    rv = store.review_by_lateness()
    man = store.app_manifest()
    return {"groups": to_records(rv, rename={"groupe": "group", "clients": "customers", "note_moyenne": "avg_review"}) if rv is not None else [],
            "customers": man.get("customers"), "repeat_rate_pct": man.get("repeat_rate_pct"), "avg_review": man.get("avg_review")}
