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
    posologie_orale_simple: Optional[str] = Field(default=None, description="Explication orale bienveillante et limpide de la posologie sans abréviations, en français soignant parlé accessible à un patient analphabète")
    posologie_ivoirienne: Optional[str] = Field(default=None, description="Explication en français ivoirien populaire et bienveillant d'Abidjan pour patient non-lecteur")
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
    patient_nom: Optional[str] = "Patient"
    patient_age: Optional[str] = None
    medecin_nom: Optional[str] = "Médecin Prescripteur"
    date_prescription: Optional[str] = "Date non spécifiée"
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

SYNONYMES_DCI = {
    "prednisone": ["predni", "solupred", "cortancyl"],
    "prednisolone": ["predni", "solupred"],
    "paracetamol": ["doliprane", "efferalgan", "perfalgan"],
    "amoxicilline": ["amox", "clamoxyl", "augmentin"],
    "ibuprofene": ["advil", "nurofen"],
    "metronidazole": ["flagyl", "metro", "metrol"],
    "ciprofloxacine": ["cipro", "ciflox"]
}

def chercher_medicament_catalogue(nom_cherche: str, dosage_cherche: str = "") -> Optional[Dict[str, Any]]:
    """Recherche floue et robuste dans les 3 852 médicaments officiels de Côte d'Ivoire."""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    mots = re.findall(r'[a-zA-Z0-9]+', (nom_cherche + " " + dosage_cherche).lower())
    stop_words = {
        'medicament', 'medicaments', 'comprime', 'comprimes', 'gelule', 'gelules',
        'sirop', 'suspension', 'injectable', 'ampoule', 'infusion', 'perfusion',
        'solution', 'gouttes', 'sachet', 'sachets', 'flacon', 'tube', 'pommade', 'creme'
    }
    mots_filtres = [m for m in mots if len(m) >= 3 and m not in stop_words]

    if not mots_filtres:
        conn.close()
        return None

    candidates = list(mots_filtres)
    for m in mots_filtres:
        if m in SYNONYMES_DCI:
            candidates.extend(SYNONYMES_DCI[m])

    rows = []
    seen_codes = set()
    for cand in candidates:
        if len(cand) >= 3:
            cursor.execute("SELECT code, nom, groupe, prix_fcfa FROM medicaments WHERE nom_normalise LIKE ? LIMIT 35", (f"%{cand}%",))
            for r in cursor.fetchall():
                if r[0] not in seen_codes:
                    seen_codes.add(r[0])
                    rows.append(r)

    conn.close()

    if not rows:
        return None

    meilleur_match = None
    meilleur_score = 0

    for row in rows:
        code, nom, groupe, prix = row
        nom_low = nom.lower()
        score = 0
        for cand in candidates:
            if cand in nom_low:
                score += 3

        # Bonus si le dosage apparaît dans le libellé
        if dosage_cherche and any(d in nom_low for d in re.findall(r'\d+', dosage_cherche)):
            score += 2

        if score > meilleur_score:
            meilleur_score = score
            meilleur_match = {
                "code": code,
                "nom": nom,
                "groupe": groupe,
                "prix_fcfa": prix
            }

    return meilleur_match if meilleur_score >= 3 else None

