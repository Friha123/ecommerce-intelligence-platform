"""Mode autonome : démarre l'API FastAPI dans un thread du processus Streamlit, sur un port local libre.

Utile pour exécuter l'application en un seul processus (démo, Streamlit Community Cloud). Le frontend parle
à l'API **par HTTP**, exactement comme avec une API distante : c'est le même code et le même contrat.
"""
from __future__ import annotations

import socket
import threading
import time


def start_embedded_api(timeout: float = 30.0) -> str:
    import uvicorn

    from ecommerce_intel.api.main import create_app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True, name="eci-embedded-api").start()
    t0 = time.time()
    while not server.started:
        if time.time() - t0 > timeout:
            raise RuntimeError("L'API intégrée n'a pas démarré à temps.")
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}"
