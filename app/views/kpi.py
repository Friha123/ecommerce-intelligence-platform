"""Page 1 : vue d'ensemble (KPI logistiques de la marketplace) — données servies par l'API FastAPI."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "src", _ROOT / "app"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import streamlit as st
from ui import api, charts
from ui.format import fmt_brl, fmt_days, fmt_int, fmt_num, fmt_ratio_pct, signed
from ui.style import demo_banner, hero, insight, kpi_row


def _delta_pct(cur: float, prev: float) -> float | None:
    return (cur / prev - 1) * 100 if prev else None


def render() -> None:
    hero("📊", "Vue d'ensemble", "Performance logistique de la marketplace : volumes, délais, retards et satisfaction des clients.")
    demo_banner()
    try:
        flt = api.kpi_filters()
    except api.ApiError as e:
        st.error(e.detail)
        st.stop()

    months = flt["months"]
    names = {s["code"]: f"{s['code']} · {s['name']}" for s in flt["states"]}
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        period = c1.select_slider("Période d'achat", options=months, value=(months[0], months[-1]))
        states = c2.multiselect("États du client", list(names), placeholder="Tous les états", format_func=names.get)
    try:
        summary = api.kpi_summary(period, states)
    except api.ApiError as e:
        st.warning(e.detail)
        st.stop()
    h, hp = summary["current"], summary["previous"]

    def delta(key, better_when_higher=True, unit=" %", digits=1, absolute=False, scale=1.0):
        if hp is None:
            return None, "neutral"
        cur, prev = h[key] * scale, hp[key] * scale
        d = (cur - prev) if absolute else _delta_pct(cur, prev)
        if d is None:
            return None, "neutral"
        good = (d > 0) == better_when_higher
        return f"{signed(d, digits, unit)} vs période précédente", ("neutral" if abs(d) < 1e-9 else "good" if good else "bad")

    d_orders, t_orders = delta("orders")
    d_rev, t_rev = delta("revenue")
    d_del, t_del = delta("avg_delivery_days", better_when_higher=False, unit=" j", absolute=True)
    d_ot, t_ot = delta("on_time_rate", unit=" pt", absolute=True, scale=100)
    kpi_row([
        dict(label="Commandes livrées", value=fmt_int(h["orders"]), delta=d_orders, tone=t_orders),
        dict(label="Chiffre d'affaires", value=fmt_brl(h["revenue"]), delta=d_rev, tone=t_rev, help=f"Panier moyen : {fmt_brl(h['avg_ticket'])}"),
        dict(label="Durée moyenne", value=fmt_days(h["avg_delivery_days"]), delta=d_del, tone=t_del, help="Achat → livraison"),
        dict(label="Livraisons à l'heure", value=fmt_ratio_pct(h["on_time_rate"]), delta=d_ot, tone=t_ot, help="Livrées avant la date promise"),
        dict(label="Avance sur la promesse", value=fmt_days(h["avg_gap_days"]), help="Promesse moyenne − durée réelle moyenne"),
    ])
    if hp is None:
        st.caption("Pas assez d'historique pour comparer à la période précédente.")

    st_df = api.kpi_states(period, states)
    t1, t2, t3, t4 = st.tabs(["📈 Tendances", "🗺️ Géographie", "⏱️ Délais", "⭐ Satisfaction"])

    with t1:
        st.plotly_chart(charts.trend_chart(api.kpi_trend(period, states)), width="stretch")
        st.markdown("#### À retenir")
        for txt in api.kpi_insights(period, states):
            insight(txt)

    with t2:
        left, right = st.columns([3, 2])
        with left:
            st.markdown("**Commandes (taille) et taux de retard (couleur) par état du client**")
            st.plotly_chart(charts.state_map(st_df, api.kpi_centroids()), width="stretch")
        with right:
            st.markdown("**États au plus fort taux de retard**")
            st.plotly_chart(charts.state_late_bar(st_df), width="stretch")
        st.dataframe(
            st_df[["state", "state_name", "orders", "share_orders_pct", "avg_delivery_days", "avg_promised_days", "late_rate_pct"]],
            hide_index=True, width="stretch",
            column_config={"state": "État", "state_name": "Nom", "orders": st.column_config.NumberColumn("Commandes", format="%d"),
                           "share_orders_pct": st.column_config.NumberColumn("Part (%)", format="%.1f"),
                           "avg_delivery_days": st.column_config.NumberColumn("Durée réelle (j)", format="%.1f"),
                           "avg_promised_days": st.column_config.NumberColumn("Durée promise (j)", format="%.1f"),
                           "late_rate_pct": st.column_config.ProgressColumn("Retards (%)", format="%.1f", min_value=0,
                                                                            max_value=max(30.0, float(st_df["late_rate_pct"].max())))})

    with t3:
        st.markdown("**Durée réelle contre durée promise par Olist**")
        st.plotly_chart(charts.delivery_hist_chart(api.kpi_histogram()), width="stretch")
        st.markdown("**Durée réelle et durée promise, par état (12 premiers états en volume)**")
        st.plotly_chart(charts.promise_vs_real_bar(st_df), width="stretch")
        insight("La promesse d'Olist est en moyenne **très au-dessus** de la durée réelle : c'est ce qui rend les retards rares, "
                "mais aussi ce qui laisse de la marge pour une promesse plus précise (page *Modèle 1*).")

    with t4:
        sat = api.kpi_satisfaction()
        rv = sat["groups"]
        if rv.empty:
            st.info("Données de satisfaction indisponibles (fournir le jeu de données du modèle 3 à `build_app_data`).")
        else:
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("**Note moyenne selon le retard vécu par le client**")
                st.plotly_chart(charts.review_chart(rv), width="stretch")
            with c2:
                if sat.get("customers"):
                    kpi_row([dict(label="Clients analysés", value=fmt_int(sat["customers"]))])
                    st.write("")
                    kpi_row([dict(label="Achat répété", value=f"{fmt_num(sat['repeat_rate_pct'])} %", help="La grande majorité des clients n'achète qu'une fois")])
                    st.write("")
                    kpi_row([dict(label="Note moyenne", value=f"{fmt_num(sat['avg_review'], 2)} / 5")])
            insight("Un retard fait chuter la satisfaction : la note moyenne des clients touchés par un retard est nettement plus basse.")


render()
