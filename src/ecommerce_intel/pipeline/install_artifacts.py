"""Installe les fichiers produits par les notebooks 05a, 05b, 05c dans ``data/app`` et ``models``.

Usage ::

    python -m ecommerce_intel.pipeline.install_artifacts --from ~/Downloads/deploy_05a ~/Downloads/deploy_05b ~/Downloads/deploy_05c

Règle : les modèles (``*.txt`` LightGBM, ``*.joblib``, ``model*_features.json``, niveaux de catégories, configuration du
modèle 2) vont dans ``models/`` ; toutes les autres tables vont dans ``data/app/``.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ecommerce_intel.config import ROOT

MODEL_FILES = {"model1_features.json", "model1_category_levels.json", "model2_config.json"}
MODEL_SUFFIXES = {".txt", ".joblib"}


def destination(name: str, app_dir: Path, models_dir: Path) -> Path:
    p = Path(name)
    return models_dir if (p.suffix in MODEL_SUFFIXES or name in MODEL_FILES) else app_dir


def install(sources: list[Path], app_dir: Path, models_dir: Path) -> list[tuple[str, Path]]:
    app_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for src in sources:
        for f in sorted(src.iterdir()):
            if f.is_file():
                dest = destination(f.name, app_dir, models_dir) / f.name
                shutil.copy2(f, dest)
                done.append((f.name, dest.parent))
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="sources", nargs="+", required=True, type=Path)
    ap.add_argument("--app-dir", type=Path, default=ROOT / "data" / "app")
    ap.add_argument("--models-dir", type=Path, default=ROOT / "models")
    a = ap.parse_args()
    for name, where in install(a.sources, a.app_dir, a.models_dir):
        print(f"  {name:48s} -> {where}")


if __name__ == "__main__":
    main()
