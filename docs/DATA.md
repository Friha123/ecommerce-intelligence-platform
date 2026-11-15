# Fichiers de données de l'application

## `data/app/` (tables)

| Fichier | Produit par | Contenu |
|---|---|---|
| `kpi_month_state.csv` | `build_app_data` | Agrégats mois × état du client : commandes, CA, frais de port, durées, retards |
| `delivery_hist.csv` | `build_app_data` | Histogramme des durées réelle et promise (jours) |
| `state_centroids.csv` | `build_app_data` | Latitude et longitude médianes par état |
| `route_stats.csv` | `build_app_data` | Dernier historique connu par trajet (état vendeur → état client) |
| `feature_defaults.json` | `build_app_data` | Médianes des variables et modalités fréquentes (complètent la saisie) |
| `review_by_lateness.csv` | `build_app_data` | Note moyenne selon le retard vécu |
| `app_manifest.json` | `build_app_data` | Métadonnées (`demo`, période, nombre de clients…) |
| `model1_rolling_*.csv`, `model1_mae_by_month.csv`, `model1_static_test_fair.csv` | 05a | Évaluation glissante et comparaison statique équitable |
| `model1_promise_simulator*.csv` | 05a | Compromis promesse par quantile / retards (global et par mois) |
| `model1_manifest.json` | 05a | Variante retenue, gains |
| `model2_test_scores.csv` | 05b | Score de risque par commande du test |
| `model2_rolling_*.csv`, `model2_static_test_topk.csv`, `model2_profitability.csv` | 05b | Évaluation des six approches, rentabilité |
| `model2_manifest.json` | 05b | Approche retenue, métriques |
| `customer_segments_final.csv` | 05c | Segment, niveau de valeur et action par client |
| `segment_*.csv`, `segmentation_*` | 05c | Profils, grille d'actions, comparaison des variantes |

## `models/`

| Fichier | Produit par | Contenu |
|---|---|---|
| `model1_point_lgbm.txt` | 05a | LightGBM L1 : durée prévue |
| `model1_quantile_{50,70,80,85,90,95}_lgbm.txt` | 05a | LightGBM quantiles : promesses possibles |
| `model1_features.json`, `model1_category_levels.json` | 05a | Variables, quantiles, modalités des catégories |
| `model2_components.joblib`, `model2_config.json` | 05b | Régresseur de l'écart durée − promesse, seuils par rang |

## Confidentialité

Le jeu de données Olist est public et anonymisé. Les identifiants clients du tableau de bord sont les `customer_unique_id` du jeu de données, sans donnée personnelle.
