"""Page 2 : modèle 1, durée de livraison et promesse intelligente — données et inférence via l'API FastAPI."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "src", _ROOT / "app"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import math

import streamlit as st
from ui import api, charts
from ui.format import fmt_days, fmt_num, signed
from ui.forms import order_form
from ui.style import demo_banner, hero, insight, kpi_row, pill


def tab_promise() -> None:
    sim = api.delivery_simulator()
    qs, levels = sim["quantiles"], sim["levels"]
    st.markdown("Au lieu de promettre la même durée à tous, le modèle prédit un **quantile** de la durée de livraison de chaque commande : "
                "promettre le quantile 90 %, c'est viser que 9 commandes sur 10 arrivent à temps.")
    default = 0.9 if 0.9 in qs else qs[len(qs) // 2]
    q = st.select_slider("Niveau de prudence de la promesse", options=qs, value=default,
                         format_func=lambda x: f"{levels[x]['label']} (q = {x:.2f})")
    st.caption(f"Niveau « {levels[q]['label']} » : {levels[q]['description'] or 'taux de retard visé = 1 − q'}.")
    c = api.delivery_compare(q)
    kpi_row([
        dict(label="Durée promise moyenne (modèle)", value=fmt_days(c["promise_days"]),
             delta=f"{signed(c['delta_days'], 1, ' j')} ({signed(c['delta_days_pct'], 0, ' %')}) vs Olist", tone="good" if c["delta_days"] <= 0 else "neutral",
             help=f"Promesse actuelle d'Olist : {fmt_days(c['olist_promise_days'])}"),
        dict(label="Taux de retard (modèle)", value=f"{fmt_num(c['late_pct'])} %",
             delta=f"{signed(c['delta_late_pts'], 1, ' pt')} vs Olist", tone="good" if c["delta_late_pts"] <= 0 else "bad",
             help=f"Taux actuel d'Olist : {fmt_num(c['olist_late_pct'])} %"),
    ])
    st.write("")
    pill(c["verdict"], c["tone"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Compromis promesse / retard**")
        st.plotly_chart(charts.tradeoff_chart(sim["points"], q), width="stretch")
    with right:
        st.markdown("**Mois par mois (évaluation glissante)**")
        st.plotly_chart(charts.monthly_compare_chart(c["monthly"]), width="stretch")
    with st.expander("Comment lire ces graphiques ?"):
        st.markdown(
            "- Chaque point est une politique de promesse : plus la durée promise est longue, moins il y a de retards.\n"
            "- Le **losange rouge** est la promesse actuelle d'Olist ; un point **en bas à gauche** de ce losange est meilleur sur les deux critères.\n"
            "- Chaque mois est prédit par un modèle entraîné **uniquement sur les mois précédents** : aucune fuite de données.\n"
            "- Le taux de retard d'un mois donné **varie** autour de la cible : on ne le contrôle pas parfaitement.\n"
            "- L'effet d'une promesse plus courte sur les achats n'est **pas** modélisé.")


def tab_estimate() -> None:
    opts = api.options()
    if not opts["delivery_model_available"]:
        st.info("Les modèles de durée ne sont pas installés côté API (voir `make install-artifacts`).")
        return
    levels = api.delivery_simulator()["levels"]
    st.markdown("Renseignez une commande : le modèle (appelé via `POST /api/v1/delivery/predict`) estime la durée de livraison "
                "et propose une promesse pour chaque niveau de prudence.")
    submitted, inputs = order_form(opts, "m1_form", "Estimer la livraison", ask_promise=opts["delivery_uses_promise"])
    if submitted:
        try:
            st.session_state["m1_result"] = (api.delivery_predict(inputs), inputs)
        except api.ApiError as e:
            st.error(e.detail)
    if "m1_result" in st.session_state:
        res, inp = st.session_state["m1_result"]
        q = {x["quantile"]: x["days"] for x in res["quantiles"]}
        q90 = q.get(0.9, max(q.values()))
        olist = inp.get("promised_days")
        kpi_row([
            dict(label="Durée prévue (médiane)", value=fmt_days(res["point_days"]), help="La moitié des commandes similaires arrive plus tôt"),
            dict(label="Promesse prudente (q 0,90)", value=fmt_days(math.ceil(q90), 0), help="Environ 9 commandes sur 10 à l'heure"),
            dict(label="Marge sur la médiane", value=fmt_days(q90 - res["point_days"]), help="Coussin de sécurité de la promesse prudente"),
        ])
        st.plotly_chart(charts.quantile_ruler(q, olist), width="stretch")
        rows = [{"Niveau": levels[k]["label"] if k in levels else f"q = {k:.2f}", "Quantile": k, "Promesse conseillée (j)": math.ceil(v),
                 "Retards visés (%)": round((1 - k) * 100, 1), **({"Écart vs Olist (j)": math.ceil(v) - olist} if olist else {})} for k, v in q.items()]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Les informations non saisies (historique du vendeur, charge de la plateforme…) sont remplacées par des valeurs typiques ; "
                   "l'historique du trajet entre les deux états est, lui, repris des données.")


def tab_performance() -> None:
    perf = api.delivery_performance()
    o, summary, by_month, static = perf["overview"], perf["summary"], perf["by_month"], perf["static_test"]
    kpi_row([
        dict(label="Erreur du modèle retenu", value=fmt_days(o["model_mae"], 2), help=o["model"]),
        dict(label="Meilleure baseline", value=fmt_days(o["baseline_mae"], 2), help=o["best_baseline"],
             delta=f"Gain du modèle : {fmt_days(o['gain_vs_baseline'], 2)} ({fmt_num(o['gain_vs_baseline_pct'], 0)} %)", tone="good"),
        dict(label="Promesse d'Olist", value=fmt_days(o["promise_mae"], 2),
             delta=f"Gain du modèle : {fmt_days(o['gain_vs_promise'], 2)} ({fmt_num(o['gain_vs_promise_pct'], 0)} %)", tone="good"),
    ])
    st.caption("Erreur absolue moyenne (MAE), évaluation glissante mois par mois : chaque mois est prédit par un modèle entraîné sur les mois précédents.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Erreur moyenne par méthode**")
        st.plotly_chart(charts.mae_bars(summary), width="stretch")
    with right:
        st.markdown("**Erreur mois par mois**")
        st.plotly_chart(charts.mae_months(by_month, o["model"]), width="stretch")
    st.markdown("**Comparaison statique équitable sur le bloc test** (modèle et baselines ajustés sur le même historique)")
    st.dataframe(static.rename(columns={"model": "Modèle", "mae": "MAE", "rmse": "RMSE", "r2": "R²", "medae": "Erreur médiane", "bias": "Biais"}).round(3),
                 hide_index=True, width="stretch")
    insight("Le modèle bat nettement la **promesse d'Olist**, et gagne de façon **plus modeste** sur une simple médiane par état : "
            "une grande part du signal est géographique.")
    with st.expander("Limites"):
        st.markdown("- Période d'évaluation courte (6 mois) et livraisons qui s'accélèrent en 2018.\n"
                    "- Pas de données sur le transporteur, la météo ou les incidents : les livraisons très longues restent imprévisibles.\n"
                    "- Les variables proxys du temps (`orders_last_7d`, `purchase_month`) ont été écartées après test.")


def render() -> None:
    hero("🚚", "Modèle 1 · Durée de livraison", "Prédire la durée de livraison dès l'achat, et en déduire une promesse plus précise que celle d'Olist.")
    demo_banner()
    try:
        t1, t2, t3 = st.tabs(["🎯 Promesse intelligente", "🔮 Estimer une commande", "📈 Performance du modèle"])
        with t1:
            tab_promise()
        with t2:
            tab_estimate()
        with t3:
            tab_performance()
    except api.ApiError as e:
        st.error(e.detail)


render()
