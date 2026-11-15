"""Configuration : chemins des données et des modèles, détection du mode démonstration.

Ordre de résolution :
1. ``ECI_APP_DIR`` / ``ECI_MODELS_DIR`` (variables d'environnement) ;
2. ``data/app`` et ``models`` (données réelles, produites par les notebooks puis ``make install-artifacts``) ;
3. ``data/demo`` : jeu de démonstration **synthétique**, fourni pour que l'application démarre toujours.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = "kpi_month_state.csv"      # présence = données applicatives prêtes
MANIFEST = "app_manifest.json"


@dataclass(frozen=True)
class Settings:
    app_dir: Path
    models_dir: Path
    demo: bool


def get_settings() -> Settings:
    app_dir = Path(os.environ.get("ECI_APP_DIR", ROOT / "data" / "app"))
    models_dir = Path(os.environ.get("ECI_MODELS_DIR", ROOT / "models"))
    if not (app_dir / SENTINEL).exists():
        app_dir, models_dir = ROOT / "data" / "demo" / "app", ROOT / "data" / "demo" / "models"
        return Settings(app_dir, models_dir, demo=True)
    manifest = app_dir / MANIFEST
    demo = bool(json.loads(manifest.read_text(encoding="utf-8")).get("demo", False)) if manifest.exists() else False
    return Settings(app_dir, models_dir, demo=demo)