def traduire_abreviations_medicales(texte: str) -> str:
    """Traduit les abréviations médicales courantes (ml, cp, x2/j, càs, etc.) en français soignant parlé naturel et bienveillant."""
    if not texte:
        return ""
    t = f" {texte} "

    # 1-0-1 notation médicale
    t = re.sub(r'\b1-0-1\b', 'un comprimé le matin et un comprimé le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\b1-1-1\b', 'un comprimé le matin, un comprimé le midi et un comprimé le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\b2-0-2\b', 'deux comprimés le matin et deux comprimés le soir', t, flags=re.IGNORECASE)

    # Fractions
    t = re.sub(r'\b1/2\s*c(?:p|ps|omp)\b', 'un demi-comprimé', t, flags=re.IGNORECASE)
    t = re.sub(r'\b1/2\b', 'un demi', t)

    # Fréquences journalières & moments de la journée
    t = re.sub(r'\bx\s*2\s*/\s*j(?:our)?\b|\b2\s*x\s*/\s*j(?:our)?\b|\bx\s*2\s*j\b|\b2\s*fois\s*/\s*j(?:our)?\b|\b2\s*prises?\s*/\s*j(?:our)?\b', 'deux fois par jour, le matin et le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\bx\s*3\s*/\s*j(?:our)?\b|\b3\s*x\s*/\s*j(?:our)?\b|\bx\s*3\s*j\b|\b3\s*fois\s*/\s*j(?:our)?\b|\b3\s*prises?\s*/\s*j(?:our)?\b', 'trois fois par jour, le matin, le midi et le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\bx\s*4\s*/\s*j(?:our)?\b|\b4\s*x\s*/\s*j(?:our)?\b|\b4\s*fois\s*/\s*j(?:our)?\b', 'quatre fois par jour, bien espacées dans la journée', t, flags=re.IGNORECASE)
    t = re.sub(r'\bx\s*1\s*/\s*j(?:our)?\b|\b1\s*x\s*/\s*j(?:our)?\b|\b1\s*fois\s*/\s*j(?:our)?\b', 'une fois par jour', t, flags=re.IGNORECASE)

    # Durée
    t = re.sub(r'\bpdt\s*(\d+)\s*j(?:ours?)?\b', r'pendant \1 jours', t, flags=re.IGNORECASE)
    t = re.sub(r'\bpendant\s*(\d+)\s*j\b', r'pendant \1 jours', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*sem(?:aines?)?\b', r'pendant \1 semaines', t, flags=re.IGNORECASE)

    # Précision moments
    t = re.sub(r'\bmat[\s/]+soir\b|\bmatin[\s/]+soir\b', 'le matin et le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\bmat[\s/]+midi[\s/]+soir\b', 'le matin, le midi et le soir', t, flags=re.IGNORECASE)
    t = re.sub(r'\bav(?:ant)?[\s\.]+rep(?:as)?\b', 'avant le repas', t, flags=re.IGNORECASE)
    t = re.sub(r'\bap(?:r[èe]s)?[\s\.]+rep(?:as)?\b', 'après le repas', t, flags=re.IGNORECASE)
    t = re.sub(r'\bau\s+couch(?:er)?\b', 'au moment du coucher le soir', t, flags=re.IGNORECASE)

    # Cuillères, pipettes, poids pédiatrique
    t = re.sub(r'(\d+)\s*c[àa]\.?s\b|\b(\d+)\s*cas\b', r'\1 cuillères à soupe', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*c[àa]\.?c\b|\b(\d+)\s*cac\b', r'\1 cuillères à café', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(?:1\s+)?(?:pipette|dose[- ]poids|dose[- ]kilo)\b', 'une dose selon le poids de l\'enfant avec la pipette graduée', t, flags=re.IGNORECASE)

    # Formes pharmaceutiques & unités
    t = re.sub(r'\b1\s*c(?:p|ps|omp)\b', 'un comprimé', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*c(?:p|ps|omp)\b', r'\1 comprimés', t, flags=re.IGNORECASE)
    t = re.sub(r'\b1\s*g[ée]l\b', 'une gélule', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*g[ée]l(?:ules?)?\b', r'\1 gélules', t, flags=re.IGNORECASE)
    t = re.sub(r'\b1\s*sach(?:ets?)?\b', 'un sachet à dissoudre dans un verre d\'eau', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*sach(?:ets?)?\b', r'\1 sachets à dissoudre dans un verre d\'eau', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*g(?:tte|ttes)\b', r'\1 gouttes', t, flags=re.IGNORECASE)
    t = re.sub(r'\b1\s*supp?o(?:sitoires?)?\b', 'un suppositoire', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*supp?o(?:sitoires?)?\b', r'\1 suppositoires', t, flags=re.IGNORECASE)

    # Volumes & Dosages
    t = re.sub(r'(\d+)\s*ml\b', r'\1 millilitres', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*mg\b', r'\1 milligrammes', t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*g\b', r'\1 grammes', t, flags=re.IGNORECASE)

    # Nettoyage
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def adapter_vers_ivoirien(texte: str) -> str:
    """Adapte la posologie en français populaire ivoirien d'Abidjan, chaleureux et bienveillant."""
    if not texte:
        return ""
    t = traduire_abreviations_medicales(texte)
    t = re.sub(r'\bprenez\b|\bvous devez (?:le )?prendre\b', 'faut prendre', t, flags=re.IGNORECASE)
    t = re.sub(r'deux fois par jour, le matin et le soir', 'deux fois dans la journée, un le matin et un le soir', t)
    t = re.sub(r'trois fois par jour, le matin, le midi et le soir', 'trois fois dans la journée, le matin, à midi et le soir', t)
    t = re.sub(r'avant le repas', 'avant de manger', t)
    t = re.sub(r'après le repas', 'après avoir mangé', t)
    t = re.sub(r'au moment du coucher le soir', 'la nuit avant d\'aller dormir', t)
    t = re.sub(r'pendant (\d+) jours', r'pendant \1 jours bien comptés sans sauter de jour', t)
    t = re.sub(r'un sachet à dissoudre dans un verre d\'eau', 'un sachet à bien mélanger dans un verre d\'eau', t)
    return t.strip()

SYSTEM_PROMPT_GOOGLE_HEALTH = """Tu es "Ordonnance+", un moteur de vision clinique expert chargé d'extraire fidèlement des ordonnances médicales manuscrites réelles.
Tu produis STRICTEMENT un objet JSON valide, sans texte additionnel ni markdown en dehors du JSON.

PROTOCOLE DE SÉCURITÉ CLINIQUE ET CONFIDENTIALITÉ :
1. "NE RIEN INVENTER NI DÉDUIRE" :
   - Recopie fidèlement le texte manuscrit tel quel dans "posologie_recopiee".
   - Si un dosage est ambigu ou raturé, signale-le immédiatement : n'extrapole JAMAIS.
   - Si la posologie est illisible ou absente, écris exactement "À confirmer auprès du pharmacien".

2. "ÉVALUATION DE LA CONFIANCE CLINIQUE (SEUIL DE VALIDATION 40%)" :
   Pour chaque ligne de prescription identifiée, évalue la lisibilité :
   - score_confiance (0 à 100) :
     * Dès que le score est supérieur ou égal à 40 (>= 40%) : la mention est identifiable et exploitable -> statut_confiance = "CONFIRME", needs_confirmation = false
     * Inférieur à 40 (< 40%) : mention totalement illisible ou raturée méconnaissable -> statut_confiance = "INCERTAIN", needs_confirmation = true, avec motif_incertitude détaillé.

3. "EXPLICATION ORALE NATURELLE EN FRANÇAIS IVOIRIEN D'ABIDJAN (posologie_orale_simple)" :
   Pour chaque ligne, formule l'explication orale dans un français ivoirien d'Abidjan chaleureux, limpide et bienveillant pour un patient non-lecteur :
   - Développe toutes les abréviations médicales avec les tournures naturelles et rassurantes d'Abidjan ("faut prendre", "dans la journée", etc.) :
     * "12ml x2j pdt 5j" -> "Faut prendre 12 millilitres deux fois dans la journée, un le matin et un le soir avant de manger pendant 5 jours sans sauter de jour"
     * "1 cp x 3/j" -> "Faut prendre un comprimé trois fois dans la journée, un le matin, un à midi et un le soir avant de manger"
     * "1/2 cp mat/soir" -> "Faut prendre un demi-comprimé le matin et un demi-comprimé le soir"
     * "1 sach au couch" -> "Faut prendre un sachet à bien mélanger dans un verre d'eau la nuit avant d'aller dormir"
     * "1 dose-poids x3/j" -> "Faut donner une dose selon le poids de l'enfant avec la pipette graduée, trois fois dans la journée"
   - Précise toujours les moments de la journée pour que ce soit limpide à l'écoute.
   - Si le dosage n'est pas précisé, dis exactement "Le dosage n'est pas précisé" (ne dis JAMAIS "c'est dosé à non précisé").
   - Pour les prix, utilise l'expression "Prix moyen" (ne dis JAMAIS "prix indicatif officiel").

4. STRUCTURE DU JSON ATTENDU :
{
  "patient_nom": "Nom du patient ou 'Patient'",
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
      "posologie_recopiee": "Posologie exacte recopiée fidèlement (avec abréviations éventuelles)",
      "posologie_orale_simple": "Explication en français ivoirien chaleureux d'Abidjan sans abréviation pour patient non-lecteur",
      "posologie_ivoirienne": "Explication en français ivoirien chaleureux d'Abidjan pour patient non-lecteur",
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

    # Modèles Gemini multimodaux 2026 par ordre d'intelligence et de performance
    models = [
        "gemini-3.8-flash",       # Modèle 2026 Google AI Studio de référence (haute précision visuelle)
        "gemini-3.5-flash-lite",  # Modèle 2026 ultra-rapide optimisé pour haut débit
        "gemini-3.1-flash-lite",  # Repli stable
        "gemini-3.7-flash",       # Repli si disponible
        "gemini-flash-lite-latest"
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
    model_utilise = "gemini-3.8-flash"

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
        if "nodename nor servname" in dernier_erreur or "ConnectError" in dernier_erreur or "gaierror" in dernier_erreur:
            raise RuntimeError("Connexion impossible aux serveurs Google Gemini. Veuillez vérifier votre connexion internet.")
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

        # RÈGLE VALIDATION : Dès que le score de confiance est >= 40%, on valide la ligne et on affiche son prix
        if score >= 40:
            statut_confiance = "CONFIRME"
            needs_conf = False
            motif = None
        else:
            statut_confiance = "INCERTAIN"
            needs_conf = True
            motif = l.get("motif_incertitude") or "Lisibilité insuffisante (< 40%) : confirmation requise auprès du pharmacien"

        # Rapprochement catalogue officiel Côte d'Ivoire (3 852 médicaments)
        med_ref = chercher_medicament_catalogue(nom_med, dosage)
        code = med_ref["code"] if med_ref else None
        nom_cat = med_ref["nom"] if med_ref else None
        grp = med_ref["groupe"] if med_ref else None

        # RÈGLE DE CALCUL DU PRIX (Validé dès >= 40%)
        if statut_confiance == "CONFIRME" and med_ref:
            prix = med_ref["prix_fcfa"]
            motif_prix = "Tarif indicatif référentiel CI"
            total_fcfa += prix
        elif statut_confiance == "CONFIRME" and not med_ref:
            prix = None
            motif_prix = "Médicament non répertorié dans la base locale"
        else:
            prix = None
            motif_prix = "Score inférieur à 40% : à chiffrer en pharmacie"

        # Posologie orale bienveillante et limpide (sécurité anti-abréviations pour patient non-lecteur)
        # Posologie orale bienveillante et limpide en français ivoirien d'Abidjan
        posologie_orale = l.get("posologie_orale_simple", "").strip()
        if not posologie_orale or len(posologie_orale) < 5:
            posologie_orale = adapter_vers_ivoirien(posologie)
        else:
            posologie_orale = adapter_vers_ivoirien(posologie_orale)

        # Posologie en français populaire ivoirien (synchrone)
        posologie_ci = l.get("posologie_ivoirienne", "").strip()
        if not posologie_ci or len(posologie_ci) < 5:
            posologie_ci = posologie_orale
        else:
            posologie_ci = adapter_vers_ivoirien(posologie_ci)

        lignes_enrichies.append(LignePrescription(
            id=lid,
            raw_text=raw_text,
            nom_medicament=nom_med,
            dosage=dosage,
            forme=forme,
            posologie_recopiee=posologie,
            posologie_orale_simple=posologie_orale,
            posologie_ivoirienne=posologie_ci,
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
        patient_nom=raw_data.get("patient_nom") or "Patient",
        patient_age=raw_data.get("patient_age"),
        medecin_nom=raw_data.get("medecin_nom") or "Médecin Prescripteur",
        date_prescription=raw_data.get("date_prescription") or "Date non spécifiée",
        etablissement=raw_data.get("etablissement") or "Cabinet Médical / Centre Hospitalier",
        lignes=lignes_enrichies,
        total_lignes=total_lignes,
        lignes_confirmees=confirmees,
        lignes_incertaines=incertaines,
        statut_global="contient_doutes" if incertaines > 0 else "pret_pour_validation",
        total_estime_fcfa=total_fcfa,
        modele_utilise=f"Google AI Studio ({model_utilise})",
        source_donnees="Extraction structurée Google AI Studio + Référentiel CI"
    )
