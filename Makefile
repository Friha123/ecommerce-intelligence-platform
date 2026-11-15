.PHONY: help install install-dev install-artifacts app-data api run run-remote test lint openapi docker-up docker-down

PY ?= python
PYTHONPATH := src:app
export PYTHONPATH

MODEL1 ?= data/processed/model1_delivery_duration.csv
MODEL3 ?= data/processed/model3_customer_segmentation.csv
ARTIFACTS ?=
API_URL ?= http://localhost:8000

help:            ## Liste des commandes
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:         ## Installe les dépendances (API + interface)
	$(PY) -m pip install -r requirements.txt

install-dev:     ## Installe aussi pytest et ruff
	$(PY) -m pip install -r requirements-dev.txt

install-artifacts: ## Copie les sorties des notebooks 05a/05b/05c : make install-artifacts ARTIFACTS="dir_05a dir_05b dir_05c"
	$(PY) -m ecommerce_intel.pipeline.install_artifacts --from $(ARTIFACTS)

app-data:        ## Construit les tables légères de l'application dans data/app
	$(PY) -m ecommerce_intel.pipeline.build_app_data --model1 $(MODEL1) --model3 $(MODEL3) --out data/app

api:             ## Lance l'API FastAPI : http://localhost:8000/docs
	$(PY) -m uvicorn ecommerce_intel.api.main:app --reload --port 8000

run:             ## Lance l'interface (API intégrée, un seul processus) : http://localhost:8501
	streamlit run app/streamlit_app.py

run-remote:      ## Lance l'interface connectée à une API déjà démarrée (make api dans un autre terminal)
	ECI_API_URL=$(API_URL) streamlit run app/streamlit_app.py

test:            ## Exécute les tests
	$(PY) -m pytest -q

lint:            ## Vérifie le style
	ruff check src app tests scripts

openapi:         ## Exporte le contrat OpenAPI dans docs/openapi.json
	$(PY) scripts/export_openapi.py

docker-up:       ## API + interface en conteneurs : http://localhost:8501
	docker compose up --build

docker-down:     ## Arrête les conteneurs
	docker compose down
