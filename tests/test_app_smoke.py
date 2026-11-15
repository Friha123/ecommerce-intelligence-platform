"""Tests de l'interface : chaque page s'exécute sans exception (Streamlit AppTest) en parlant à l'API par HTTP."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
VIEWS = APP / "views"
PAGES = ["kpi.py", "model1.py", "model2.py", "model3.py"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(str(VIEWS / page), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert len(at.tabs) >= 3 or page == "kpi.py"


def test_entrypoint_navigation():
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_kpi_filters_update():
    at = AppTest.from_file(str(VIEWS / "kpi.py"), default_timeout=90).run()
    at.multiselect[0].select(at.multiselect[0].options[0].split(" ")[0]).run()
    assert not at.exception and not at.error


def test_model1_estimate_form():
    at = AppTest.from_file(str(VIEWS / "model1.py"), default_timeout=90).run()
    at.button[0].click().run()          # bouton « Estimer la livraison »
    assert not at.exception and "m1_result" in at.session_state


def test_model2_sliders_and_form():
    at = AppTest.from_file(str(VIEWS / "model2.py"), default_timeout=90).run()
    at.slider[0].set_value(15).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception


def test_frontend_is_decoupled_from_backend():
    """Le frontend ne parle au backend que par HTTP : seul `embedded.py` (API intégrée) importe `ecommerce_intel`."""
    offenders = []
    for f in [*(APP / "views").glob("*.py"), *(APP / "ui").glob("*.py"), APP / "streamlit_app.py"]:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(("import ecommerce_intel", "from ecommerce_intel")) and f.name != "embedded.py":
                offenders.append(f"{f.name}: {line.strip()}")
    assert not offenders, offenders


def test_frontend_sends_api_key(monkeypatch):
    """Avec une API protégée par clé, le client Streamlit envoie l'en-tête X-API-Key."""
    import streamlit as st

    monkeypatch.setenv("ECI_API_KEY", "cle-de-test")
    st.cache_resource.clear()
    st.cache_data.clear()
    try:
        at = AppTest.from_file(str(VIEWS / "kpi.py"), default_timeout=90).run()
        assert not at.exception and not at.error, [e.value for e in at.error]
    finally:
        monkeypatch.undo()
        st.cache_resource.clear()
        st.cache_data.clear()
