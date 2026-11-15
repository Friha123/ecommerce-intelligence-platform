# API REST

Documentation interactive : `http://localhost:8000/docs` (Swagger UI) et `/redoc`. Contrat exporté : [`openapi.json`](openapi.json).

```bash
make api        # http://localhost:8000
```

## Routes

Toutes les routes métier sont sous `/api/v1`. `GET /health` est publique.

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | État du service, mode démonstration, modèles disponibles |
| GET | `/api/v1/meta` | Métadonnées des jeux de données et des modèles |
| GET | `/api/v1/options` | États, catégories et modes de paiement des formulaires |
| GET | `/api/v1/kpi/filters` | Mois et états disponibles |
| GET | `/api/v1/kpi/summary` | KPI de la période et de la période précédente (`start`, `end`, `states`) |
| GET | `/api/v1/kpi/trend` · `/states` · `/insights` | Tendance mensuelle, indicateurs par état, constats automatiques |
| GET | `/api/v1/kpi/histogram` · `/centroids` · `/satisfaction` | Histogramme des durées, centroïdes, note selon le retard |
| GET | `/api/v1/delivery/simulator` | Compromis durée promise / retards pour chaque quantile |
| GET | `/api/v1/delivery/simulator/compare?quantile=0.9` | Un niveau de prudence comparé à la promesse d'Olist |
| GET | `/api/v1/delivery/performance` | Erreur du modèle et des baselines (glissant et test statique) |
| **POST** | `/api/v1/delivery/predict` | Prédit la durée et les promesses possibles d'une commande |
| GET | `/api/v1/risk/steering` | Pilotage des alertes : `capacity`, `cost_fn`, `cost_fp`, `prevent` |
| GET | `/api/v1/risk/top-orders` | Commandes à surveiller (`format=json` ou `csv`) |
| GET | `/api/v1/risk/reliability` | Fiabilité mensuelle et comparaison des 6 approches |
| **POST** | `/api/v1/risk/score` | Score de risque et niveau d'une commande |
| GET | `/api/v1/segments/overview` · `/grid` · `/methodology` | Segments, grille d'actions, comparaison des variantes |
| GET | `/api/v1/segments/customers` | Clients ciblés : filtres, pagination, `format=csv` |
| GET | `/api/v1/segments/customers/{customer_id}` | Segment et action d'un client |

## Exemples

```bash
# Prédire la durée d'une commande
curl -X POST http://localhost:8000/api/v1/delivery/predict -H "Content-Type: application/json" -d '{
  "customer_state": "RJ", "seller_state": "SP", "categorie_grouped": "bed_bath_table",
  "total_price": 120, "total_freight": 25, "total_weight_g": 1500, "total_volume_cm3": 8000,
  "purchase_datetime": "2018-06-12T14:30:00", "promised_days": 24 }'

# Bénéfice net des alertes pour 10 % de capacité et un retard 5 fois plus coûteux qu'une fausse alerte
curl "http://localhost:8000/api/v1/risk/steering?capacity=0.10&cost_fn=5&prevent=0.5"

# Export CSV des clients de valeur élevée insatisfaits
curl -o cibles.csv "http://localhost:8000/api/v1/segments/customers?priority=true&format=csv"
```

## Erreurs

| Code | Cas |
|---|---|
| 401 | Clé d'API absente ou invalide (si `ECI_API_KEY` est définie) |
| 404 | Client inconnu, sélection vide |
| 422 | Entrée invalide : valeur hors bornes, état inconnu, quantile ou période indisponibles |
| 503 | Artefact ou modèle manquant (`make install-artifacts`) : le message indique le fichier attendu |

Toutes les erreurs ont la forme `{"detail": "message lisible"}`.

## Configuration

| Variable | Rôle |
|---|---|
| `ECI_APP_DIR`, `ECI_MODELS_DIR` | Dossiers des tables et des modèles (défaut : `data/app`, `models`, puis `data/demo`) |
| `ECI_API_KEY` | Active l'authentification par l'en-tête `X-API-Key` |
| `ECI_CORS_ORIGINS` | Origines autorisées, séparées par des virgules (défaut : `http://localhost:8501`) |

Chaque réponse porte l'en-tête `X-Process-Time-Ms`.
