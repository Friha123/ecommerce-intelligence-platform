"""Indicateurs clés (KPI) à partir du tableau agrégé « mois × état du client »."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ecommerce_intel.utils.formatting import fmt_days, fmt_int, fmt_pct
from ecommerce_intel.utils.geo import STATE_NAMES

SUM_COLS = ["orders", "revenue", "freight", "delivery_days_sum", "promised_days_sum", "late_orders", "extreme_orders", "same_state_orders"]


@dataclass(frozen=True)
class Headline:
    orders: int
    revenue: float
    avg_ticket: float
    avg_delivery_days: float
    avg_promised_days: float
    late_rate: float          # proportion (0-1)

    @property
    def on_time_rate(self) -> float:
        return 1.0 - self.late_rate

    @property
    def avg_gap_days(self) -> float:
        """Avance moyenne de la livraison sur la promesse (positif = en avance)."""
        return self.avg_promised_days - self.avg_delivery_days


def filter_df(df: pd.DataFrame, period: tuple[str, str] | None = None, states: list[str] | None = None) -> pd.DataFrame:
    out = df
    if period:
        out = out[(out["month"] >= period[0]) & (out["month"] <= period[1])]
    if states:
        out = out[out["customer_state"].isin(states)]
    return out


def previous_period(df_all: pd.DataFrame, period: tuple[str, str], states: list[str] | None = None) -> pd.DataFrame | None:
    """Fenêtre précédente de même longueur (en mois), ou None si l'historique est insuffisant."""
    months = sorted(df_all["month"].unique())
    i0, i1 = months.index(period[0]), months.index(period[1])
    n = i1 - i0 + 1
    if i0 - n < 0:
        return None
    return filter_df(df_all, (months[i0 - n], months[i0 - 1]), states)


def headline(df: pd.DataFrame) -> Headline:
    s = df[[c for c in SUM_COLS if c in df.columns]].sum()
    n = max(float(s.get("orders", 0)), 1.0)
    return Headline(
        orders=int(s.get("orders", 0)), revenue=float(s.get("revenue", 0.0)), avg_ticket=float(s.get("revenue", 0.0)) / n,
        avg_delivery_days=float(s.get("delivery_days_sum", 0.0)) / n, avg_promised_days=float(s.get("promised_days_sum", 0.0)) / n,
        late_rate=float(s.get("late_orders", 0.0)) / n)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("month")[[c for c in SUM_COLS if c in df.columns]].sum().reset_index().sort_values("month")
    g["avg_delivery_days"] = g["delivery_days_sum"] / g["orders"]
    g["avg_promised_days"] = g["promised_days_sum"] / g["orders"]
    g["late_rate_pct"] = g["late_orders"] / g["orders"] * 100
    return g


def state_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("customer_state")[[c for c in SUM_COLS if c in df.columns]].sum().reset_index()
    g["avg_delivery_days"] = g["delivery_days_sum"] / g["orders"]
    g["avg_promised_days"] = g["promised_days_sum"] / g["orders"]
    g["late_rate_pct"] = g["late_orders"] / g["orders"] * 100
    g["share_orders_pct"] = g["orders"] / g["orders"].sum() * 100
    g["state_name"] = g["customer_state"].map(STATE_NAMES).fillna(g["customer_state"])
    return g.sort_values("orders", ascending=False).reset_index(drop=True)


def insights(df: pd.DataFrame, min_orders: int = 100) -> list[str]:
    """Constats automatiques, formulés en français, à partir des données filtrées."""
    out: list[str] = []
    if df.empty:
        return out
    st = state_table(df)
    big = st[st["orders"] >= min_orders]
    if len(big) >= 2:
        worst, best = big.sort_values("late_rate_pct").iloc[-1], big.sort_values("late_rate_pct").iloc[0]
        out.append(f"**{worst['state_name']}** a le plus fort taux de retard ({fmt_pct(worst['late_rate_pct'])}), "
                   f"contre {fmt_pct(best['late_rate_pct'])} pour {best['state_name']}.")
    mt = monthly_trend(df)
    mt = mt[mt["orders"] >= min_orders]
    if len(mt) >= 2:
        peak = mt.sort_values("late_rate_pct").iloc[-1]
        out.append(f"Pic de retards en **{peak['month']}** : {fmt_pct(peak['late_rate_pct'])} des commandes livrées après la date promise.")
    h = headline(df)
    out.append(f"En moyenne, la livraison arrive **{fmt_days(abs(h.avg_gap_days))} "
               f"{'avant' if h.avg_gap_days >= 0 else 'après'}** la date promise : la promesse est "
               f"{'très large' if h.avg_gap_days > 5 else 'serrée'}.")
    if "same_state_orders" in df.columns and h.orders:
        share = df["same_state_orders"].sum() / h.orders * 100
        out.append(f"Seules **{fmt_pct(share, 0)}** des commandes restent dans l'état du vendeur : la géographie domine les délais.")
    top = st.iloc[0]
    out.append(f"{top['state_name']} concentre {fmt_pct(top['share_orders_pct'], 0)} des commandes ({fmt_int(top['orders'])}).")
    return out
