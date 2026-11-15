import numpy as np
import pytest

from ecommerce_intel.data import loaders
from ecommerce_intel.services import delivery_service as ds
from ecommerce_intel.services import kpi_service as kpi
from ecommerce_intel.services import risk_service as rs
from ecommerce_intel.services import segmentation_service as sg
from ecommerce_intel.utils import formatting as f


def test_formatting_french():
    assert f.fmt_int(1234567) == "1\u202f234\u202f567"
    assert f.fmt_num(3.14159, 2) == "3,14"
    assert f.fmt_pct(7.25) == "7,3 %" or f.fmt_pct(7.25) == "7,2 %"
    assert f.signed(-2.5, 1, " j") == "−2,5 j"
    assert f.fmt_days(float("nan")) == "n.d."


# ---------------- KPI
@pytest.fixture(scope="module")
def kpi_df():
    return loaders.load_kpi_month_state()


def test_headline_is_consistent(kpi_df):
    h = kpi.headline(kpi_df)
    assert h.orders == kpi_df["orders"].sum()
    assert 0 <= h.late_rate <= 1 and h.on_time_rate == pytest.approx(1 - h.late_rate)
    assert h.avg_gap_days == pytest.approx(h.avg_promised_days - h.avg_delivery_days)


def test_filters_and_previous_period(kpi_df):
    months = sorted(kpi_df["month"].unique())
    sub = kpi.filter_df(kpi_df, (months[0], months[1]))
    assert set(sub["month"]) == {months[0], months[1]}
    assert kpi.previous_period(kpi_df, (months[0], months[1])) is None
    prev = kpi.previous_period(kpi_df, (months[2], months[3]))
    assert set(prev["month"]) == {months[0], months[1]}


def test_state_table_and_insights(kpi_df):
    st_df = kpi.state_table(kpi_df)
    assert st_df["share_orders_pct"].sum() == pytest.approx(100)
    assert len(kpi.insights(kpi_df, min_orders=1)) >= 3


# ---------------- Modèle 1
def test_simulator_comparison():
    sim = loaders.load_m1_simulator()
    qs = ds.quantile_options(sim)
    assert qs == sorted(qs) and len(qs) >= 2
    c = ds.compare_to_olist(sim, qs[0])
    assert c["tone"] in {"good", "neutral", "bad"} and "verdict" in c
    m = ds.monthly_for_quantile(loaders.load_m1_simulator_monthly(), qs[-1])
    assert {"Modèle : taux de retard (%)", "Olist : promesse (j)"} <= set(m.columns)


def test_mae_overview_gain_positive():
    o = ds.mae_overview(loaders.load_m1_rolling_summary())
    assert o["gain_vs_promise"] == pytest.approx(o["promise_mae"] - o["model_mae"])


# ---------------- Modèle 2
def test_capacity_metrics_exact():
    y = np.array([1, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    score = np.array([9, 8, 7, 1, 2, 3, 6, 0, 4, 5])
    m = rs.capacity_metrics(y, score, 0.3)       # top 3 : scores 9, 8, 7 -> y = 1, 0, 1
    assert m["n_flagged"] == 3 and m["tp"] == 2 and m["fp"] == 1
    assert m["precision"] == pytest.approx(2 / 3) and m["recall"] == pytest.approx(2 / 3)
    assert m["lift"] == pytest.approx((2 / 3) / 0.3)


def test_net_benefit_and_breakeven():
    assert rs.net_benefit(tp=10, fp=40, cost_fn=5, cost_fp=1, prevent=1.0) == 10
    assert rs.net_benefit(tp=10, fp=40, cost_fn=5, cost_fp=1, prevent=0.5) == -15
    assert rs.breakeven_precision(5, 1, 1.0) == pytest.approx(1 / 6)
    # à précision égale au seuil, le bénéfice est nul
    tp, fp = 1, 5
    assert rs.net_benefit(tp, fp, 5, 1, 1.0) == 0 and tp / (tp + fp) == pytest.approx(rs.breakeven_precision(5, 1, 1.0))


def test_risk_level_thresholds():
    th = {"top_5": 5.0, "top_10": 2.0, "top_20": 0.0}
    assert rs.risk_level(6, th)[0] == "Critique" and rs.risk_level(3, th)[0] == "Élevé"
    assert rs.risk_level(1, th)[0] == "Modéré" and rs.risk_level(-1, th)[0] == "Faible"


def test_benefit_curve_and_top_orders():
    scores = loaders.load_m2_scores()
    curve = rs.benefit_curve(scores["is_late"].values, scores["score"].values, np.linspace(0.05, 0.3, 6), 5, 1, 1.0)
    assert len(curve) == 6 and rs.best_capacity(curve)["capacité (%)"] in curve["capacité (%)"].values
    top = rs.top_orders(scores, 0.1)
    assert top["score"].is_monotonic_decreasing


# ---------------- Modèle 3
def test_segmentation_services():
    seg = loaders.load_m3_segments()
    ov = sg.overview(seg)
    assert ov["part_clients"].sum() == pytest.approx(100)
    prio = sg.priority_customers(seg, 2.0)
    assert (prio["value_tier"] == "valeur élevée").all() and (prio["avg_review_score"] <= 2).all()
    cid = seg["customer_unique_id"].iloc[0]
    assert sg.lookup_customer(seg, cid)["customer_unique_id"] == cid and sg.lookup_customer(seg, "inconnu") is None
    g = sg.grid_long(loaders.load_m3_grid_counts(), loaders.load_m3_grid_notes(), loaders.load_m3_action_grid())
    assert {"segment_experience", "value_tier", "clients", "note", "action"} <= set(g.columns)
