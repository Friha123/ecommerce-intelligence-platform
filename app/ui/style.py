"""Thème visuel et composants réutilisables (cartes KPI, bandeau, encadrés)."""
from __future__ import annotations

import html

import streamlit as st

from ui import api

ACCENT, GOOD, WARN, BAD, MUTED, VIOLET = "#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#94A3B8", "#7C3AED"
COLORWAY = [ACCENT, WARN, GOOD, BAD, VIOLET, "#0891B2", MUTED]

CSS = """
<style>
.block-container {padding-top: 2.4rem; max-width: 1300px;}
.hero {border-radius: 18px; padding: 1.3rem 1.6rem; margin-bottom: 1.1rem; border: 1px solid rgba(128,128,128,.28);
       background: linear-gradient(120deg, rgba(37,99,235,.18), rgba(245,158,11,.10));}
.hero h1 {margin: 0; font-size: 1.85rem; line-height: 1.25;}
.hero p {margin: .4rem 0 0; opacity: .82; font-size: 1.02rem;}
.kcard {border: 1px solid rgba(128,128,128,.30); border-radius: 14px; padding: .85rem 1.05rem;
        background: rgba(128,128,128,.07); height: 100%;}
.kcard .lbl {font-size: .74rem; text-transform: uppercase; letter-spacing: .05em; opacity: .72;}
.kcard .val {font-size: 1.62rem; font-weight: 700; line-height: 1.3;}
.kcard .dlt {font-size: .82rem; margin-top: .1rem;}
.kcard .hlp {font-size: .74rem; opacity: .62; margin-top: .25rem;}
.good {color: #16A34A;} .bad {color: #DC2626;} .warn {color: #D97706;} .neutral {opacity: .75;}
.pill {display: inline-block; padding: .2rem .75rem; border-radius: 999px; font-size: .82rem; font-weight: 600;
       border: 1px solid rgba(128,128,128,.4);}
.pill.good {background: rgba(22,163,74,.14);} .pill.bad {background: rgba(220,38,38,.14);}
.pill.warn {background: rgba(245,158,11,.18);} .pill.neutral {background: rgba(128,128,128,.12);}
.insight {border-left: 4px solid #2563EB; padding: .5rem .95rem; margin: .45rem 0;
          background: rgba(37,99,235,.08); border-radius: 0 10px 10px 0;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(icon: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{icon} {html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str | None = None, tone: str = "neutral", help: str | None = None) -> None:
    d = f'<div class="dlt {tone}">{html.escape(delta)}</div>' if delta else ""
    h = f'<div class="hlp">{html.escape(help)}</div>' if help else ""
    st.markdown(f'<div class="kcard"><div class="lbl">{html.escape(label)}</div><div class="val">{html.escape(value)}</div>{d}{h}</div>',
                unsafe_allow_html=True)


def kpi_row(items: list[dict]) -> None:
    cols = st.columns(len(items))
    for col, it in zip(cols, items, strict=True):
        with col:
            kpi_card(**it)


def insight(text: str) -> None:
    st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


def pill(text: str, tone: str = "neutral") -> None:
    st.markdown(f'<span class="pill {tone}">{html.escape(text)}</span>', unsafe_allow_html=True)


def demo_banner() -> None:
    try:
        demo = api.health().get("demo", False)
    except api.ApiError:
        return
    if demo:
        st.warning("**Mode démonstration** : ces chiffres proviennent d'un jeu de données **synthétique** livré avec le dépôt. "
                   "Pour afficher les vrais résultats, exécutez les notebooks puis `make install-artifacts app-data` (voir le README).",
                   icon="🧪")


def sidebar_footer() -> None:
    with st.sidebar:
        st.markdown("---")
        try:
            h = api.health()
            data_mode = "démonstration (données synthétiques)" if h["demo"] else "données réelles Olist"
            st.caption(f"**E-Commerce Intelligence Platform** · v{h['version']}\n\nDonnées : {data_mode}\n\n"
                       f"Backend : FastAPI ({api.mode()})\n\nSource : Brazilian E-Commerce Public Dataset by Olist (Kaggle).")
        except api.ApiError as e:
            st.error(f"API indisponible : {e.detail}")
