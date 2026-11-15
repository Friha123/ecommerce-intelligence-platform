"""Graphiques Plotly : palette cohérente, fond transparent (compatible thèmes clair et sombre)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.style import ACCENT, BAD, COLORWAY, GOOD, MUTED, VIOLET, WARN


def _layout(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), colorway=COLORWAY, showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(font_size=13))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.2)")
    return fig


# ---------------------------------------------------------------- KPI
def trend_chart(mt: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=mt["month"], y=mt["orders"], name="Commandes livrées", marker_color=ACCENT, opacity=0.85, secondary_y=False)
    fig.add_scatter(x=mt["month"], y=mt["late_rate_pct"], name="Taux de retard (%)", mode="lines+markers",
                    line=dict(color=BAD, width=3), secondary_y=True)
    fig.update_yaxes(title_text="Commandes", secondary_y=False)
    fig.update_yaxes(title_text="Taux de retard (%)", secondary_y=True, showgrid=False, rangemode="tozero")
    return _layout(fig, 400)


def state_map(st_df: pd.DataFrame, centroids: pd.DataFrame) -> go.Figure:
    d = st_df.merge(centroids, on="state", how="inner")
    fig = px.scatter_geo(d, lat="lat", lon="lng", size="orders", color="late_rate_pct", hover_name="state_name",
                         hover_data={"orders": ":,", "late_rate_pct": ":.1f", "avg_delivery_days": ":.1f", "lat": False, "lng": False},
                         color_continuous_scale=["#16A34A", "#F59E0B", "#DC2626"], size_max=42,
                         labels={"late_rate_pct": "Retards (%)", "orders": "Commandes", "avg_delivery_days": "Durée moy. (j)"})
    fig.update_geos(scope="south america", fitbounds="locations", showcountries=True, countrycolor="rgba(128,128,128,.5)",
                    showland=True, landcolor="rgba(128,128,128,.10)", showocean=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(coloraxis_colorbar=dict(title="Retards (%)", thickness=12))
    return _layout(fig, 470, legend=False)


def state_late_bar(st_df: pd.DataFrame, min_orders: int = 100, top: int = 15) -> go.Figure:
    d = st_df[st_df["orders"] >= min_orders].sort_values("late_rate_pct", ascending=False).head(top).iloc[::-1]
    fig = go.Figure(go.Bar(x=d["late_rate_pct"], y=d["state"], orientation="h", marker_color=BAD, opacity=0.85,
                           text=d["late_rate_pct"].map(lambda v: f"{v:.1f} %"), textposition="outside",
                           hovertemplate="%{y} : %{x:.1f} % de retards<extra></extra>"))
    fig.update_xaxes(title_text="Taux de retard (%)")
    return _layout(fig, 470, legend=False)


def delivery_hist_chart(h: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=h["day"], y=h["delivered"], name="Durée réelle", marker_color=ACCENT, opacity=0.75)
    fig.add_bar(x=h["day"], y=h["promised"], name="Durée promise par Olist", marker_color=WARN, opacity=0.6)
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Jours entre l'achat et la livraison (tronqué à 60)")
    fig.update_yaxes(title_text="Commandes")
    return _layout(fig, 380)


def promise_vs_real_bar(st_df: pd.DataFrame, top: int = 12) -> go.Figure:
    d = st_df.head(top)
    fig = go.Figure()
    fig.add_bar(x=d["state"], y=d["avg_delivery_days"], name="Durée réelle moyenne", marker_color=ACCENT)
    fig.add_bar(x=d["state"], y=d["avg_promised_days"], name="Durée promise moyenne", marker_color=WARN)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Jours")
    return _layout(fig, 360)


def review_chart(rv: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(x=rv["group"], y=rv["avg_review"], marker_color=[GOOD, WARN, BAD][: len(rv)],
                           text=rv["avg_review"].map(lambda v: f"{v:.2f}"), textposition="outside",
                           customdata=rv["customers"], hovertemplate="%{x}<br>Note %{y:.2f} (%{customdata:,} clients)<extra></extra>"))
    fig.update_yaxes(range=[0, 5.3], title_text="Note moyenne (sur 5)")
    return _layout(fig, 360, legend=False)


# ---------------------------------------------------------------- Modèle 1
def tradeoff_chart(sim: pd.DataFrame, selected_q: float) -> go.Figure:
    q = sim[~sim["is_olist"]].sort_values("promise_days")
    o = sim[sim["is_olist"]].iloc[0]
    fig = go.Figure()
    fig.add_scatter(x=q["promise_days"], y=q["late_pct"], mode="lines+markers+text", name="Promesse par quantile",
                    line=dict(color=ACCENT, width=3), marker=dict(size=10), text=q["quantile"].map(lambda v: f"q = {v:.2f}"),
                    textposition="top right")
    sel = q[q["quantile"].round(3) == round(selected_q, 3)]
    fig.add_scatter(x=sel["promise_days"], y=sel["late_pct"], mode="markers", name="Niveau choisi",
                    marker=dict(size=20, color="rgba(0,0,0,0)", line=dict(color=VIOLET, width=3)))
    fig.add_scatter(x=[o["promise_days"]], y=[o["late_pct"]], mode="markers+text", name="Promesse actuelle d'Olist",
                    marker=dict(size=14, color=BAD, symbol="diamond"), text=["Olist"], textposition="bottom right")
    fig.add_hline(y=o["late_pct"], line_dash="dot", line_color=MUTED)
    fig.add_vline(x=o["promise_days"], line_dash="dot", line_color=MUTED)
    fig.update_xaxes(title_text="Durée promise moyenne (jours)")
    fig.update_yaxes(title_text="Taux de retard (%)", rangemode="tozero")
    return _layout(fig, 400)


def monthly_compare_chart(m: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Taux de retard (%)", "Durée promise moyenne (jours)"))
    for name, key, color in [("Olist", "olist", BAD), ("Modèle", "model", ACCENT)]:
        fig.add_scatter(x=m["month"], y=m[f"{key}_late_pct"], name=name, mode="lines+markers", line=dict(color=color, width=3), row=1, col=1)
        fig.add_scatter(x=m["month"], y=m[f"{key}_promise_days"], name=name, mode="lines+markers", line=dict(color=color, width=3),
                        showlegend=False, row=1, col=2)
    return _layout(fig, 340)


def mae_bars(summary: pd.DataFrame) -> go.Figure:
    col = "mae_all_months"
    d = summary.sort_values(col, ascending=True).iloc[::-1]
    colors = [BAD if t == "Baseline" else ACCENT for t in d["type"]]
    fig = go.Figure(go.Bar(x=d[col], y=d["method"], orientation="h", marker_color=colors,
                           text=d[col].map(lambda v: f"{v:.2f} j"), textposition="outside"))
    fig.update_xaxes(title_text="Erreur absolue moyenne (jours), évaluation glissante")
    return _layout(fig, 120 + 38 * len(d), legend=False)


def mae_months(by_month: pd.DataFrame, model_col: str) -> go.Figure:
    fig = go.Figure()
    for c in by_month.columns:
        is_model = c == model_col
        fig.add_scatter(x=by_month.index.astype(str), y=by_month[c], name=c, mode="lines+markers",
                        line=dict(width=4 if is_model else 1.5, dash="solid" if is_model else "dot", color=ACCENT if is_model else None),
                        opacity=1 if is_model else 0.7)
    fig.update_yaxes(title_text="Erreur absolue moyenne (jours)")
    return _layout(fig, 400)


def quantile_ruler(quantiles: dict, olist_promise: float | None = None) -> go.Figure:
    qs = sorted(quantiles.items())
    fig = go.Figure()
    fig.add_scatter(x=[v for _, v in qs], y=[0] * len(qs), mode="lines+markers+text", line=dict(color=ACCENT, width=6),
                    marker=dict(size=14, color=ACCENT), text=[f"{v:.1f} j<br>(q {q:.2f})" for q, v in qs], textposition="top center",
                    hoverinfo="skip", showlegend=False)
    if olist_promise:
        fig.add_vline(x=olist_promise, line_dash="dash", line_color=BAD, annotation_text=f"Promesse Olist : {olist_promise:.0f} j",
                      annotation_position="bottom right")
    fig.update_yaxes(visible=False, range=[-1, 1.4])
    fig.update_xaxes(title_text="Durée de livraison (jours)")
    return _layout(fig, 230, legend=False)


# ---------------------------------------------------------------- Modèle 2
def benefit_curve_chart(curve: pd.DataFrame, chosen_pct: float, best_pct: float) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=curve["capacity_pct"], y=curve["net_benefit"], mode="lines", line=dict(color=ACCENT, width=3),
                    fill="tozeroy", fillcolor="rgba(37,99,235,.12)", name="Bénéfice net")
    fig.add_hline(y=0, line_color=MUTED)
    fig.add_vline(x=chosen_pct, line_dash="dot", line_color=VIOLET, annotation_text="Votre choix")
    fig.add_scatter(x=[best_pct], y=[float(curve.loc[(curve["capacity_pct"] - best_pct).abs().idxmin(), "net_benefit"])],
                    mode="markers", marker=dict(size=14, color=GOOD, symbol="star"), name="Optimum")
    fig.update_xaxes(title_text="Part des commandes signalées (%)")
    fig.update_yaxes(title_text="Bénéfice net (unités de coût)")
    return _layout(fig, 380)


def lift_monthly_chart(m: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=m["month"], y=m["gain"], name="Gain vs hasard (x)", marker_color=ACCENT, opacity=0.85, secondary_y=False)
    fig.add_scatter(x=m["month"], y=m["recall"] * 100, name="Retards détectés (%)", mode="lines+markers", line=dict(color=WARN, width=3), secondary_y=True)
    fig.update_yaxes(title_text="Gain (x)", secondary_y=False)
    fig.update_yaxes(title_text="Rappel (%)", secondary_y=True, showgrid=False, rangemode="tozero")
    return _layout(fig, 340)


def approaches_chart(results: pd.DataFrame, metric: str = "gain") -> go.Figure:
    fig = px.line(results, x="month", y=metric, color="approach", markers=True)
    fig.update_traces(line=dict(width=3))
    fig.update_yaxes(title_text={"gain": "Gain de PR-AUC vs taux de base (x)", "roc_auc": "ROC-AUC"}.get(metric, metric))
    if metric == "roc_auc":
        fig.add_hline(y=0.5, line_dash="dot", line_color=MUTED, annotation_text="Hasard")
    return _layout(fig, 400)


# ---------------------------------------------------------------- Modèle 3
def segment_donut(ov: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(labels=ov["segment"], values=ov["clients"], hole=0.62, sort=False,
                           marker=dict(colors=[GOOD, WARN, BAD, VIOLET, ACCENT][: len(ov)]), textinfo="percent",
                           hovertemplate="%{label}<br>%{value:,} clients (%{percent})<extra></extra>"))
    fig.update_layout(annotations=[dict(text=f"{int(ov['clients'].sum()):,}".replace(",", "\u202f") + "<br>clients", showarrow=False, font_size=18)])
    return _layout(fig, 360)


def grid_heatmap(g: pd.DataFrame) -> go.Figure:
    z = g.pivot(index="segment", columns="value_tier", values="clients")
    n = g.pivot(index="segment", columns="value_tier", values="avg_review")
    z = z[[c for c in ["valeur faible", "valeur moyenne", "valeur élevée"] if c in z.columns]]
    n = n[z.columns]
    text = [[f"{int(z.iloc[i, j]):,}".replace(",", "\u202f") + f"<br>note {n.iloc[i, j]:.2f}" for j in range(z.shape[1])] for i in range(z.shape[0])]
    fig = go.Figure(go.Heatmap(z=z.values, x=list(z.columns), y=list(z.index), text=text, texttemplate="%{text}",
                               colorscale="Blues", showscale=False, hovertemplate="%{y} · %{x}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, 300, legend=False)


def profile_bars(ov: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Note moyenne (sur 5)", "Durée de livraison moyenne (j)", "Part de commandes en retard (%)"))
    colors = [GOOD, WARN, BAD, VIOLET, ACCENT][: len(ov)]
    for i, (col, scale) in enumerate([("avg_review", 1), ("avg_delivery_days", 1), ("late_share", 100)], start=1):
        fig.add_bar(x=ov["segment"], y=ov[col] * scale, marker_color=colors, showlegend=False, row=1, col=i,
                    text=(ov[col] * scale).map(lambda v: f"{v:.1f}"), textposition="outside")
    fig.update_xaxes(showticklabels=False)
    return _layout(fig, 330, legend=False)


def eta_chart(variants: pd.DataFrame) -> go.Figure:
    cols = {"eta2_recency": "récence", "eta2_value": "valeur", "eta2_satisfaction": "satisfaction", "eta2_delivery": "livraison"}
    d = variants.melt(id_vars="variant", value_vars=list(cols), var_name="dimension", value_name="eta2")
    d["dimension"] = d["dimension"].map(cols)
    fig = px.bar(d, x="dimension", y="eta2", color="variant", barmode="group")
    fig.update_yaxes(title_text="Part de variance expliquée (η²)", range=[0, 1])
    return _layout(fig, 360)


def region_chart(mix: pd.DataFrame) -> go.Figure:
    fig = px.bar(mix, x="region", y="share_pct", color="segment", barmode="stack")
    fig.update_yaxes(title_text="Part des clients de la région (%)")
    return _layout(fig, 360)
