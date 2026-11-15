"""Exporte le contrat OpenAPI de l'API dans docs/openapi.json (à versionner : le contrat est un livrable).

Usage : python scripts/export_openapi.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecommerce_intel.api.main import create_app  # noqa: E402

out = ROOT / "docs" / "openapi.json"
out.write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print("Contrat OpenAPI écrit dans", out)
