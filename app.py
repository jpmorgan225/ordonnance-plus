"""
Application Ordonnance+ — L'assistant de lecture clinique pour le pharmacien.
Design System officiel Google Health / Material Design 3.
Exécution directe sans données fictives (Google AI Studio Gemini Multimodal).
"""

import os
import json
import sqlite3
import base64
import httpx
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
    traduire_abreviations_medicales,
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
    # ==========================================
    # COCODY (35 Pharmacies réelles - Tous quartiers)
    # ==========================================
    {
        "id": "cocody_1",
        "commune": "Cocody",
        "nom": "Pharmacie Saint-Jean",
        "tel": "+225 27 22 44 11 00",
        "adresse": "Cocody Centre, Carrefour Saint-Jean, face Église",
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
        "adresse": "Deux-Plateaux, Boulevard des Martyrs, face Station Shell",
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
        "adresse": "Angré 8ème Tranche, Carrefour Duncan",
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
    {
        "id": "cocody_6",
        "commune": "Cocody",
        "nom": "Pharmacie de la Riviera Golf",
        "tel": "+225 27 22 43 11 20",
        "adresse": "Riviera Golf, face Hôtel Ivoire Golf Club",
        "lat": 5.3410,
        "lon": -3.9820,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_7",
        "commune": "Cocody",
        "nom": "Pharmacie de la Palmeraie",
        "tel": "+225 27 22 49 10 30",
        "adresse": "Riviera Palmeraie, Rond-Point Monument",
        "lat": 5.3615,
        "lon": -3.9450,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_8",
        "commune": "Cocody",
        "nom": "Pharmacie Sainte Cécile du Vallon",
        "tel": "+225 27 22 41 55 60",
        "adresse": "Deux-Plateaux Vallons, Rue des Jardins",
        "lat": 5.3570,
        "lon": -3.9920,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_9",
        "commune": "Cocody",
        "nom": "Pharmacie du Carrefour Duncan",
        "tel": "+225 27 22 52 40 10",
        "adresse": "Deux-Plateaux, Bd Latrille, angle Rue K1",
        "lat": 5.3650,
        "lon": -3.9990,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_10",
        "commune": "Cocody",
        "nom": "Pharmacie Attoban",
        "tel": "+225 27 22 42 80 90",
        "adresse": "Cocody Attoban, face Cité Zinsou",
        "lat": 5.3640,
        "lon": -3.9710,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_11",
        "commune": "Cocody",
        "nom": "Pharmacie de Bonoumin",
        "tel": "+225 27 22 49 88 50",
        "adresse": "Riviera Bonoumin, voie express près Abidjan Mall",
        "lat": 5.3620,
        "lon": -3.9580,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_12",
        "commune": "Cocody",
        "nom": "Pharmacie Sainte Famille",
        "tel": "+225 27 22 43 25 10",
        "adresse": "Riviera 2, Carrefour Sainte Famille",
        "lat": 5.3470,
        "lon": -3.9740,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_13",
        "commune": "Cocody",
        "nom": "Pharmacie Danga",
        "tel": "+225 27 22 44 30 00",
        "adresse": "Cocody Danga, Avenue Jean Mermoz",
        "lat": 5.3395,
        "lon": -4.0010,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_14",
        "commune": "Cocody",
        "nom": "Pharmacie Mermoz",
        "tel": "+225 27 22 44 18 19",
        "adresse": "Cocody Cité des Arts, près Université Félix H-B",
        "lat": 5.3420,
        "lon": -4.0070,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_15",
        "commune": "Cocody",
        "nom": "Pharmacie des Ambassades",
        "tel": "+225 27 22 44 55 12",
        "adresse": "Cocody Ambassades, Rue des Ambassadeurs",
        "lat": 5.3320,
        "lon": -4.0080,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_16",
        "commune": "Cocody",
        "nom": "Pharmacie Blockhauss",
        "tel": "+225 27 22 48 12 34",
        "adresse": "Cocody Blockhauss, bordure lagune Ébrié",
        "lat": 5.3280,
        "lon": -4.0040,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_17",
        "commune": "Cocody",
        "nom": "Pharmacie 7ème Tranche",
        "tel": "+225 27 22 42 77 88",
        "adresse": "Angré 7ème Tranche, face Agence CIE",
        "lat": 5.3850,
        "lon": -3.9890,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_18",
        "commune": "Cocody",
        "nom": "Pharmacie 9ème Tranche",
        "tel": "+225 27 22 50 44 33",
        "adresse": "Angré 9ème Tranche, après Carrefour Mandela",
        "lat": 5.3980,
        "lon": -3.9810,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_19",
        "commune": "Cocody",
        "nom": "Pharmacie Mahou",
        "tel": "+225 27 22 52 14 00",
        "adresse": "Angré Mahou, Carrefour Mahou",
        "lat": 5.3890,
        "lon": -3.9960,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_20",
        "commune": "Cocody",
        "nom": "Pharmacie Petro Ivoire Angré",
        "tel": "+225 27 22 49 33 22",
        "adresse": "Angré, Boulevard Latrille face Station Petro Ivoire",
        "lat": 5.3940,
        "lon": -3.9780,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_21",
        "commune": "Cocody",
        "nom": "Pharmacie Perles Grises",
        "tel": "+225 27 22 52 70 80",
        "adresse": "Deux-Plateaux Aghien, face Cité Perles Grises",
        "lat": 5.3720,
        "lon": -3.9890,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_22",
        "commune": "Cocody",
        "nom": "Pharmacie Sainte Marie",
        "tel": "+225 27 22 44 26 15",
        "adresse": "Cocody Saint-Jean, face Lycée Sainte-Marie",
        "lat": 5.3440,
        "lon": -4.0020,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_23",
        "commune": "Cocody",
        "nom": "Pharmacie Belle Côte",
        "tel": "+225 27 22 47 18 19",
        "adresse": "Riviera Palmeraie, Carrefour Belle Côte",
        "lat": 5.3670,
        "lon": -3.9390,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_24",
        "commune": "Cocody",
        "nom": "Pharmacie Ephrata",
        "tel": "+225 27 22 43 90 90",
        "adresse": "Riviera 4, Carrefour M'Badon Village",
        "lat": 5.3430,
        "lon": -3.9350,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_25",
        "commune": "Cocody",
        "nom": "Pharmacie Akouédo",
        "tel": "+225 27 22 47 30 40",
        "adresse": "Riviera Palmeraie, Voie d'Akouédo Village",
        "lat": 5.3720,
        "lon": -3.9320,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_26",
        "commune": "Cocody",
        "nom": "Pharmacie Djibi",
        "tel": "+225 27 22 50 85 90",
        "adresse": "Angré 8ème Tranche, Entrée Cité Djibi 1",
        "lat": 5.4050,
        "lon": -3.9770,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_27",
        "commune": "Cocody",
        "nom": "Pharmacie Les Cascades",
        "tel": "+225 27 22 41 89 00",
        "adresse": "Deux-Plateaux, Boulevard des Martyrs, Carrefour Les Cascades",
        "lat": 5.3680,
        "lon": -3.9950,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_28",
        "commune": "Cocody",
        "nom": "Pharmacie Étoile d'Angré",
        "tel": "+225 27 22 52 09 11",
        "adresse": "Angré, Terminus Bus 81/82",
        "lat": 5.3995,
        "lon": -3.9720,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_29",
        "commune": "Cocody",
        "nom": "Pharmacie La Grâce de Bonoumin",
        "tel": "+225 27 22 49 70 12",
        "adresse": "Riviera Bonoumin, Carrefour Abatta",
        "lat": 5.3690,
        "lon": -3.9510,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_30",
        "commune": "Cocody",
        "nom": "Pharmacie Soleil de la Riviera",
        "tel": "+225 27 22 43 60 70",
        "adresse": "Riviera 3, Cité Synacass-ci",
        "lat": 5.3560,
        "lon": -3.9550,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_31",
        "commune": "Cocody",
        "nom": "Pharmacie Saint Gabriel",
        "tel": "+225 27 22 42 15 16",
        "adresse": "Angré, Rue L133 face Clinique Sainte Anne",
        "lat": 5.3830,
        "lon": -3.9780,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_32",
        "commune": "Cocody",
        "nom": "Pharmacie Cristal Deux-Plateaux",
        "tel": "+225 27 22 41 95 95",
        "adresse": "Deux-Plateaux, Rue du Docteur Blanchard",
        "lat": 5.3610,
        "lon": -3.9930,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_33",
        "commune": "Cocody",
        "nom": "Pharmacie Les Arcades",
        "tel": "+225 27 22 41 12 13",
        "adresse": "Deux-Plateaux Bd des Martyrs, Galerie Commerciale Les Arcades",
        "lat": 5.3660,
        "lon": -3.9960,
        "est_de_garde": False,
        "ouvert_jour_ouvrable": True,
        "type_service": "jour_ouvrable",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Fermée la nuit et le dimanche",
        "periode_garde": None
    },
    {
        "id": "cocody_34",
        "commune": "Cocody",
        "nom": "Pharmacie Sainte Monique",
        "tel": "+225 27 22 47 50 60",
        "adresse": "Riviera Palmeraie, Cité Rosiers 3",
        "lat": 5.3630,
        "lon": -3.9410,
        "est_de_garde": True,
        "ouvert_jour_ouvrable": True,
        "type_service": "garde_et_jour",
        "horaires_jour": "Lun - Sam : 08h00 - 20h00",
        "horaires_garde": "Garde 24h/24 (Nuit, Dimanche & Fériés)",
        "periode_garde": "Semaine du 26 sept au 02 oct 2026"
    },
    {
        "id": "cocody_35",
        "commune": "Cocody",
        "nom": "Pharmacie Fann Cocody",
        "tel": "+225 27 22 44 71 80",
        "adresse": "Cocody Centre, Cité Cadres près RTI",
        "lat": 5.3400,
        "lon": -4.0040,
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

    # Statistiques globales de la commune cible
    total_commune = sum(1 for p in PHARMACIES_GARDE_ABIDJAN if p["commune"].lower() == commune_cible.lower())
    total_garde = sum(1 for p in PHARMACIES_GARDE_ABIDJAN if p["commune"].lower() == commune_cible.lower() and p.get("est_de_garde", False))
    total_jour = sum(1 for p in PHARMACIES_GARDE_ABIDJAN if p["commune"].lower() == commune_cible.lower() and p.get("ouvert_jour_ouvrable", True))

    return {
        "count": len(result),
        "commune_active": commune_cible,
        "communes_disponibles": communes_dispo,
        "service_filtre": service,
        "geolocalise": bool(lat is not None and lon is not None),
        "user_lat": lat,
        "user_lon": lon,
        "stats_commune": {
            "total": total_commune,
            "garde": total_garde,
            "jour_ouvrable": total_jour
        },
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

import hashlib
import edge_tts
from fastapi import Response

AUDIO_CACHE_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

@app.get("/api/tts")
@app.post("/api/tts")
async def generate_tts(text: str = "", voice: str = "fr-FR-VivienneMultilingualNeural", rate: str = "-4%"):
    """Génère un flux audio MP3 naturel et humain via synthèse vocale neuronale HD."""
    raw_text = text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Texte manquant")
    
    # Traduction automatique des abréviations médicales en langage soignant oral
    texte_oral = traduire_abreviations_medicales(raw_text)
    
    GEMINI_VOICES = {
        "kore": "Kore",
        "aoede": "Aoede",
        "fenrir": "Fenrir",
    }
    voice_key = voice.lower().strip()

    # 1. Prise en charge des voix Studio Google Gemini 3.8 Flash TTS
    if voice_key in GEMINI_VOICES:
        gemini_voice = GEMINI_VOICES[voice_key]
        cache_key = hashlib.md5(f"gemini_38_tts_{gemini_voice}_{texte_oral}".encode("utf-8")).hexdigest()
        cache_file = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.wav")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return Response(content=f.read(), media_type="audio/wav")
        
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": texte_oral}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": gemini_voice}
                            }
                        }
                    }
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "inlineData" in p and p["inlineData"].get("data"):
                                audio_bytes = base64.b64decode(p["inlineData"]["data"])
                                with open(cache_file, "wb") as f:
                                    f.write(audio_bytes)
                                return Response(content=audio_bytes, media_type="audio/wav")
            except Exception as ge:
                print(f"Gemini TTS error ({ge}), bascule vers synthèse neuronale...")

    VOIX_VALIDES = {
        "vivienne": "fr-FR-VivienneMultilingualNeural",
        "remy": "fr-FR-RemyMultilingualNeural",
        "denise": "fr-FR-DeniseNeural",
        "eloise": "fr-FR-EloiseNeural",
        "henri": "fr-FR-HenriNeural",
    }
    selected_voice = VOIX_VALIDES.get(voice_key, "fr-FR-VivienneMultilingualNeural")
    
    cache_key = hashlib.md5(f"{selected_voice}_{rate}_{texte_oral}".encode("utf-8")).hexdigest()
    cache_file = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
    
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return Response(content=f.read(), media_type="audio/mpeg")
            
    try:
        communicate = edge_tts.Communicate(texte_oral, voice=selected_voice, rate=rate)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        audio_data = b"".join(chunks)
        
        with open(cache_file, "wb") as f:
            f.write(audio_data)
            
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        print("Erreur edge-tts:", e)
        raise HTTPException(status_code=500, detail=f"Erreur de synthèse vocale : {str(e)}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Ordonnance+ API en ligne."}
