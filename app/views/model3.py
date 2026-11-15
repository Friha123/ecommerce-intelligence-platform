"""Page 4 : modèle 3, segmentation des clients et grille d'actions — données servies par l'API FastAPI."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "src", _ROOT / "app"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import streamlit as st
from ui import api, charts
from ui.format import fmt_brl, fmt_int, fmt_num, fmt_ratio_pct
from ui.style import demo_banner, hero, insight, kpi_row

TIERS = ["valeur faible", "valeur moyenne", "valeur élevée"]


def tab_segments(ov, mix) -> None:
    left, right = st.columns([2, 3])
    with left:
        st.markdown("**Répartition des clients**")
        st.plotly_chart(charts.segment_donut(ov), width="stretch")
    with right:
        st.markdown("**Profil de chaque segment**")
        st.plotly_chart(charts.profile_bars(ov), width="stretch")
    st.dataframe(ov.rename(columns={"segment": "Segment", "clients": "Clients", "share_pct": "Part (%)", "avg_review": "Note moyenne",
                                    "avg_delivery_days": "Livraison (j)", "late_share": "Part en retard", "median_spend": "Montant médian (R$)",
                                    "median_recency_days": "Récence médiane (j)"}).round(2), hide_index=True, width="stretch")
    st.markdown("**Répartition des segments par région**")
    st.plotly_chart(charts.region_chart(mix), width="stretch")
    insight("Les segments se distinguent par l'**expérience vécue** (satisfaction et livraison). Avec une grande majorité de clients à achat unique, "
            "ils décrivent des profils d'expérience, pas une fidélité mesurée.")


def tab_grid() -> None:
    grid = api.segments_grid()
    st.markdown("Chaque case croise l'**expérience** du client et son **niveau de valeur** (terciles du montant dépensé) et propose une action.")
    st.plotly_chart(charts.grid_heatmap(grid), width="stretch")
    st.dataframe(grid.rename(columns={"segment": "Segment", "value_tier": "Valeur", "clients": "Clients", "avg_review": "Note moyenne",
                                      "action": "Action recommandée"}).round(2), hide_index=True, width="stretch")


def tab_targeting(regions_all, segments_all) -> None:
    c1, c2, c3 = st.columns(3)
    regions = c1.multiselect("Région", regions_all, placeholder="Toutes")
    tiers = c2.multiselect("Niveau de valeur", TIERS, placeholder="Tous")
    segs = c3.multiselect("Segment d'expérience", segments_all, placeholder="Tous")
    priority = st.toggle("Cible prioritaire : valeur élevée et note ≤ 2", value=False)
    late = st.checkbox("Seulement les clients touchés par un retard", value=False) if priority else False
    res = api.segments_customers(regions, tiers, segs, priority, late)
    total = res["total"]
    kpi_row([dict(label="Clients ciblés", value=fmt_int(total)),
             dict(label="Montant dépensé médian", value=fmt_brl(res["median_spend"]) if total else "n.d."),
             dict(label="Note moyenne", value=f"{fmt_num(res['avg_review'], 2)} / 5" if total else "n.d.")])
    cols = ["customer_id", "segment", "value_tier", "action", "region", "total_spent", "avg_review", "avg_delivery_days", "late_share"]
    st.dataframe(res["items"][cols] if total else res["items"], hide_index=True, width="stretch", height=320)
    st.caption("Affichage limité à 500 lignes ; le fichier CSV contient toute la sélection.")
    st.download_button("Télécharger la sélection (CSV)", api.segments_customers_csv(regions, tiers, segs, priority, late),
                       file_name="clients_cibles.csv", mime="text/csv")


def tab_lookup() -> None:
    st.markdown("Retrouvez le segment et l'action recommandée d'un client à partir de son identifiant (`GET /api/v1/segments/customers/{id}`).")
    sample = api.segments_customers(limit=3)["items"]
    if len(sample):
        st.caption("Exemples d'identifiants : " + ", ".join(f"`{c}`" for c in sample["customer_id"]))
    cid = st.text_input("Identifiant client (customer_unique_id)")
    if cid:
        row = api.segments_customer(cid)
        if row is None:
            st.warning("Identifiant inconnu.")
        else:
            kpi_row([dict(label="Segment", value=str(row["segment"])), dict(label="Valeur", value=str(row["value_tier"])),
                     dict(label="Note moyenne", value=f"{fmt_num(row['avg_review'], 1)} / 5"),
                     dict(label="Part de commandes en retard", value=fmt_ratio_pct(row["late_share"]))])
            insight(f"**Action recommandée :** {row['action']}")


def tab_method() -> None:
    st.markdown("**Trois variantes de segmentation ont été comparées.** η² mesure la part de variance de chaque dimension expliquée par les segments "
                "(0 = les segments ne distinguent pas cette dimension).")
    var = api.segments_methodology()["variants"]
    st.plotly_chart(charts.eta_chart(var), width="stretch")
    st.dataframe(var.round(3), hide_index=True, width="stretch")
    insight("La segmentation **d'expérience** est la plus stable ; elle ne capture ni la valeur ni la récence, d'où l'ajout d'une **dimension de valeur** "
            "par terciles pour construire la grille d'actions.")
    with st.expander("Limites"):
        st.markdown("- La grande majorité des clients n'achète qu'une fois : pas de segmentation de fidélité possible.\n"
                    "- La note moyenne, très polarisée, domine la séparation en groupes.")


def render() -> None:
    hero("👥", "Modèle 3 · Segments de clients", "Comprendre l'expérience vécue par les clients et cibler les actions selon leur valeur.")
    demo_banner()
    try:
        sm = api.segments_overview()
        ov, mix = sm["overview"], sm["region_mix"]
        kpi_row([dict(label="Clients analysés", value=fmt_int(sm["clients"])), dict(label="Segments d'expérience", value=str(sm["segments"])),
                 dict(label="Valeur élevée et insatisfaits", value=fmt_int(sm["priority_clients"]),
                      help=f"{fmt_num(sm['priority_clients'] / sm['clients'] * 100)} % des clients : cible prioritaire"),
                 dict(label="Achat répété", value=fmt_ratio_pct(sm["repeat_rate"]))])
        t1, t2, t3, t4, t5 = st.tabs(["🧩 Segments", "🧭 Grille d'actions", "🎯 Ciblage", "🔎 Rechercher un client", "📘 Méthode"])
        with t1:
            tab_segments(ov, mix)
        with t2:
            tab_grid()
        with t3:
            tab_targeting(sorted(mix["region"].unique()), sorted(ov["segment"].unique()))
        with t4:
            tab_lookup()
        with t5:
            tab_method()
    except api.ApiError as e:
        st.error(e.detail)


render()
