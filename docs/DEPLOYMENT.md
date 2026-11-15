# Déploiement

## 1. Un seul processus (démonstration, développement)

```bash
git clone <votre-depot> && cd ecommerce-intelligence-platform
python -m venv .venv && source .venv/bin/activate
make install
make run          # http://localhost:8501
```

L'interface démarre l'API FastAPI dans un thread local (« API intégrée ») : le contrat HTTP est le même qu'avec une API distante.
L'application affiche « Mode démonstration » (données synthétiques) tant que les vrais résultats ne sont pas installés.

## 2. Deux processus (architecture cible)

```bash
make api          # terminal 1 : API sur http://localhost:8000  (documentation : /docs)
make run-remote   # terminal 2 : interface sur http://localhost:8501, connectée à l'API
```

## 3. Brancher les vraies données

1. Exécuter les notebooks `03`, puis `05a`, `05b`, `05c` sur Kaggle.
2. Télécharger le dossier `/kaggle/working/deploy/` de chacun des notebooks 05a, 05b, 05c, et depuis le notebook 03 les fichiers
   `model1_delivery_duration.csv` et `model3_customer_segmentation.csv` (à placer dans `data/processed/`).
3. Installer et construire :

```bash
make install-artifacts ARTIFACTS="~/Downloads/deploy_05a ~/Downloads/deploy_05b ~/Downloads/deploy_05c"
make app-data
make test          # les tests s'exécutent sur le jeu de démonstration
make api           # ou make run
```

Le bandeau « Mode démonstration » disparaît dès que `data/app/kpi_month_state.csv` existe et que `app_manifest.json` ne contient plus `"demo": true`.
Taille indicative à versionner : `data/app/` (quelques Mo, dont `customer_segments_final.csv` d'environ 20 Mo) et `models/`. Au-delà de 50 Mo par fichier : Git LFS.

## 4. Docker Compose (API + interface)

```bash
make docker-up            # http://localhost:8501 (interface) et http://localhost:8000/docs (API)
ECI_API_KEY=secret make docker-up    # active la clé d'API des deux côtés
```

Deux images : `Dockerfile.api` (backend, données et modèles) et `Dockerfile.app` (interface seule, sans données ni modèles).

## 5. Hébergement gratuit ou peu coûteux

**Option A : tout-en-un sur Streamlit Community Cloud** (API intégrée, aucun secret) : *New app*, dépôt, branche `main`, fichier `app/streamlit_app.py`, Python 3.11.

**Option B : API et interface séparées** (démontre l'architecture complète)
1. API : déployer `Dockerfile.api` sur Render, Railway, Fly.io ou Hugging Face Spaces (port 8000). Variables : `ECI_API_KEY`, `ECI_CORS_ORIGINS`.
2. Interface : Streamlit Community Cloud, avec les secrets `ECI_API_URL = "https://votre-api..."` et `ECI_API_KEY = "..."` (*Settings → Secrets*).

## 6. Mise à jour mensuelle

Les modèles sont conçus pour un **réentraînement mensuel** (évaluation glissante) : ré-exécuter `03`, `05a`, `05b`, `05c` avec les nouvelles commandes,
puis `make install-artifacts app-data` et redéployer l'API (l'interface n'a pas à changer).
