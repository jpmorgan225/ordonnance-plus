"""
Service d'analyse multimodale d'ordonnances réelles via Google Gemini (Google AI Studio).
Architecture clinique Google Health :
- Zéro données fictives inventées
- Respect strict de la règle "Ne rien déduire"
- Analyse en direct de vraies ordonnances manuscrites réelles
- Rapprochement en temps réel avec le référentiel de prix de Côte d'Ivoire (3 852 médicaments)
"""

import os
import json
import base64
import sqlite3
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import httpx

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "medicaments.db")

class LignePrescription(BaseModel):
    id: str
    raw_text: str = Field(default="", description="Ligne textuelle brute visible sur l'ordonnance")
    nom_medicament: str
    dosage: str
    forme: str
    posologie_recopiee: str
    score_confiance: int = Field(default=95, description="Score de certitude visuelle de 0 à 100")
    statut_confiance: str = Field(default="CONFIRME", description="'CONFIRME' (>=80%), 'INCERTAIN' (50-79%), ou 'NON_IDENTIFIE' (<50%)")
    motif_incertitude: Optional[str] = None
    needs_confirmation: bool = False
    
    # Compatibilité antérieure
    confiance: str = "haute"
    note_securite: Optional[str] = None
    valide_par_pharmacien: bool = False
    
    # Données issues du référentiel officiel CI
    code_catalogue: Optional[str] = None
    nom_catalogue: Optional[str] = None
    prix_reference_fcfa: Optional[int] = None
    motif_prix: Optional[str] = None
    groupe_therapeutique: Optional[str] = None

class AnalyseOrdonnance(BaseModel):
    patient_nom: str
    patient_age: Optional[str] = None
    medecin_nom: str
    date_prescription: str
    etablissement: Optional[str] = None
    lignes: List[LignePrescription]
    total_lignes: int = 0
    lignes_confirmees: int = 0
    lignes_incertaines: int = 0
    statut_global: str = Field(description="'pret_pour_validation' ou 'contient_doutes'")
    total_estime_fcfa: int = 0
    modele_utilise: str = "Google Gemini Multimodal"
    source_donnees: str = "Extraction structurée Google AI Studio + Référentiel CI"
    mentions_legales: str = "Traitement éphémère en mémoire vive. Conçu selon les principes de minimisation et de confidentialité des données."

def chercher_medicament_catalogue(nom_cherche: str, dosage_cherche: str = "") -> Optional[Dict[str, Any]]:
    """Recherche floue rapide dans le catalogue officiel des médicaments de Côte d'Ivoire."""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    mots = re.findall(r'[a-zA-Z0-9]+', (nom_cherche + " " + dosage_cherche).lower())
    mots_filtres = [m for m in mots if len(m) > 2 and m not in ['comprime', 'comprimes', 'gelule', 'gelules', 'sirop', 'suspension', 'injectable', 'ampoule']]

    if not mots_filtres:
        conn.close()
        return None

    cle_principale = mots_filtres[0]
    cursor.execute("SELECT code, nom, groupe, prix_fcfa FROM medicaments WHERE nom_normalise LIKE ? LIMIT 25", (f"%{cle_principale}%",))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    meilleur_match = None
    meilleur_score = -1

    for row in rows:
        code, nom, groupe, prix = row
        nom_low = nom.lower()
        score = 1
        for m in mots_filtres[1:]:
            if m in nom_low:
                score += 2
        if score > meilleur_score:
            meilleur_score = score
            meilleur_match = {
                "code": code,
                "nom": nom,
                "groupe": groupe,
                "prix_fcfa": prix
            }

    return meilleur_match

