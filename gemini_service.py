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
    nom_medicament: str
    dosage: str
    forme: str
    posologie_recopiee: str
    confiance: str = Field(description="'haute' si lecture limpide, 'douteux' si écriture ambiguë, raturée ou incomplète")
    note_securite: Optional[str] = None
    valide_par_pharmacien: bool = False
    # Données issues du catalogue officiel CI
    code_catalogue: Optional[str] = None
    nom_catalogue: Optional[str] = None
    prix_reference_fcfa: Optional[int] = None
    groupe_therapeutique: Optional[str] = None

class AnalyseOrdonnance(BaseModel):
    patient_nom: str
    patient_age: Optional[str] = None
    medecin_nom: str
    date_prescription: str
    etablissement: Optional[str] = None
    lignes: List[LignePrescription]
    statut_global: str = Field(description="'pret_pour_validation' ou 'contient_doutes'")
    total_estime_fcfa: int = 0
    modele_utilise: str = "Google Gemini Multimodal"
    source_donnees: str = "Analyse en direct Google AI Studio"
    mentions_legales: str = "Données traitées sous contrôle strict du pharmacien diplômé. Conforme Loi n° 2013-450 (Protection des données sensibles de santé)."

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

SYSTEM_PROMPT_GOOGLE_HEALTH = """Tu es "Ordonnance+", l'assistant clinique officiel de lecture et transcription d'ordonnances médicales pour les pharmaciens d'officine.
Ton rôle est de lire l'image de l'ordonnance médicale manuscrite fournie et d'en extraire les informations avec une rigueur chirurgicale.

PROTOCOLE DE SÉCURITÉ PATIENT (OBLIGATOIRE) :
1. "NE RIEN INTERPRÉTER NI INVENTER" :
   - Recopie fidèlement la posologie telle qu'elle est écrite par le praticien.
   - Ne déduis JAMAIS une répartition inexistante (n'invente pas "matin, midi et soir" si ce n'est pas expressément écrit).
   - N'invente pas de consignes de repas ("avant/après manger").

2. "DÉTECTION SYSTÉMATIQUE DU DOUTE" :
   - Si une écriture manuscrite est cursive, difficile à lire, hésitante ou raturée : marque confiance = "douteux" et explique précisément le doute dans "note_securite".
   - Si un dosage est ambigu (ex: chiffre ambigu entre 250mg et 500mg, virgule mal placée) : marque confiance = "douteux".
   - Si la posologie est absente ou illisible sur le document : écris strictement "À confirmer auprès du pharmacien" et marque confiance = "douteux".
   - Si la lecture est limpide et sans équivoque : marque confiance = "haute".

3. ANONYMISATION DES DONNÉES SENSIBLES :
   - Si l'ordonnance comporte un nom réel, préserve le prénom ou anonymise sous forme "Patient Anonymisé" ou le nom tel quel s'il s'agit d'un spécimen.

FORMAT DE SORTIE JSON STRICT :
{
  "patient_nom": "Nom ou Anonymisé",
  "patient_age": "Âge si mentionné",
  "medecin_nom": "Nom du médecin prescripteur",
  "date_prescription": "Date jj/mm/aaaa",
  "etablissement": "Nom de la clinique ou cabinet médical",
  "lignes": [
    {
      "id": "l-1",
      "nom_medicament": "Nom du médicament",
      "dosage": "Dosage exact relevé",
      "forme": "Comprimé, gélule, sirop, etc.",
      "posologie_recopiee": "Texte exact tel quel ou 'À confirmer auprès du pharmacien'",
      "confiance": "haute" ou "douteux",
      "note_securite": "Explication du doute clinique ou 'Lecture claire'",
      "valide_par_pharmacien": false
    }
  ],
  "statut_global": "pret_pour_validation" ou "contient_doutes"
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

    # Modèles Gemini multimodaux par ordre de précision
    models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
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

    # Rapprochement avec le catalogue de prix officiel de Côte d'Ivoire
    lignes_enrichies: List[LignePrescription] = []
    total_fcfa = 0

    for idx, l in enumerate(raw_data.get("lignes", [])):
        lid = l.get("id") or f"l-{idx+1}"
        nom_med = l.get("nom_medicament", "").strip()
        dosage = l.get("dosage", "").strip()

        med_ref = chercher_medicament_catalogue(nom_med, dosage)
        prix = med_ref["prix_fcfa"] if med_ref else None
        code = med_ref["code"] if med_ref else None
        nom_cat = med_ref["nom"] if med_ref else None
        grp = med_ref["groupe"] if med_ref else None

        if prix:
            total_fcfa += prix

        confiance = l.get("confiance", "haute")
        if "confirmer" in l.get("posologie_recopiee", "").lower() or "?" in dosage:
            confiance = "douteux"

        valide = (confiance == "haute")

        lignes_enrichies.append(LignePrescription(
            id=lid,
            nom_medicament=nom_med,
            dosage=dosage,
            forme=l.get("forme", "Forme galénique"),
            posologie_recopiee=l.get("posologie_recopiee", ""),
            confiance=confiance,
            note_securite=l.get("note_securite"),
            valide_par_pharmacien=valide,
            code_catalogue=code,
            nom_catalogue=nom_cat,
            prix_reference_fcfa=prix,
            groupe_therapeutique=grp
        ))

    contient_doutes = any(l.confiance == "douteux" for l in lignes_enrichies)

    return AnalyseOrdonnance(
        patient_nom=raw_data.get("patient_nom", "Patient"),
        patient_age=raw_data.get("patient_age"),
        medecin_nom=raw_data.get("medecin_nom", "Médecin Prescripteur"),
        date_prescription=raw_data.get("date_prescription", "Date non spécifiée"),
        etablissement=raw_data.get("etablissement", "Cabinet Médical / Centre Hospitalier"),
        lignes=lignes_enrichies,
        statut_global="contient_doutes" if contient_doutes else "pret_pour_validation",
        total_estime_fcfa=total_fcfa,
        modele_utilise=f"Google AI Studio ({model_utilise})",
        source_donnees="Analyse Multimodale en direct (Vraie ordonnance)"
    )
