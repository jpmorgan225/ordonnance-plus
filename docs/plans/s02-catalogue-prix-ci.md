---
track: flow
validated: yes
story: s02-catalogue-prix-ci
---

# Plan — s02-catalogue-prix-ci

- [x] Extraction de 3 852 médicaments de `pharmacies-de-garde.ci`.
- [x] Base SQLite locale et script de synchronisation hebdomadaire (`scraper_prix.py`).
- [x] Recherche floue (fuzzy lookup) pour associer automatiquement le prix officiel en FCFA.
- [x] Calcul en direct du total de l'ordonnance.
