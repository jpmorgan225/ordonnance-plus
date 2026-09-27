# Ordonnance+ — L'assistant de lecture d'ordonnances pour le pharmacien
> **Hackathon Come Build with AI** (Abidjan, Côte d'Ivoire — Septembre 2026)  
> *Conçu selon la méthode Killer-SaaS / Ship Fast : Monolithe réactif, sécurisé, ancré dans le cadre réglementaire ivoirien.*

---

## 🎯 Le Problème & Le Pivot Responsable

* **Le piège classique de l'IA en santé :** Prétendre remplacer le médecin, inventer des posologies non écrites ou imposer des substitutions automatiques met directement la vie du patient en danger et se heurte à un refus catégorique des jurys et praticiens.
* **La solution Ordonnance+ :** **Pharmacist-in-the-Loop**. 
  * L'IA assiste la lecture et transcrit en 2 secondes l'ordonnance manuscrite.
  * **Règle d'or absolue : Ne rien déduire ni inventer.** Recopier fidèlement la posologie brute.
  * **Savoir dire "Je ne sais pas" :** Si une dose est ambiguë ou raturée, le système lève une alerte rouge et **bloque la validation** tant que le pharmacien n'a pas vérifié.
  * L'application ne prescrit pas : le pharmacien garde la pleine maîtrise et engage sa responsabilité professionnelle.

---

## 🚀 Fonctionnalités Clés du Prototype

1. **Transcription Multimodale Fidèle (Google AI Studio - Gemini Vision)** :
   * Détection de l'en-tête (médecin, établissement, patient, date).
   * Transcription des lignes avec indice de confiance (`haute` ou `douteux`).
   * Fallback local 100% infaillible pour garantir la réussite du live pitch sans dépendre du Wi-Fi.

2. **Catalogue Officiel des Prix en Côte d'Ivoire (3 852 médicaments)** :
   * Source : `pharmacies-de-garde.ci` (Catalogue officiel de référence).
   * Rapprochement automatique instantané (fuzzy match) avec affichage des prix en **FCFA**.
   * Script de synchronisation hebdomadaire automatisé (`scraper_prix.py` exécutable chaque samedi matin à 06:00 GMT).

3. **Garde-fou Médical Bloquant** :
   * Si une ligne comporte un doute non levé par le pharmacien, le bouton d'exportation officielle est verrouillé.

4. **Fiche Patient Officielle Prête à Imprimer** :
   * Fiche claire avec Visa du pharmacien, conseils personnalisés et contacts des pharmacies de garde d'Abidjan à proximité (Cocody, Plateau, Yopougon, Marcory...).

5. **Bonus Dictée Vocale Pharmacien (Web Speech API)** :
   * Permet au pharmacien de dicter à la voix ses conseils d'administration sans toucher au clavier.

---

## ⚡ Démarrage Rapide (1 Clic)

L'application est accessible en ligne :
👉 **[Ouvrir Ordonnance+ en production](https://ordonnance-plus.vercel.app/)**

### Lancer l'application en local

Pour démarrer une version locale sur votre machine :
```bash
# Activer l'environnement
source .venv/bin/activate

# Lancer le serveur en mode dev
uvicorn app:app --reload --host 127.0.0.1 --port 8000

# Tester la mise à jour du catalogue de prix CI
python3 scraper_prix.py
```

### Pour connecter votre clé Google AI Studio :
Ouvrez le fichier `.env` et collez votre clé :
```env
GEMINI_API_KEY=AIzaSy...
```
*(Si la clé n'est pas encore renseignée, l'application fonctionne automatiquement en mode étalon pré-calibré sans aucun bug).*

---

## 🎤 Guide de Pitch Jury (3 Minutes Chrono)

### Minute 1 : L'Accroche & Le Problème
> *"Chaque jour en Côte d'Ivoire, les pharmaciens d'officine passent un temps précieux à déchiffrer des écritures manuscrites médicales parfois illisibles. Une mauvaise lecture de dosage (ex: 250mg au lieu de 500mg) peut avoir des conséquences vitales.*  
> *Notre parti pris : l'IA ne doit pas remplacer le soignant, elle doit sécuriser son geste. Voici Ordonnance+."*

### Minute 2 : La Démo en Direct (L'Effet Wahou & La Sécurité)
1. **Montrer le Cas 1 (Lisible) :**
   * Clic sur `1. Cas Nominal`. En 2 secondes, les 3 médicaments apparaissent avec leur posologie fidèle et leur prix en FCFA issu du catalogue officiel ivoirien.
2. **Le Clou du Pitch — Montrer le Cas 2 (Le doute bloquant) :**
   * Clic sur `2. Dosage Ambigu`.
   * Montrer au jury la rature manuscrite sur la Ciprofloxacine.
   * Montrer l'alerte orange : *"Dosage manuscrit ambigu entre 250mg et 500mg"*.
   * **Pointer du doigt que le bouton de validation globale est CADENASSÉ !**
   * Dire au jury : *"Contrairement aux IA naïves qui hallucinent une réponse au hasard, notre système s'arrête et exige la validation humaine du praticien."*
   * Le pharmacien confirme la ligne $\rightarrow$ Le cadenas se débloque.

### Minute 3 : La Délivrance & L'Ancrage Local
* Clic sur `Valider & Générer la Fiche Patient`.
* La fiche grand format apparaît :
  * Posologie limpide pour le patient.
  * Référence des prix en FCFA (Catalogue national mis à jour chaque samedi).
  * Conseils d'administration (démontrer la dictée vocale en 5 secondes en parlant dans le micro).
  * Pharmacies de garde d'Abidjan pour la nuit.
* **Conclusion éthique :**
  > *"Ordonnance+ respecte scrupuleusement la loi ivoirienne n° 2013-450 sur la protection des données de santé : aucune donnée réelle de patient n'est exposée, et la décision finale reste à 100% entre les mains du pharmacien ivoirien."*
