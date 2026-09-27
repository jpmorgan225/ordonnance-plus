"""
Script de synchronisation hebdomadaire du catalogue des médicaments de Côte d'Ivoire.
Source officielle : https://www.pharmacies-de-garde.ci/prix-des-medicaments-en-pharmacie-en-cote-divoire/
Exécution automatique recommandée : Chaque samedi matin (Cron / Pipeline)
"""

import os
import sys
import sqlite3
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "medicaments.db")
JSON_PATH = os.path.join(DATA_DIR, "medicaments_ci.json")
URL_CATALOGUE = "https://www.pharmacies-de-garde.ci/prix-des-medicaments-en-pharmacie-en-cote-divoire/"

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            nom_normalise TEXT NOT NULL,
            groupe TEXT,
            prix_fcfa INTEGER NOT NULL,
            date_maj TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nom_norm ON medicaments(nom_normalise)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_code ON medicaments(code)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta_sync (
            cle TEXT PRIMARY KEY,
            valeur TEXT
        )
    """)
    conn.commit()

def normaliser(texte: str) -> str:
    if not texte:
        return ""
    t = texte.lower()
    # Remplacer accents
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c'
    }
    for k, v in replacements.items():
        t = t.replace(k, v)
    # Supprimer ponctuations superflues
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return ' '.join(t.split())

def parse_html(html_content: str):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'tablepress-1'})
    if not table:
        print("[WARN] Table tablepress-1 non trouvée, recherche globale de table...")
        table = soup.find('table')
    
    meds = []
    if not table:
        return meds
    
    rows = table.find_all('tr')
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for r in rows:
        cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
        if len(cols) >= 5 and cols[0] != 'N°':
            code = cols[1]
            nom = cols[2]
            groupe = cols[3]
            digits = re.sub(r'[^\d]', '', cols[4])
            try:
                prix = int(digits) if digits else 0
            except ValueError:
                continue
            
            if nom and prix > 0:
                meds.append({
                    "code": code,
                    "nom": nom,
                    "nom_normalise": normaliser(nom),
                    "groupe": groupe,
                    "prix_fcfa": prix,
                    "date_maj": now_iso
                })
    return meds

def synchroniser(source_file: str = None):
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    html_content = None
    if source_file and os.path.exists(source_file):
        print(f"[*] Lecture depuis le fichier local: {source_file}")
        with open(source_file, "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        print(f"[*] Téléchargement du catalogue depuis {URL_CATALOGUE}...")
        try:
            resp = requests.get(URL_CATALOGUE, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            if resp.status_code == 200:
                html_content = resp.text
        except Exception as e:
            print(f"[!] Erreur réseau lors du scraping: {e}")

    if not html_content:
        print("[!] Aucun contenu HTML disponible.")
        return 0

    meds = parse_html(html_content)
    print(f"[*] {len(meds)} médicaments extraits.")

    cursor = conn.cursor()
    for m in meds:
        cursor.execute("""
            INSERT INTO medicaments (code, nom, nom_normalise, groupe, prix_fcfa, date_maj)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                nom=excluded.nom,
                nom_normalise=excluded.nom_normalise,
                groupe=excluded.groupe,
                prix_fcfa=excluded.prix_fcfa,
                date_maj=excluded.date_maj
        """, (m["code"], m["nom"], m["nom_normalise"], m["groupe"], m["prix_fcfa"], m["date_maj"]))

    sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO meta_sync (cle, valeur) VALUES ('derniere_sync', ?)", (sync_time,))
    cursor.execute("INSERT OR REPLACE INTO meta_sync (cle, valeur) VALUES ('total_meds', ?)", (str(len(meds)),))
    cursor.execute("INSERT OR REPLACE INTO meta_sync (cle, valeur) VALUES ('source', 'pharmacies-de-garde.ci')",)
    conn.commit()

    # Export JSON léger pour frontend / consultation
    with open(JSON_PATH, "w", encoding="utf-8") as jf:
        json.dump({
            "derniere_sync": sync_time,
            "source": "pharmacies-de-garde.ci",
            "frequence": "Hebdomadaire (Chaque samedi matin à 06:00 GMT)",
            "total": len(meds),
            "medicaments": meds
        }, jf, ensure_ascii=False, indent=2)

    print(f"[OK] Base de données mise à jour avec succès : {DB_PATH} ({len(meds)} références)")
    conn.close()
    return len(meds)

if __name__ == "__main__":
    local_source = sys.argv[1] if len(sys.argv) > 1 else None
    synchroniser(local_source)
