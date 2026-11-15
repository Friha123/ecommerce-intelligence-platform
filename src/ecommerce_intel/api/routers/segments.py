"""Modèle 3 : segments de clients, grille d'actions, ciblage et recherche d'un client."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ecommerce_intel.api import store
from ecommerce_intel.api.deps import require_api_key
from ecommerce_intel.api.schemas import CustomerOut, CustomersPage
from ecommerce_intel.api.serializers import M3_CUSTOMER, M3_GRID, M3_OVERVIEW, M3_VARIANTS, frame_with_index, to_records
from ecommerce_intel.services import segmentation_service as sg

router = APIRouter(prefix="/api/v1/segments", tags=["Modèle 3 · Segments clients"], dependencies=[Depends(require_api_key)])


def _customer(rec: dict) -> CustomerOut:
    return CustomerOut(**{k: rec.get(k) for k in CustomerOut.model_fields})


@router.get("/overview", summary="Segments, profils et répartition par région")
def overview() -> dict:
    seg = store.m3_segments()
    ov = sg.overview(seg)
    mix = sg.region_mix(seg).reset_index().melt(id_vars="region", var_name="segment", value_name="share_pct")
    return {"clients": len(seg), "segments": len(ov), "priority_clients": len(sg.priority_customers(seg)),
            "repeat_rate": float((seg["n_orders"] > 1).mean()), "overview": to_records(ov, rename=M3_OVERVIEW),
            "region_mix": to_records(mix)}


@router.get("/grid", summary="Grille d'actions « expérience × valeur »")
def grid() -> list[dict]:
    g = sg.grid_long(store.m3_grid_counts(), store.m3_grid_notes(), store.m3_action_grid())
    g["value_tier"] = g["value_tier"].astype(str)
    return to_records(g, rename=M3_GRID)


@router.get("/customers", response_model=CustomersPage, summary="Clients ciblés (filtres, pagination) ; `format=csv` exporte toute la sélection",
            responses={200: {"content": {"text/csv": {}}}})
def customers(region: list[str] = Query(default=[]), value_tier: list[str] = Query(default=[]), segment: list[str] = Query(default=[]),
              priority: bool = Query(False, description="Valeur élevée et note moyenne <= max_note"),
              late_only: bool = Query(False, description="Avec `priority` : seulement les clients touchés par un retard"),
              max_note: float = Query(2.0, ge=1, le=5), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
              format: Literal["json", "csv"] = "json"):
    sel = sg.filter_customers(store.m3_segments(), region, value_tier, segment)
    if priority:
        sel = sg.priority_customers(sel, max_note, late_only)
    if format == "csv":
        out = sel.head(100_000).rename(columns=M3_CUSTOMER)[list(M3_CUSTOMER.values())]
        return Response(out.to_csv(index=False), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=clients_cibles.csv"})
    page = sel.iloc[offset: offset + limit]
    return CustomersPage(total=len(sel), offset=offset, limit=limit,
                         median_spend=float(sel["monetary_total"].median()) if len(sel) else None,
                         avg_review=float(sel["avg_review_score"].mean()) if len(sel) else None,
                         items=[_customer(r) for r in to_records(page, rename=M3_CUSTOMER)])


@router.get("/customers/{customer_id}", response_model=CustomerOut, summary="Segment et action d'un client",
            responses={404: {"description": "Client inconnu"}})
def customer(customer_id: str) -> CustomerOut:
    row = sg.lookup_customer(store.m3_segments(), customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Client inconnu : {customer_id}")
    return _customer(to_records(row.to_frame().T, rename=M3_CUSTOMER)[0])


@router.get("/methodology", summary="Comparaison des variantes de segmentation (η², silhouette, stabilité)")
def methodology() -> dict:
    return {"variants": to_records(frame_with_index(store.m3_variants(), "variante"), rename=M3_VARIANTS), "manifest": store.m3_manifest()}
