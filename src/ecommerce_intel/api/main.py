"""Application FastAPI : API REST versionnée du backend.

Lancement ::

    uvicorn ecommerce_intel.api.main:app --reload          # http://localhost:8000/docs

Variables d'environnement : ``ECI_APP_DIR`` / ``ECI_MODELS_DIR`` (données), ``ECI_API_KEY`` (clé d'API optionnelle),
``ECI_CORS_ORIGINS`` (origines autorisées, séparées par des virgules).
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ecommerce_intel import __version__
from ecommerce_intel.api import store
from ecommerce_intel.api.routers import delivery, health, kpi, risk, segments
from ecommerce_intel.data.loaders import DataNotFoundError

log = logging.getLogger("ecommerce_intel.api")

DESCRIPTION = """
API du projet **E-Commerce Intelligence Platform** (marketplace Olist).

* **KPI** : indicateurs logistiques filtrables (période, états).
* **Modèle 1** : promesse de livraison par quantile et prédiction de durée.
* **Modèle 2** : pilotage des alertes de retard (capacité, coûts, rentabilité) et score de risque.
* **Modèle 3** : segments de clients, grille d'actions, ciblage.

Toutes les routes métier sont sous `/api/v1`. Si `ECI_API_KEY` est définie, l'en-tête `X-API-Key` est requis.
"""

TAGS = [{"name": "Santé", "description": "Disponibilité du service"}, {"name": "Méta", "description": "Métadonnées et options"},
        {"name": "KPI", "description": "Vue d'ensemble"}, {"name": "Modèle 1 · Durée de livraison", "description": "Promesse et durée"},
        {"name": "Modèle 2 · Risque de retard", "description": "Alertes et score"}, {"name": "Modèle 3 · Segments clients", "description": "Segmentation"}]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Préchauffage : charge les tables et les modèles au démarrage (les erreurs n'empêchent pas le démarrage)."""
    for name, fn in [("kpi", store.kpi), ("delivery_predictor", store.delivery_predictor), ("risk_scorer", store.risk_scorer)]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            log.warning("Préchauffage de %s impossible : %s", name, exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="E-Commerce Intelligence Platform API", version=__version__, description=DESCRIPTION, openapi_tags=TAGS,
                  lifespan=lifespan, contact={"name": "E-Commerce Intelligence Platform"}, license_info={"name": "MIT"})

    origins = [o.strip() for o in os.environ.get("ECI_CORS_ORIGINS", "http://localhost:8501").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.middleware("http")
    async def timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
        return response

    @app.exception_handler(DataNotFoundError)
    async def missing_data(_: Request, exc: DataNotFoundError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get("/", include_in_schema=False)
    def root():
        return {"name": "E-Commerce Intelligence Platform API", "version": __version__, "docs": "/docs", "health": "/health"}

    app.include_router(health.public)
    for r in (health.router, kpi.router, delivery.router, risk.router, segments.router):
        app.include_router(r)
    return app


app = create_app()
