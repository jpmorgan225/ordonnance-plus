# Ordonnance+ — Guide de Démonstration & Pitch Hackathon (15h30)

## 1. Repositionnement Clé
> **« Ordonnance+ est une IA de lecture et d'aide à la vérification d'ordonnances médicales qui transforme une écriture manuscrite incertaine en une fiche structurée que le patient peut vérifier avec son pharmacien, avec estimation indicative du budget et orientation vers les pharmacies de garde en service. »**

Le mot d'ordre pour le jury : **Vérification & Sécurité**, pas diagnostic ni prescription.

---

## 2. La phrase d'accroche technique (Killer Opener)
> **« Le vrai défi technique n'est pas seulement de faire de l'OCR sur une ordonnance. Le vrai défi est de transformer une écriture médicale manuscrite et ambiguë en information exploitable sans jamais inventer ce que l'IA ne voit pas. »**

---

## 3. Le Pipeline Technique (Où est l'IA, où est le Métier ?)

```text
               PHOTO ORDONNANCE (Upload direct / Caméra)
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │     GEMINI VISION     │ (IA Multimodale)
                     │  Extraction brute     │
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  VALIDATION PYDANTIC  │ (Contrat d'API strict)
                     │    Score de certitude │
                     └───────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       CONFIRMÉ (≥ 80%)                 INCERTAIN / NON IDENTIFIÉ
                 │                               │
                 ▼                               ▼
      ┌──────────────────────┐        ┌──────────────────────┐
      │  NORMALISATION &     │        │ ISOLEMENT DU DOUTE   │
      │  MATCHING RÉFÉRENTIEL│        │ "À vérifier en       │
      │  (Base locale CI)    │        │  officine"           │
      └──────────┬───────────┘        └──────────┬───────────┘
                 │                               │
                 ▼                               ▼
      Prix indicatif unitaire          Exclu du total estimé
                 │                     (Zéro hallucination)
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  PANIER ESTIMÉ INDICATIF│
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   PHARMACIES DE GARDE   │ (Géolocalisation consentie)
                    │   Appel direct & GPS    │
                    └─────────────────────────┘
```

---

## 4. Ce que vous montrez en direct (Démo de 3 minutes)

1. **Écran d'accueil épuré** :
   - Aucune image factice préchargée : montrez que l'application attend un vrai document.
   - Présentez le principe de **minimisation des données** : traitement éphémère en mémoire vive, aucune photo médicale n'est conservée sur le disque.

2. **Dépôt d'une ordonnance réelle** :
   - Glissez ou sélectionnez une vraie ordonnance.
   - Le **stepper en 4 étapes** s'anime sous les yeux du jury :
     1. *Extraction visuelle multimodale (Gemini)*
     2. *Évaluation de la confiance & détection des incertitudes*
     3. *Normalisation & Rapprochement avec le référentiel de Côte d'Ivoire*
     4. *Calcul du panier indicatif & pharmacies de garde*

3. **Les résultats avec niveaux de confiance** :
   - Montrez une ligne **CONFIRMÉE** (vert, jauge 95%) : texte brut lu, rapprochement base de données, prix indicatif en FCFA.
   - Montrez une ligne **INCERTAINE** (orange, jauge 62%) : dosage ambigu isolé avec son motif exact (*« Point d'attention : dosage illisible »*), marquée comme *« À chiffrer en officine »* et **non comptabilisée dans le budget total** pour ne pas tromper le patient.

4. **Pharmacies de garde & Géolocalisation** :
   - Cliquez sur *« Me localiser automatiquement »*.
   - Acceptez l'autorisation : les pharmacies d'Abidjan se trient instantanément par distance réelle (ex: *« À 450 m (~2 min) »*).
   - Montrez les deux boutons d'action : **Appel direct** (`tel:...`) et **Itinéraire GPS**.

5. **Fiche Patient Récapitulative** :
   - Cliquez sur *« Imprimer / Télécharger ma fiche patient »*.
   - Montrez le récapitulatif propre et imprimable que le patient emporte au comptoir de la pharmacie.

---

## 5. Réponses aux questions probables du jury

| Question du jury | Réponse recommandée |
|---|---|
| **« Pourquoi ne pas utiliser un simple OCR ? »** | *« Un OCR classique transcrit des caractères sans comprendre la sémantique médicale. Notre architecture utilise Gemini Vision pour extraire la structure, mais c'est notre moteur logiciel qui évalue la certitude, filtre les doutes et refuse catégoriquement d'extrapoler. »* |
| **« Et si l'IA hallucine un mauvais dosage ? »** | *« C'est notre choix d'architecture fondamental : si un caractère ou un dosage n'est pas indiscutable, il est classé 'INCERTAIN' et exclu de toute déduction. Le patient est explicitement orienté vers son pharmacien. »* |
| **« Les prix sont-ils garantis en pharmacie ? »** | *« Non, nous précisons clairement qu'il s'agit d'une estimation indicative basée sur le référentiel local. Le pharmacien reste le maître de la dispensation et des génériques substituables. »* |
| **« Qu'en est-il de la confidentialité des données de santé ? »** | *« L'application applique une politique stricte de minimisation : traitement éphémère en mémoire vive, aucune image n'est stockée sur nos serveurs. »* |