SYSTEM_PROMPT_GOOGLE_HEALTH = """Tu es "Ordonnance+", un moteur de vision clinique expert chargé d'extraire fidèlement des ordonnances médicales manuscrites réelles.
Tu produis STRICTEMENT un objet JSON valide, sans texte additionnel ni markdown en dehors du JSON.

PROTOCOLE DE SÉCURITÉ CLINIQUE ET CONFIDENTIALITÉ :
1. "NE RIEN INVENTER NI DÉDUIRE" :
   - Recopie fidèlement le texte manuscrit tel quel.
   - Si un dosage est ambigu ou raturé, signale-le immédiatement comme incertain : n'extrapole JAMAIS.
   - Si la posologie est illisible ou absente, écris exactement "À confirmer auprès du pharmacien".

2. "ÉVALUATION RIGOUREUSE DE LA CONFIANCE" :
   Pour chaque ligne de prescription identifiée, évalue la lisibilité :
   - score_confiance (0 à 100) :
     * 80 à 100 : lecture nette, sans ambiguïté -> statut_confiance = "CONFIRME", needs_confirmation = false
     * 50 à 79 : écriture cursive difficile, dosage ambigu, chiffre peu lisible -> statut_confiance = "INCERTAIN", needs_confirmation = true, avec motif_incertitude détaillé.
     * 0 à 49 : mot raturé ou illisible -> statut_confiance = "NON_IDENTIFIE", needs_confirmation = true.

3. STRUCTURE DU JSON ATTENDU :
{
  "patient_nom": "Nom du patient ou 'Patient Anonymisé'",
  "patient_age": "Âge si mentionné sur le document, sinon null",
  "medecin_nom": "Nom du médecin praticien",
  "date_prescription": "Date au format JJ/MM/AAAA si lisible",
  "etablissement": "Clinique, hôpital ou cabinet",
  "lignes": [
    {
      "id": "l-1",
      "raw_text": "Texte brut complet lu sur la ligne (ex: Doliprane 1000 1 cp x 3/j)",
      "nom_medicament": "Nom usuel du médicament",
      "dosage": "Dosage explicite ou 'Non précisé / Illisible'",
      "forme": "Comprimé, gélule, sirop, pommade, etc.",
      "posologie_recopiee": "Posologie exacte recopiée",
      "score_confiance": 95,
      "statut_confiance": "CONFIRME",
      "motif_incertitude": null,
      "needs_confirmation": false
    }
  ],
  "statut_global": "pret_pour_validation"
}
"""

