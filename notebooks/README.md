# Notebooks (exécutés sur Kaggle)

À exécuter dans l'ordre. Chaque notebook décrit son objectif et ses sorties en en-tête.

| # | Notebook | CRISP-DM | Sortie |
|---|---|---|---|
| 02 | `02_data_understanding_eda` | Data Understanding | Analyse exploratoire, tests, SQL |
| 03 | `03_data_preparation` | Data Preparation | 3 jeux de données (`model1_…`, `model2_…`, `model3_…`) |
| 04a | `04a_model1_delivery_duration` | Modeling | Comparaison de 24 modèles de régression |
| 04b | `04b_model2_late_risk` | Modeling | Comparaison de 17 modèles de classification |
| 04c | `04c_model3_customer_segmentation` | Modeling | Comparaison de 16 algorithmes de clustering |
| 05a | `05a_model1_corrections_final` | Evaluation | **Fichiers de déploiement du modèle 1** |
| 05b | `05b_model2_corrections_final` | Evaluation | **Fichiers de déploiement du modèle 2** |
| 05c | `05c_model3_segmentation_final` | Evaluation | **Fichiers de déploiement du modèle 3** |

Le notebook d'analyse de la qualité des données (étape 3 de Data Understanding) complète la phase 2.
Les notebooks 05a, 05b, 05c écrivent dans `/kaggle/working/deploy/` : télécharger ce dossier, puis `make install-artifacts`.
