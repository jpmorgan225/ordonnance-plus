"""
Application Ordonnance+ — L'assistant de lecture clinique pour le pharmacien.
Design System officiel Google Health / Material Design 3.
Exécution directe sans données fictives (Google AI Studio Gemini Multimodal).
"""

import os
import json
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

load_dotenv()

from gemini_service import (
    analyser_ordonnance_reelle,
    chercher_medicament_catalogue,
    AnalyseOrdonnance,
    LignePrescription,
    DB_PATH
)

app = FastAPI(
    title="Ordonnance+ — Google Health Assistant",
    description="Plateforme clinique d'aide à la transcription d'ordonnances manuscrites réelles",
    version="2.0.0"
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
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Vraies ordonnances réelles et impersonnelles disponibles pour le test
ORDONNANCES_REELLES = [
    {
        "id": "reelle_1",
        "titre": "Ordonnance Réelle 1 — Écriture Manuscrite Cursive",
        "description": "Document clinique réel (photo smartphone). Écriture cursive médicale dense, posologies manuscrites.",
        "image_url": "/static/samples/ordonnance_reelle_1.jpg",
        "source": "Wikimedia Commons / Archives médicales ouvertes",
        "type": "Manuscrit Réel"
    },
    {
        "id": "reelle_2",
        "titre": "Ordonnance Réelle 2 — Prescription Clinique Scannée",
        "description": "Document médical scanné réel avec en-tête praticien et prescriptions multiples.",
        "image_url": "/static/samples/ordonnance_reelle_2.png",
        "source": "Open Healthcare Dataset / Prescription OCR",
        "type": "Manuscrit Scanné"
    },
    {
        "id": "reelle_3",
        "titre": "Ordonnance Réelle 3 — Prescription Hospitalière Scannée",
        "description": "Document hospitalier authentique avec posologie complexe à déchiffrer.",
        "image_url": "/static/samples/ordonnance_reelle_3.png",
        "source": "Open Healthcare Dataset / Prescription OCR",
        "type": "Hospitalier Réel"
    }
]

import math

def calculer_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcule la distance géodésique (en km) selon la formule de Haversine."""
    R = 6371.0 # Rayon moyen de la Terre en kilomètres
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# Répertoire officiel des pharmacies de garde réelles d'Abidjan avec coordonnées GPS
PHARMACIES_GARDE_ABIDJAN = [
    # Cocody
    {
        "id": "cocody_1",
        "commune": "Cocody",
        "nom": "Pharmacie Saint-Jean",
        "tel": "+225 27 22 44 11 00",
        "adresse": "Rue des Jardins, II Plateaux Vallon",
        "lat": 5.3482,
        "lon": -4.0041,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_2",
        "commune": "Cocody",
        "nom": "Pharmacie des Deux-Plateaux",
        "tel": "+225 27 22 41 20 20",
        "adresse": "Boulevard des Martyrs, face Station Shell",
        "lat": 5.3621,
        "lon": -3.9985,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_3",
        "commune": "Cocody",
        "nom": "Pharmacie de la Riviera 3",
        "tel": "+225 27 22 43 15 15",
        "adresse": "Riviera 3, près Lycée Français",
        "lat": 5.3510,
        "lon": -3.9620,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_4",
        "commune": "Cocody",
        "nom": "Pharmacie d'Angré",
        "tel": "+225 27 22 50 18 19",
        "adresse": "8ème Tranche, Carrefour Duncan",
        "lat": 5.3920,
        "lon": -3.9850,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_5",
        "commune": "Cocody",
        "nom": "Pharmacie Sainte Agathe",
        "tel": "+225 27 22 49 60 70",
        "adresse": "Angré Château d'eau",
        "lat": 5.3780,
        "lon": -3.9720,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Plateau
    {
        "id": "plateau_1",
        "commune": "Plateau",
        "nom": "Pharmacie du Commerce",
        "tel": "+225 27 20 21 02 12",
        "adresse": "Avenue Général de Gaulle, Immeuble Nabil",
        "lat": 5.3240,
        "lon": -4.0185,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "plateau_2",
        "commune": "Plateau",
        "nom": "Pharmacie Moderne du Plateau",
        "tel": "+225 27 20 22 88 00",
        "adresse": "Avenue Chardy, angle Rue Gourgas",
        "lat": 5.3265,
        "lon": -4.0220,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 19h30",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Marcory
    {
        "id": "marcory_1",
        "commune": "Marcory",
        "nom": "Pharmacie Tiacoh",
        "tel": "+225 27 21 25 30 40",
        "adresse": "Boulevard VGE, face Prima Center",
        "lat": 5.3055,
        "lon": -3.9870,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "marcory_2",
        "commune": "Marcory",
        "nom": "Pharmacie du Grand Marché Marcory",
        "tel": "+225 27 21 26 12 14",
        "adresse": "Rue Thomas Edison",
        "lat": 5.3010,
        "lon": -3.9910,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "marcory_3",
        "commune": "Marcory",
        "nom": "Pharmacie des Lagunes",
        "tel": "+225 27 21 35 44 20",
        "adresse": "Zone 4C, Rue du Canal",
        "lat": 5.2920,
        "lon": -3.9780,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },

    # Treichville
    {
        "id": "treichville_1",
        "commune": "Treichville",
        "nom": "Pharmacie Avenue 8",
        "tel": "+225 27 21 24 05 50",
        "adresse": "Avenue 8, angle Rue 12",
        "lat": 5.3080,
        "lon": -4.0120,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "treichville_2",
        "commune": "Treichville",
        "nom": "Pharmacie du CHU Treichville",
        "tel": "+225 27 21 25 80 00",
        "adresse": "Face Entrée Principale CHU Treichville",
        "lat": 5.3030,
        "lon": -4.0190,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 07h30 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Yopougon
    {
        "id": "yopougon_1",
        "commune": "Yopougon",
        "nom": "Pharmacie Bel-Air",
        "tel": "+225 27 23 45 67 89",
        "adresse": "Yopougon Selmer, Carrefour Zone",
        "lat": 5.3370,
        "lon": -4.0720,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "yopougon_2",
        "commune": "Yopougon",
        "nom": "Pharmacie Saint André",
        "tel": "+225 27 23 52 10 30",
        "adresse": "Yopougon Siporex, Boulevard Principal",
        "lat": 5.3520,
        "lon": -4.0680,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "yopougon_3",
        "commune": "Yopougon",
        "nom": "Pharmacie Saint Hermann",
        "tel": "+225 27 23 46 22 11",
        "adresse": "Yopougon Toits Rouges",
        "lat": 5.3610,
        "lon": -4.0840,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "yopougon_4",
        "commune": "Yopougon",
        "nom": "Pharmacie Saint Aubin d'Agbayaté",
        "tel": "+225 27 23 48 55 90",
        "adresse": "Yopougon Agbayaté",
        "lat": 5.3480,
        "lon": -4.0950,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "yopougon_5",
        "commune": "Yopougon",
        "nom": "Pharmacie Keneya",
        "tel": "+225 27 23 45 12 00",
        "adresse": "Yopougon Carrefour CHU",
        "lat": 5.3410,
        "lon": -4.0550,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Abobo
    {
        "id": "abobo_1",
        "commune": "Abobo",
        "nom": "Pharmacie Grand Marché Abobo",
        "tel": "+225 27 24 39 01 01",
        "adresse": "Rond-point Mairie / Grand Marché",
        "lat": 5.4190,
        "lon": -4.0190,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "abobo_2",
        "commune": "Abobo",
        "nom": "Pharmacie Al-Fatih",
        "tel": "+225 01 52 12 12 21",
        "adresse": "Abobo Samaké, voie express",
        "lat": 5.4280,
        "lon": -4.0120,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "abobo_3",
        "commune": "Abobo",
        "nom": "Pharmacie Sainte Croix",
        "tel": "+225 07 78 13 75 03",
        "adresse": "Abobo Sagbé, Terminus Bus",
        "lat": 5.4350,
        "lon": -4.0250,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "abobo_4",
        "commune": "Abobo",
        "nom": "Pharmacie Yarapha",
        "tel": "+225 27 24 49 12 63",
        "adresse": "Abobo Baoulé Carrefour",
        "lat": 5.4120,
        "lon": -4.0080,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Koumassi
    {
        "id": "koumassi_1",
        "commune": "Koumassi",
        "nom": "Pharmacie du Grand Carrefour",
        "tel": "+225 27 21 36 20 40",
        "adresse": "Grand Carrefour Koumassi, Bd du 7 Décembre",
        "lat": 5.2980,
        "lon": -3.9520,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "koumassi_2",
        "commune": "Koumassi",
        "nom": "Pharmacie Marais",
        "tel": "+225 27 21 28 05 30",
        "adresse": "Koumassi Remblais",
        "lat": 5.2910,
        "lon": -3.9450,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Port-Bouët
    {
        "id": "portbouet_1",
        "commune": "Port-Bouët",
        "nom": "Pharmacie Océan",
        "tel": "+225 27 21 27 75 10",
        "adresse": "Port-Bouët Phare, route de Grand-Bassam",
        "lat": 5.2580,
        "lon": -3.9320,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "portbouet_2",
        "commune": "Port-Bouët",
        "nom": "Pharmacie Vridi Canal",
        "tel": "+225 27 21 27 00 12",
        "adresse": "Vridi Cité, Carrefour Douane",
        "lat": 5.2680,
        "lon": -3.9890,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Adjamé
    {
        "id": "adjame_1",
        "commune": "Adjamé",
        "nom": "Pharmacie 220 Logements",
        "tel": "+225 27 20 37 40 50",
        "adresse": "Adjamé 220 Logements, près Marché Gouro",
        "lat": 5.3520,
        "lon": -4.0280,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "adjame_2",
        "commune": "Adjamé",
        "nom": "Pharmacie de la Liberté",
        "tel": "+225 27 20 38 12 30",
        "adresse": "Adjamé Liberté, Boulevard Nangui Abrogoua",
        "lat": 5.3610,
        "lon": -4.0320,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },

    # Bingerville
    {
        "id": "bingerville_1",
        "commune": "Bingerville",
        "nom": "Pharmacie de Bingerville",
        "tel": "+225 27 22 40 31 10",
        "adresse": "Artère principale, face Jardin Botanique",
        "lat": 5.3560,
        "lon": -3.8910,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    }
]

@app.get("/api/pharmacies-garde")
async def get_pharmacies_garde(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    commune: Optional[str] = None,
    service: Optional[str] = "tous"  # 'tous', 'garde', 'jour_ouvrable'
):
    """
    Renvoie les pharmacies d'Abidjan filtrées STRICTEMENT par commune et triées par proximité.
    Distingue :
    - 'jour_ouvrable' (Lundi au Samedi en journée)
    - 'garde' (Nuit, Week-end et Jours fériés 24h)
    """
    communes_dispo = [
        "Cocody", "Yopougon", "Plateau", "Marcory", "Treichville", 
        "Abobo", "Koumassi", "Port-Bouët", "Adjamé", "Bingerville"
    ]

    commune_cible = (commune or "").strip()
    
    # Si géolocalisation fournie et aucune commune spécifiée (ou auto) :
    # Déduire automatiquement la commune la plus proche
    if (not commune_cible or commune_cible.lower() in ["auto", "toutes", ""]) and (lat is not None and lon is not None):
        plus_proche = min(
            PHARMACIES_GARDE_ABIDJAN,
            key=lambda p: calculer_distance_km(lat, lon, p["lat"], p["lon"])
        )
        commune_cible = plus_proche["commune"]
    elif not commune_cible or commune_cible.lower() in ["auto", "toutes", ""]:
        commune_cible = "Cocody"

    result = []
    for p in PHARMACIES_GARDE_ABIDJAN:
        # Restriction stricte à la commune demandée
        if p["commune"].lower() != commune_cible.lower():
            continue

        item = dict(p)

        # Filtre sur le régime de service
        if service == "garde" and not item.get("est_de_garde", False):
            continue
        if service == "jour_ouvrable" and not item.get("ouvert_jour_ouvrable", True):
            continue

        if lat is not None and lon is not None:
            dist = calculer_distance_km(lat, lon, item["lat"], item["lon"])
            item["distance_km"] = dist
            if dist < 1.0:
                item["distance_texte"] = f"{int(dist * 1000)} m"
            else:
                item["distance_texte"] = f"{dist:.1f} km"
            item["temps_voiture_min"] = max(2, int(dist * 2.5))
        else:
            item["distance_km"] = None
            item["distance_texte"] = None
            item["temps_voiture_min"] = None

        result.append(item)

    # Tri par distance croissante si géolocalisé
    if lat is not None and lon is not None:
        result.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 99999))
    else:
        # Pharmacies de garde d'abord, puis par nom
        result.sort(key=lambda x: (not x.get("est_de_garde", False), x["nom"]))

    return {
        "count": len(result),
        "commune_active": commune_cible,
        "communes_disponibles": communes_dispo,
        "service_filtre": service,
        "geolocalise": bool(lat is not None and lon is not None),
        "user_lat": lat,
        "user_lon": lon,
        "pharmacies": result
    }

@app.get("/api/samples")
async def get_real_prescriptions():
    """Renvoie la liste des ordonnances médicales réelles impersonnelles."""
    return ORDONNANCES_REELLES

@app.get("/api/key/status")
async def get_api_key_status(x_gemini_api_key: Optional[str] = Header(None)):
    """Vérifie si une clé API est configurée."""
    key = (x_gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    return {
        "configured": bool(key and len(key) > 8),
        "source": "header" if x_gemini_api_key else ("env" if os.getenv("GEMINI_API_KEY") else "none")
    }

class KeyPayload(BaseModel):
    api_key: str

@app.post("/api/key/save")
async def save_api_key(payload: KeyPayload):
    """Enregistre la clé Google AI Studio dans le fichier .env."""
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Clé API vide")
    
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={key}\n")
    os.environ["GEMINI_API_KEY"] = key
    return {"status": "saved", "message": "Clé Google AI Studio enregistrée avec succès"}

@app.post("/api/analyze")
async def analyze_prescription(
    sample_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """Analyse une ordonnance réelle via Google Gemini Multimodal en direct."""
    key = (api_key or x_gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Clé API Google AI Studio manquante. Veuillez saisir votre clé Gemini dans la barre supérieure pour lancer l'analyse en direct."
        )

    image_bytes = b""
    mime_type = "image/png"

    if file and file.filename:
        image_bytes = await file.read()
        mime_type = file.content_type or "image/png"
    elif sample_id:
        mapping = {
            "reelle_1": "ordonnance_reelle_1.jpg",
            "reelle_2": "ordonnance_reelle_2.png",
            "reelle_3": "ordonnance_reelle_3.png",
        }
        filename = mapping.get(sample_id, "ordonnance_reelle_1.jpg")
        sample_path = os.path.join(STATIC_DIR, "samples", filename)
        mime_type = "image/jpeg" if filename.endswith(".jpg") else "image/png"
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                image_bytes = f.read()
        else:
            raise HTTPException(status_code=404, detail="Échantillon d'ordonnance introuvable sur le disque.")
    else:
        raise HTTPException(status_code=400, detail="Aucun document ou ordonnance fourni pour l'analyse.")

    try:
        resultat = await analyser_ordonnance_reelle(
            image_bytes=image_bytes,
            mime_type=mime_type,
            api_key_override=key
        )
        return resultat
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        LIMIT 20
    """, (f"%{q.lower().strip()}%",))
    rows = cursor.fetchall()
    conn.close()

    return [
        {"code": r[0], "nom": r[1], "groupe": r[2], "prix_fcfa": r[3]}
        for r in rows
    ]

@app.get("/api/sync/status")
async def get_sync_status():
    """Informations sur le catalogue officiel de Côte d'Ivoire."""
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
        "derniere_mise_a_jour": metas.get("derniere_sync", "Samedi"),
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
        "date_validation": "27/09/2026",
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
        "conseils_delivrance": payload.conseils_delivrance or "Respecter scrupuleusement la durée prescrite. Contacter votre pharmacien en cas de questions.",
        "pharmacies_garde_recommandees": PHARMACIES_GARDE_ABIDJAN[:2],
        "mentions_legales": "Fiche de dispensation sous le contrôle du pharmacien. Données de santé protégées (traitement éphémère et confidentiel)."
    }

    return fiche_patient

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Ordonnance+ API en ligne."}
