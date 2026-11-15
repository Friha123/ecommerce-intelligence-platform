"""Page 3 : modèle 2, risque de retard (pilotage des alertes) — données et score via l'API FastAPI."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "src", _ROOT / "app"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np
import pandas as pd
import streamlit as st
from ui import api, charts
from ui.format import fmt_int, fmt_num, fmt_ratio_pct, signed
from ui.forms import order_form
from ui.style import demo_banner, hero, insight, kpi_row, pill


def tab_steering() -> None:
    st.markdown("Le score de risque est **la durée prédite moins la promesse d'Olist** (en jours) : plus il est élevé, plus la commande risque d'arriver en retard. "
                "On signale les commandes **les plus risquées**, dans la limite de la capacité de traitement de l'équipe.")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        capacity = c1.slider("Capacité de traitement (% des commandes signalées)", 1, 30, 10) / 100
        cost_fn = c2.slider("Coût d'un retard non traité (en multiples d'une fausse alerte)", 1, 40, 5,
                            help="1 = une fausse alerte coûte autant qu'un retard manqué.")
        prevent = c3.slider("Part des retards alertés réellement évités (%)", 10, 100, 100, step=10,
                            help="Une alerte (relance du vendeur, suivi du colis) n'évite pas toujours le retard.") / 100
    m = api.risk_steering(capacity, float(cost_fn), prevent)
    net, be = m["net_benefit"], m["breakeven_precision"]
    kpi_row([
        dict(label="Commandes à traiter", value=fmt_int(m["n_flagged"]), help=f"{fmt_num(capacity * 100, 0)} % de {fmt_int(m['n_orders'])} commandes"),
        dict(label="Retards détectés", value=fmt_ratio_pct(m["recall"]), help=f"{fmt_int(m['true_positives'])} retards sur {fmt_int(m['n_late'])}"),
        dict(label="Précision des alertes", value=fmt_ratio_pct(m["precision"]), help=f"Rentabilité à partir de {fmt_ratio_pct(be)}",
             delta=f"Gain x{fmt_num(m['lift'])} vs hasard", tone="good" if m["lift"] > 1.5 else "neutral"),
        dict(label="Bénéfice net", value=signed(net, 0), tone="good" if net > 0 else "bad",
             delta="Alertes rentables" if m["profitable"] else "Alertes non rentables", help="Unités de coût, comparé à ne rien faire"),
    ])
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Bénéfice net selon la capacité de traitement**")
        st.plotly_chart(charts.benefit_curve_chart(m["curve"], capacity * 100, m["best_capacity_pct"]), width="stretch")
    with right:
        st.markdown("**Lecture**")
        insight(f"Avec ces hypothèses, la capacité la plus rentable est **{fmt_num(m['best_capacity_pct'], 0)} %** des commandes "
                f"(bénéfice net {signed(m['best_net_benefit'], 0)}).")
        insight(f"Une alerte est rentable si sa précision dépasse **{fmt_ratio_pct(be)}** ; elle est de **{fmt_ratio_pct(m['precision'])}** ici "
                f"(taux de retard de base : {fmt_ratio_pct(m['base_rate'])}).")
        pill("Rentable" if m["profitable"] else "Non rentable", "good" if m["profitable"] else "bad")
        st.caption("Coûts et part de retards évités sont des **hypothèses** à calibrer avec l'équipe logistique.")

    st.markdown("#### Commandes à surveiller en priorité")
    top = api.risk_top_orders(capacity, limit=200)
    show = pd.DataFrame({"Commande": top["order_id"], "Mois": top["month"], "Score (jours)": top["score"].round(2),
                         "Percentile": top["percentile"].round(1), "Issue réelle": np.where(top["is_late"] == 1, "En retard", "À l'heure")})
    st.dataframe(show, hide_index=True, width="stretch", height=300)
    st.download_button("Télécharger la liste complète (CSV)", api.risk_top_orders_csv(capacity), file_name="commandes_a_surveiller.csv", mime="text/csv")


def tab_reliability() -> None:
    st.markdown("**Le score reste-t-il fiable dans le temps ?** Chaque mois est évalué avec des modèles entraînés sur les mois précédents.")
    share = st.select_slider("Capacité pour le suivi mensuel", options=[0.05, 0.10, 0.20], value=0.10, format_func=lambda v: f"top {int(v * 100)} %")
    rel = api.risk_reliability(share)
    ml = rel["monthly"]
    left, right = st.columns(2)
    with left:
        st.markdown("**Approche retenue : gain et rappel par mois**")
        if ml.empty:
            st.info("Pas assez de commandes par mois pour ce suivi.")
        else:
            st.plotly_chart(charts.lift_monthly_chart(ml), width="stretch")
    with right:
        st.markdown("**Comparaison des 6 approches (ROC-AUC par mois)**")
        st.plotly_chart(charts.approaches_chart(rel["rolling"], "roc_auc"), width="stretch")
    st.markdown(f"**Résumé de l'évaluation glissante** (approche retenue : {rel['approach'] or 'n.d.'})")
    st.dataframe(rel["summary"].rename(columns={"approach": "Approche", "roc_auc_mean": "ROC-AUC moyen", "pr_auc_mean": "PR-AUC moyenne",
                                                "gain_mean": "Gain moyen", "roc_auc_min": "ROC-AUC minimum"}).round(3),
                 hide_index=True, width="stretch")
    st.markdown("**Évaluation statique à capacité égale (test)**")
    st.dataframe(rel["static_topk"].round(3), hide_index=True, width="stretch")
    insight("La **régression de l'écart durée − promesse** est plus stable et plus performante que le classifieur direct : "
            "la durée est une cible plus riche qu'un simple indicateur retard / pas de retard.")


def tab_single() -> None:
    opts = api.options()
    if not opts["risk_scoring_available"]:
        st.info("Le score unitaire n'est pas disponible (modèle de risque non installé ou approche non régressive).")
        return
    st.markdown("Évaluez le risque d'une commande avant son expédition (appel à `POST /api/v1/risk/score`).")
    submitted, inputs = order_form(opts, "m2_form", "Évaluer le risque", ask_promise=True)
    if submitted:
        try:
            st.session_state["m2_result"] = api.risk_score(inputs)
        except api.ApiError as e:
            st.error(e.detail)
    if "m2_result" in st.session_state:
        r = st.session_state["m2_result"]
        kpi_row([
            dict(label="Durée prédite", value=f"{fmt_num(r['predicted_days'])} j"),
            dict(label="Promesse d'Olist", value=f"{fmt_num(r['promised_days'], 0)} j"),
            dict(label="Score de risque", value=f"{signed(r['score'], 1)} j", help="Durée prédite − promesse"),
            dict(label="Niveau de risque", value=r["level"], tone=r["tone"]),
        ])
        th = r["thresholds"]
        st.caption(f"Seuils (rang sur le test) : critique à partir de {th['top_5']:.1f} j, élevé à partir de {th['top_10']:.1f} j, modéré à partir de {th['top_20']:.1f} j.")
        insight("Un score proche de zéro ou positif signifie que la durée prédite approche ou dépasse la promesse.")


def tab_method() -> None:
    st.markdown("""
