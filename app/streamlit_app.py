"""Point d'entrée Streamlit : navigation entre les quatre pages.

Lancement : ``streamlit run app/streamlit_app.py``
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="E-Commerce Intelligence Platform", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

from ui.style import inject_css, sidebar_footer  # noqa: E402

inject_css()
pages = [
    st.Page("views/kpi.py", title="KPI · Vue d'ensemble", icon="📊", url_path="kpi", default=True),
    st.Page("views/model1.py", title="Modèle 1 · Durée de livraison", icon="🚚", url_path="duree-livraison"),
    st.Page("views/model2.py", title="Modèle 2 · Risque de retard", icon="⚠️", url_path="risque-retard"),
    st.Page("views/model3.py", title="Modèle 3 · Segments clients", icon="👥", url_path="segments-clients"),
]
navigation = st.navigation(pages)
sidebar_footer()
navigation.run()
