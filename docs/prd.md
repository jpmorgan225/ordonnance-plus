# PRD — Ordonnance+ (L'Assistant de Lecture pour le Pharmacien)

## Target SaaS
Logiciels traditionnels de gestion d'officine (LGO) et outils généralistes d'OCR médical (ex: Nuance DAX, solutions hospitalières lourdes à abonnement mensuel élevé).

## Kill mode
**Competing product / Micro-SaaS verticalisé pour l'Afrique de l'Ouest (Côte d'Ivoire)** :
Remplacer les solutions d'OCR lentes, complexes et coûteuses par un assistant léger, immédiat, centré sur la sécurité du pharmacien en officine.

## Why kill it
- Les logiciels d'officine actuels ne déchiffrent pas les ordonnances manuscrites et forcent une saisie manuelle fastidieuse (3 à 5 minutes par ordonnance).
- Les modèles d'IA générique "grand public" hallucinent des posologies dangereuses et créent un risque médicolégal majeur en tentant de prescrire ou substituer directement.
- Manque total d'intégration avec le catalogue de prix officiel en FCFA encadré par le Ministère de la Santé en Côte d'Ivoire.

## Problem
- En officine en Côte d'Ivoire, les ordonnances manuscrites sont souvent rédigées en écriture cursive rapide, parfois raturée ou tronquée.
- Le déchiffrage manuel génère de l'attente au comptoir et un risque réel d'erreur de dosage (ex: confondre 250mg et 500mg).
- **Le besoin :** Un outil d'assistance pour le pharmacien qui numérise instantanément, recopie fidèlement sans rien inventer, lève un drapeau rouge au moindre doute et chiffre l'ordonnance en FCFA selon le catalogue officiel.

## Target users
- **Utilisateurs cibles :** Pharmaciens titulaires, pharmaciens assistants et préparateurs en pharmacie d'officine (Abidjan et intérieur de la Côte d'Ivoire).

---

## Perimeter — the 20% that matters

### Replicated (core loop)
| Feature | Complexity (1-5) | Why this score |
|---|---|---|
| **Transcription Visuelle Fidèle (Multimodal)** | 2 | Utilisation de Gemini Vision avec prompt strict de recopie brute. |
| **Garde-fou Médical Bloquant (Pharmacist-in-the-loop)** | 3 | Ligne par ligne : si confiance = "douteux", validation finale bloquée tant que non validée. |
| **Rapprochement Catalogue Officiel CI (3 852 méd.)** | 2 | Recherche locale SQLite sur le référentiel de `pharmacies-de-garde.ci` avec prix en FCFA. |
| **Génération & Impression Fiche Patient Sécurisée** | 1 | Fiche claire, imprimable, avec Visa officiel et pharmacies de garde d'Abidjan. |
| **Dictée Vocale Pharmacien (Bonus audio)** | 2 | Web Speech API pour ajouter des conseils sans frappe clavier. |

### Explicitly NOT replicated (graveyard — ce qu'on jette)
- ❌ **Interactions médicamenteuses bricolées :** Dangereux sans base clinique certifiée complète et historique patient.
- ❌ **Auto-substitution par génériques :** L'IA ne doit pas imposer de substitution ; la décision appartient au pharmacien.
- ❌ **Suivi de stock temps réel fantaisiste :** Aucune promesse de stock non vérifiable. On affiche le prix indicatif officiel régulé.
- ❌ **Espace patient / Téléconsultation / Tunnel de connexion lourd :** Zéro friction, usage comptoir immédiat.

### The angle (done differently / better)
- **Le principe "Ne rien déduire" :** Si une posologie est absente ou illisible, l'IA indique formellement *"À confirmer auprès du pharmacien"* au lieu d'inventer des prises matin/midi/soir.
- **Fail-closed :** L'IA sait dire *"Je ne sais pas"*. Une incertitude bloque la certification.
- **Ancrage réglementaire local :** Conforme aux préconisations de l'ARTCI (Loi n° 2013-450 sur les données de santé) grâce à des jeux d'ordonnances anonymisés et un chiffrement local.

---

## Constraints
- **Hackathon Come Build with AI** : 4 heures de développement.
- **Démo résiliente (Zero-Crash)** : Fonctionne en direct avec l'API Google AI Studio et dispose d'un fallback étalon local si le Wi-Fi faiblit.
- **Réglementation ivoirienne** : Données sensibles, aucun envoi de nom de patient réel.

## Success criteria
- [x] L'analyse d'une ordonnance manuscrite prend moins de 3 secondes.
- [x] Une ligne douteuse (ex: dosage raturé) bloque le bouton de validation finale.
- [x] Les prix en FCFA sont automatiquement rapprochés depuis la base locale (3 852 médicaments).
- [x] Fiche patient certifiée prête à être imprimée en 1 clic.