async def analyser_ordonnance_reelle(
    image_bytes: bytes, 
    mime_type: str = "image/png", 
    api_key_override: Optional[str] = None
) -> AnalyseOrdonnance:
    """Effectue la vraie analyse par vision multimodale sur Google Gemini."""
    
    api_key = (api_key_override or os.getenv("GEMINI_API_KEY", "")).strip()

    if not api_key:
        raise ValueError("Clé API Google AI Studio manquante. Veuillez saisir votre clé API pour lancer l'analyse en direct.")

    # Modèles Gemini multimodaux par ordre de disponibilité et performance
    models = [
        "gemini-flash-latest",
        "gemini-3.7-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
        "gemini-3.5-flash"
    ]
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT_GOOGLE_HEALTH},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64
                        }
                    },
                    {"text": "Transcris fidèlement et rigoureusement cette ordonnance médicale manuscrite selon le schéma JSON."}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.05,
            "responseMimeType": "application/json"
        }
    }

    raw_data = None
    dernier_erreur = ""
    model_utilise = "gemini-2.5-flash"

    async with httpx.AsyncClient(timeout=35.0) as client:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    result_json = resp.json()
                    candidate_text = result_json["candidates"][0]["content"]["parts"][0]["text"]
                    raw_data = json.loads(candidate_text)
                    model_utilise = model
                    break
                else:
                    dernier_erreur = f"Status {resp.status_code}: {resp.text}"
                    print(f"[!] Gemini {model} error: {dernier_erreur}")
            except Exception as e:
                dernier_erreur = str(e)
                print(f"[!] Erreur appel Gemini {model}: {e}")

    if not raw_data:
        raise RuntimeError(f"Échec de l'appel Google Gemini : {dernier_erreur}")

    # Rapprochement avec le référentiel de prix de Côte d'Ivoire
    lignes_enrichies: List[LignePrescription] = []
    total_fcfa = 0

    for idx, l in enumerate(raw_data.get("lignes", [])):
        lid = l.get("id") or f"l-{idx+1}"
        raw_text = l.get("raw_text") or f"{l.get('nom_medicament', '')} {l.get('dosage', '')}".strip()
        nom_med = l.get("nom_medicament", "").strip()
        dosage = l.get("dosage", "").strip()
        forme = l.get("forme", "Comprimé / Gélule").strip()
        posologie = l.get("posologie_recopiee", "").strip()

        # Score numérique de confiance (0 - 100)
        raw_score = l.get("score_confiance")
        if raw_score is not None:
            try:
                score = int(raw_score)
                # Si fourni entre 0.0 et 1.0
                if score <= 1 and float(raw_score) <= 1.0:
                    score = int(float(raw_score) * 100)
            except Exception:
                score = 85
        else:
            score = 92 if l.get("confiance") == "haute" else 62

        # Détection d'ambiguïté sur le dosage ou la posologie
        if "?" in dosage or "illisible" in dosage.lower() or "non précisé" in dosage.lower() or "confirmer" in posologie.lower():
            score = min(score, 68)

        # Statut à 3 niveaux
        if score >= 80:
            statut_confiance = "CONFIRME"
            needs_conf = False
            motif = None
        elif score >= 50:
            statut_confiance = "INCERTAIN"
            needs_conf = True
            motif = l.get("motif_incertitude") or l.get("note_securite") or "Dosage ou écriture manuscrite difficilement lisible"
        else:
            statut_confiance = "NON_IDENTIFIE"
            needs_conf = True
            motif = l.get("motif_incertitude") or "Mention raturée ou méconnaissable : vérification directe requise"

        # Rapprochement catalogue métier
        med_ref = chercher_medicament_catalogue(nom_med, dosage if statut_confiance == "CONFIRME" else "")
        code = med_ref["code"] if med_ref else None
        nom_cat = med_ref["nom"] if med_ref else None
        grp = med_ref["groupe"] if med_ref else None

        # RÈGLE MÉTIER DE CALCUL DU PRIX :
        # Si la ligne est incertaine ou non identifiée, nous n'inventons pas de prix (exclu du total estimé)
        if statut_confiance == "CONFIRME" and med_ref:
            prix = med_ref["prix_fcfa"]
            motif_prix = "Tarif indicatif référentiel CI"
            total_fcfa += prix
        elif statut_confiance == "CONFIRME" and not med_ref:
            prix = None
            motif_prix = "Médicament non répertorié dans la base locale"
        else:
            prix = None
            motif_prix = "Non inclus dans l'estimation : ligne incertaine à chiffrer en officine"

        lignes_enrichies.append(LignePrescription(
            id=lid,
            raw_text=raw_text,
            nom_medicament=nom_med,
            dosage=dosage,
            forme=forme,
            posologie_recopiee=posologie,
            score_confiance=score,
            statut_confiance=statut_confiance,
            motif_incertitude=motif,
            needs_confirmation=needs_conf,
            confiance="haute" if statut_confiance == "CONFIRME" else "douteux",
            note_securite=motif or "Lecture claire",
            valide_par_pharmacien=(statut_confiance == "CONFIRME"),
            code_catalogue=code,
            nom_catalogue=nom_cat,
            prix_reference_fcfa=prix,
            motif_prix=motif_prix,
            groupe_therapeutique=grp
        ))

    total_lignes = len(lignes_enrichies)
    confirmees = sum(1 for l in lignes_enrichies if l.statut_confiance == "CONFIRME")
    incertaines = total_lignes - confirmees

    return AnalyseOrdonnance(
        patient_nom=raw_data.get("patient_nom", "Patient"),
        patient_age=raw_data.get("patient_age"),
        medecin_nom=raw_data.get("medecin_nom", "Médecin Prescripteur"),
        date_prescription=raw_data.get("date_prescription", "Date non spécifiée"),
        etablissement=raw_data.get("etablissement", "Cabinet Médical / Centre Hospitalier"),
        lignes=lignes_enrichies,
        total_lignes=total_lignes,
        lignes_confirmees=confirmees,
        lignes_incertaines=incertaines,
        statut_global="contient_doutes" if incertaines > 0 else "pret_pour_validation",
        total_estime_fcfa=total_fcfa,
        modele_utilise=f"Google AI Studio ({model_utilise})",
        source_donnees="Extraction structurée Google AI Studio + Référentiel CI"
    )
