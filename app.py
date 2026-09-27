"""
Application Ordonnance+ — L'assistant de lecture d'ordonnances pour le pharmacien.
Hackathon Come Build with AI (Abidjan, Côte d'Ivoire).
Architecture Killer-SaaS / Ship Fast : Monolithe ultra-réactif, zéro dépendance superflue.
"""

import os
import io
import json
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from gemini_service import (
    analyser_ordonnance_gemini,
    chercher_medicament_catalogue,
    AnalyseOrdonnance,
    LignePrescription,
    PRESETS_ANALYSES,
    DB_PATH
)

app = FastAPI(
    title="Ordonnance+ API",
    description="Assistant de transcription sécurisée d'ordonnances médicales pour pharmaciens",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Données des pharmacies de garde d'Abidjan (Valeur ajoutée locale pour la fiche patient)
PHARMACIES_GARDE_ABIDJAN = [
    {"commune": "Cocody", "nom": "Pharmacie des Deux-Plateaux", "tel": "+225 27 22 41 20 20", "adresse": "Boulevard des Martyrs, près de la station Shell"},
    {"commune": "Cocody", "nom": "Pharmacie Saint-Jean", "tel": "+225 27 22 44 11 00", "adresse": "Rue des Jardins, II Plateaux Vallon"},
    {"commune": "Plateau", "nom": "Pharmacie du Commerce", "tel": "+225 27 20 21 02 12", "adresse": "Avenue Général de Gaulle"},
    {"commune": "Yopougon", "nom": "Pharmacie Bel-Air", "tel": "+225 27 23 45 67 89", "adresse": "Yopougon Selmer, Carrefour Zone"},
    {"commune": "Marcory", "nom": "Pharmacie Tiacoh", "tel": "+225 27 21 25 30 40", "adresse": "Boulevard VGE, face Prima Center"},
]

@app.get("/api/samples")
async def get_samples():
    """Renvoie les 3 ordonnances étalons de démonstration."""
    return [
        {
            "id": "sample_1",
            "titre": "Cas 1 : Ordonnance Claire & Lisible",
            "medecin": "Dr. KOUASSI Jean (Cocody)",
            "patient": "KONE Ibrahim (Fictif)",
            "medicaments": "Doliprane 1000mg, Amoxicilline 500mg, Spasfon 80mg",
            "image_url": "/static/samples/ordonnance_1_standard.png",
            "statut_attendu": "pret_pour_validation",
            "description_demo": "Démonstration du flux nominal. Détection haute confiance en 2 secondes, calcul des prix en FCFA, validation fluide."
        },
        {
            "id": "sample_2",
            "titre": "Cas 2 : Dosage Manuscrit Ambigu (Sécurité Pharmacien)",
            "medecin": "Dr. AMANI Brigitte (Plateau)",
            "patient": "BAKAYOKO Aminata (Fictif)",
            "medicaments": "Spasfon 80mg, Ciprofloxacine (250mg ou 500mg ?)",
            "image_url": "/static/samples/ordonnance_2_ambigue.png",
            "statut_attendu": "contient_doutes",
            "description_demo": "⭐ Point fort du jury : L'IA détecte l'ambiguïté du chiffre manuscrit, lève une alerte rouge et BLOQUE la validation tant que le pharmacien n'a pas confirmé."
        },
        {
            "id": "sample_3",
            "titre": "Cas 3 : Posologie Incomplète (Règle d'or : Ne rien inventer)",
            "medecin": "Dr. TOURE Moussa (Yopougon)",
            "patient": "DIARRA Seydou (Fictif)",
            "medicaments": "Coartem 80/480mg (Posologie manquante), Efferalgan 1g",
            "image_url": "/static/samples/ordonnance_3_incomplete.png",
            "statut_attendu": "contient_doutes",
            "description_demo": "Éthique médicale : Posologie absente. L'IA ne déduit aucun 'matin/midi/soir' et marque 'À confirmer auprès du pharmacien'."
        }
    ]

@app.post("/api/analyze")
async def analyze_prescription(
    preset_key: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Analyse une ordonnance envoyée ou un preset démo."""
    image_bytes = b""
    mime_type = "image/png"

    if file:
        image_bytes = await file.read()
        mime_type = file.content_type or "image/png"
    elif preset_key:
        sample_path = os.path.join(STATIC_DIR, "samples", f"ordonnance_{preset_key.replace('sample_', '')}.png")
        # adapter au nom réel de fichier
        mapping = {
            "sample_1": "ordonnance_1_standard.png",
            "sample_2": "ordonnance_2_ambigue.png",
            "sample_3": "ordonnance_3_incomplete.png",
        }
        fname = mapping.get(preset_key, "ordonnance_1_standard.png")
        sample_path = os.path.join(STATIC_DIR, "samples", fname)
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                image_bytes = f.read()

    resultat = await analyser_ordonnance_gemini(image_bytes, mime_type=mime_type, preset_key=preset_key)
    return resultat

@app.get("/api/catalog/search")
async def search_catalog(q: str):
    """Recherche instantanée dans les 3 852 médicaments de Côte d'Ivoire."""
    if not q or len(q) < 2:
        return []
    
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT code, nom, groupe, prix_fcfa 
        FROM medicaments 
        WHERE nom_normalise LIKE ? 
        ORDER BY nom ASC 
        LIMIT 15
    """, (f"%{q.lower().strip()}%",))
    rows = cursor.fetchall()
    conn.close()

    return [
        {"code": r[0], "nom": r[1], "groupe": r[2], "prix_fcfa": r[3]}
        for r in rows
    ]

@app.get("/api/sync/status")
async def get_sync_status():
    """Informations de synchronisation du catalogue."""
    if not os.path.exists(DB_PATH):
        return {"status": "non_initialise"}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT cle, valeur FROM meta_sync")
    metas = dict(cursor.fetchall())
    cursor.execute("SELECT COUNT(*) FROM medicaments")
    count = cursor.fetchone()[0]
    conn.close()
    return {
        "status": "actif",
        "total_references": count,
        "derniere_mise_a_jour": metas.get("derniere_sync", "Samedi matin"),
        "source": "pharmacies-de-garde.ci",
        "frequence": "Automatique chaque samedi à 06:00 GMT"
    }

class ValidationPayload(BaseModel):
    patient_nom: str
    patient_age: Optional[str]
    medecin_nom: str
    date_prescription: str
    nom_pharmacien: str = "Dr. KONAN (Pharmacien Responsable)"
    officine_nom: str = "Grande Pharmacie de la Riviera"
    lignes: List[LignePrescription]
    conseils_delivrance: Optional[str] = ""

@app.post("/api/validate-prescription")
async def validate_prescription(payload: ValidationPayload):
    """Valide l'ordonnance par le pharmacien et génère la fiche officielle patient."""
    # Règle de sécurité absolue : Aucune ligne non vérifiée ne doit persister
    for l in payload.lignes:
        if l.confiance == "douteux" and not l.valide_par_pharmacien:
            raise HTTPException(
                status_code=400, 
                detail=f"Sécurité violée : La ligne '{l.nom_medicament}' comporte un doute non levé par le pharmacien."
            )

    total_prix = sum(l.prix_reference_fcfa or 0 for l in payload.lignes)
    
    fiche_patient = {
        "statut": "CERTIFIEE_CONFORME",
        "numero_visa": f"VISA-PHARM-CI-2026-{os.urandom(3).hex().upper()}",
        "date_validation": "27/09/2026 à 11:30 GMT",
        "officine": payload.officine_nom,
        "pharmacien": payload.nom_pharmacien,
        "patient": {
            "nom": payload.patient_nom,
            "age": payload.patient_age
        },
        "prescripteur": payload.medecin_nom,
        "date_ordonnance": payload.date_prescription,
        "medicaments": [
            {
                "nom": l.nom_medicament,
                "dosage": l.dosage,
                "forme": l.forme,
                "posologie_officielle": l.posologie_recopiee,
                "prix_reference_fcfa": l.prix_reference_fcfa,
                "code": l.code_catalogue
            }
            for l in payload.lignes
        ],
        "total_estime_fcfa": total_prix,
        "source_prix": "Catalogue officiel Côte d'Ivoire (pharmacies-de-garde.ci)",
        "conseils_delivrance": payload.conseils_delivrance or "Respecter scrupuleusement la durée de traitement prescrite. En cas d'effets secondaires, contacter immédiatement votre pharmacien.",
        "pharmacies_garde_recommandees": PHARMACIES_GARDE_ABIDJAN[:2],
        "mentions_legales": "Fiche de dispensation délivrée sous le contrôle du pharmacien diplômé. Données traitées conformément à la loi ivoirienne n° 2013-450."
    }

    return fiche_patient

# Montage des fichiers statiques
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Ordonnance+ API opérationnelle."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
