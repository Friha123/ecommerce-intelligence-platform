"""Santé, métadonnées et options de formulaire."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ecommerce_intel import __version__
from ecommerce_intel.api import store
from ecommerce_intel.api.deps import known_state_codes, require_api_key, state_name
from ecommerce_intel.api.schemas import HealthOut, MetaOut, OptionsOut, StateOut
from ecommerce_intel.config import get_settings
from ecommerce_intel.data.loaders import DataNotFoundError
from ecommerce_intel.models.predictors import delivery_models_available, risk_model_available

public = APIRouter(tags=["Santé"])
router = APIRouter(prefix="/api/v1", tags=["Méta"], dependencies=[Depends(require_api_key)])


@public.get("/health", response_model=HealthOut, summary="État du service")
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__, demo=get_settings().demo,
                     delivery_model=delivery_models_available(), risk_model=risk_model_available())


def _safe(fn) -> dict:
    try:
        return fn()
    except DataNotFoundError:
        return {}


@router.get("/meta", response_model=MetaOut, summary="Métadonnées des jeux de données et des modèles")
def meta() -> MetaOut:
    return MetaOut(app=_safe(store.app_manifest), delivery=_safe(store.m1_manifest), risk=_safe(store.m2_manifest),
                   segmentation=_safe(store.m3_manifest))


@router.get("/options", response_model=OptionsOut, summary="Valeurs proposées dans les formulaires")
def options() -> OptionsOut:
    predictor = store.delivery_predictor()
    builder = predictor.builder if predictor else None
    return OptionsOut(
        states=[StateOut(code=c, name=state_name(c)) for c in known_state_codes()],
        categories=builder.level_options("categorie_grouped") if builder else [],
        payment_types=builder.level_options("payment_type") if builder else [],
        delivery_model_available=predictor is not None,
        delivery_uses_promise=bool(predictor and predictor.uses_promise),
        risk_scoring_available=store.risk_scorer() is not None)