**Pourquoi un score en jours ?** Le premier réflexe est un classifieur « en retard / pas en retard ». Il s'est révélé fragile : ses performances chutent d'un mois à l'autre,
car le taux de retard varie fortement (de 1 % à 21 % selon le mois). La **durée de livraison**, elle, est une cible plus riche : on prédit la durée, puis on la compare à la promesse.

**Six approches comparées**, évaluées mois par mois : classifieur avec toutes les variables, classifieur sans variables proxys du temps, régression L1 (écart durée − promesse),
régression quantile 0,8, classifieur enrichi de l'écart, et une règle simple (distance / promesse).

**Signalement par rang.** On signale les k % de commandes les plus risquées plutôt que d'appliquer un seuil de probabilité, qui dérive avec le taux de retard.

**Rentabilité.** Bénéfice net = part évitée × coût d'un retard manqué × retards alertés − coût d'une fausse alerte × fausses alertes.
""")
    with st.expander("Limites"):
        st.markdown("- Coûts et efficacité des alertes : hypothèses non mesurées.\n- Les retards dépendent de facteurs non observés (transporteur, météo, incidents).\n"
                    "- Évaluation sur 6 mois seulement ; les performances peuvent varier avec d'autres périodes.")


def render() -> None:
    hero("⚠️", "Modèle 2 · Risque de retard", "Repérer à l'avance les commandes susceptibles d'arriver après la date promise, et piloter les alertes.")
    demo_banner()
    try:
        t1, t2, t3, t4 = st.tabs(["🎛️ Pilotage des alertes", "📈 Fiabilité du score", "🔎 Évaluer une commande", "📘 Méthode"])
        with t1:
            tab_steering()
        with t2:
            tab_reliability()
        with t3:
            tab_single()
        with t4:
            tab_method()
    except api.ApiError as e:
        st.error(e.detail)


render()
