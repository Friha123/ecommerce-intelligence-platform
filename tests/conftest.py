"""Configuration pytest : chemins et jeu de démonstration."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Les tests s'exécutent toujours sur le jeu de démonstration synthétique
os.environ["ECI_APP_DIR"] = str(ROOT / "data" / "demo" / "app")
os.environ["ECI_MODELS_DIR"] = str(ROOT / "data" / "demo" / "models")
