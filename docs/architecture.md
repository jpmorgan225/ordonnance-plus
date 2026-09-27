# Architecture — Ordonnance+

## Stack
- **Backend :** Python 3.14 + FastAPI + Pydantic v2 (Validation stricte JSON et typage)
- **Serveur d'exécution :** Uvicorn (haute performance asynchrone)
- **Base de données :** SQLite locale (`data/medicaments.db`) avec 3 852 médicaments indexés
- **IA Multimodale :** Google AI Studio (Gemini 2.5 Flash / 1.5 Flash via REST HTTPX) + Moteur étalon de secours local
- **Frontend :** Single-Page Interface moderne sans framework de build lourd (HTML5 + Tailwind CSS CDN + Lucide Icons + Web Speech API)
- **Scraping / Sync :** BeautifulSoup4 + Requests (`scraper_prix.py` hebdomadaire)

## Repo structure
```
/
├── data/
│   ├── medicaments.db         # SQLite des 3 852 médicaments et prix CI
│   └── medicaments_ci.json    # Export JSON avec métadonnées de synchronisation
├── docs/                      # Documentation du cadrage Killer-SaaS
│   ├── prd.md
│   ├── stories.md
│   ├── architecture.md
│   └── design-system.md
├── static/                    # Frontend Web & Assets
│   ├── index.html             # Application Web Single-Page
│   └── samples/               # Les 3 ordonnances étalons de démonstration
├── templates/                 # Templates Killer-SaaS de référence
├── app.py                     # Serveur FastAPI et API REST
├── gemini_service.py          # Service de vision multimodale et règles de sécurité
├── scraper_prix.py            # Pipeline de synchronisation hebdomadaire du catalogue
├── generate_samples.py        # Générateur d'ordonnances fictives réalistes
└── README.md                  # Guide de démarrage et script de pitch
```

## Patterns & conventions
- **Monolithe Lean :** Zéro friction de build, lancement instantané en 1 commande `uvicorn app:app`.
- **Fail-Closed Safety :** Si un doute subsiste, l'API refuse formellement de valider (HTTP 400).
- **Offline Resilient :** Les 3 cas de démonstration fonctionnent avec ou sans clé API, assurant 100% de succès pendant le pitch.

## Data model
- `medicaments` : `(id, code, nom, nom_normalise, groupe, prix_fcfa, date_maj)`
- `meta_sync` : `(cle, valeur)` pour tracer la dernière synchronisation hebdomadaire du samedi matin.
- `LignePrescription` : `(id, nom_medicament, dosage, forme, posologie_recopiee, confiance, note_securite, valide_par_pharmacien, prix_reference_fcfa)`

## Integration points
- **Source des prix :** `https://www.pharmacies-de-garde.ci/prix-des-medicaments-en-pharmacie-en-cote-divoire/`
- **Modèle Vision :** Google Generative Language API (`gemini-2.5-flash` / `gemini-1.5-flash`).
