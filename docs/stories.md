# User Stories — Ordonnance+

> One story = one shippable slice, written to be executed by an agent.
> Id format: `s<number>-<short-slug>`

---

## Story s01-transcription-fidele — Transcription Multimodale "Ne Rien Déduire"
**As a** pharmacien d'officine  
**I want** soumettre la photo d'une ordonnance manuscrite pour en extraire fidèlement les lignes écrites  
**so that** je gagne du temps de saisie sans risquer qu'une posologie fictive soit inventée par l'IA.

### Complexity
2

### Acceptance criteria
- [x] L'image est analysée par vision multimodale (Gemini Vision ou fallback étalon).
- [x] La posologie est recopiée mot pour mot.
- [x] Si la posologie est coupée ou absente, le champ contient explicitement *"À confirmer auprès du pharmacien"*.
- [x] L'analyse renvoie un indice de confiance : `haute` ou `douteux`.

### Dependencies
Aucune.

### Agentic notes
Fichiers : `gemini_service.py`, `app.py`.

---

## Story s02-catalogue-prix-ci — Rapprochement Prix Officiel Côte d'Ivoire
**As a** pharmacien et patient  
**I want** voir automatiquement le prix officiel réglementé en FCFA pour chaque médicament  
**so that** le montant estimé du panier soit clair et transparent dès le comptoir.

### Complexity
2

### Acceptance criteria
- [x] Base SQLite indexant 3 852 médicaments issus de `pharmacies-de-garde.ci`.
- [x] Script de mise à jour hebdomadaire (`scraper_prix.py`).
- [x] Correspondance automatique instantanée (fuzzy matching) entre nom manuscrit et dénomination officielle.
- [x] Calcul du total indicatif en FCFA en temps réel.

### Dependencies
s01-transcription-fidele.

### Agentic notes
Fichiers : `scraper_prix.py`, `data/medicaments.db`, `gemini_service.py`.

---

## Story s03-garde-fou-pharmacien — Validation Bloquante & Sécurité Médicale
**As a** pharmacien responsable  
**I want** que toute incertitude (dosage raturé, ambiguïté) bloque la certification finale  
**so that** aucune ordonnance mal interprétée ne soit délivrée par inadvertance.

### Complexity
3

### Acceptance criteria
- [x] Si une ligne est marquée `douteux`, un bandeau d'alerte spécifique s'affiche.
- [x] Le bouton "Valider & Générer la Fiche" est désactivé avec un cadenas.
- [x] Le pharmacien peut modifier le dosage ou la posologie en 1 clic.
- [x] La confirmation explicite de la ligne par le pharmacien débloque la validation.

### Dependencies
s01-transcription-fidele.

### Agentic notes
Fichiers : `app.py` (`POST /api/validate-prescription`), `static/index.html`.

---

## Story s04-fiche-patient-impression — Fiche de Dispensation & Dictée Vocale
**As a** patient et pharmacien  
**I want** imprimer une fiche récapitulative claire avec Visa officiel, conseils et pharmacies de garde  
**so that** le patient reparte avec un document lisible et sécurisé pour son traitement.

### Complexity
2

### Acceptance criteria
- [x] Modal responsive et vue d'impression propre (CSS print ready).
- [x] Visa officiel unique généré (`VISA-PHARM-CI-2026-XXXX`).
- [x] Mention des pharmacies de garde d'Abidjan à proximité.
- [x] Dictée vocale opérationnelle pour dicter les conseils du pharmacien via le micro.

### Dependencies
s03-garde-fou-pharmacien.

### Agentic notes
Fichiers : `static/index.html`.
