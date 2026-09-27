"""
Générateur d'ordonnances médicales fictives pour la démonstration Ordonnance+.
Conforme aux recommandations ARTCI / Loi 2013-450 (données strictement fictives).
"""

import os
from PIL import Image, ImageDraw, ImageFont

STATIC_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "static", "samples")
os.makedirs(STATIC_SAMPLES_DIR, exist_ok=True)

def draw_cadre_ordonnance(draw, width, height):
    # Fond blanc légèrement texturé/ivoire d'ordonnance
    draw.rectangle([(0, 0), (width, height)], fill=(253, 253, 250))
    # Bordure subtile
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(190, 200, 210), width=2)
    # Ligne d'en-tête
    draw.line([(30, 160), (width - 30, 160)], fill=(0, 128, 128), width=3)
    # Filigrane discret "SPECIMEN FICTIF - CONFORME ARTCI"
    font_specimen = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
    draw.text((width - 380, 28), "SPECIMEN FICTIF - HACKATHON 2026", fill=(180, 50, 50), font=font_specimen)

def draw_tampon(draw, x, y, nom_medecin):
    # Tampon circulaire ou rectangulaire du médecin
    draw.rounded_rectangle([(x, y), (x + 220, y + 90)], radius=8, outline=(20, 70, 140), width=2)
    font_t1 = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 13)
    font_t2 = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 11)
    draw.text((x + 15, y + 12), nom_medecin, fill=(20, 70, 140), font=font_t1)
    draw.text((x + 15, y + 34), "Ordre National Médecins CI", fill=(20, 70, 140), font=font_t2)
    draw.text((x + 15, y + 54), "N° Inscription: 04512-ABJ", fill=(20, 70, 140), font=font_t2)
    draw.text((x + 15, y + 70), "VISA VALIDE", fill=(20, 70, 140), font=font_t2)

def creer_ordonnance_1():
    # Cas 1 : Standard / Lisible
    width, height = 900, 1150
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_cadre_ordonnance(draw, width, height)

    font_header_title = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
    font_header_sub = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
    font_info = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
    font_handwriting = ImageFont.truetype('/System/Library/Fonts/Supplemental/Brush Script.ttf', 38)
    font_sig = ImageFont.truetype('/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', 36)

    # En-tête imprimé
    draw.text((40, 40), "POLYCLINIQUE DES DEUX-PLATEAUX", fill=(0, 90, 90), font=font_header_title)
    draw.text((40, 78), "Service de Médecine Générale & Urgences — Cocody, Abidjan", fill=(80, 80, 80), font=font_header_sub)
    draw.text((40, 100), "Dr. KOUASSI Jean • Spécialiste en Médecine Interne", fill=(60, 60, 60), font=font_header_sub)
    draw.text((40, 122), "Tél: +225 27 22 41 00 00 • Urgences: +225 07 08 09 10", fill=(100, 100, 100), font=font_header_sub)

    # Infos patient
    draw.text((40, 180), "Date : 26 Septembre 2026", fill=(40, 40, 40), font=font_info)
    draw.text((40, 210), "Patient : KONE Ibrahim (Dossier #4092)", fill=(40, 40, 40), font=font_info)
    draw.text((40, 240), "Âge : 34 ans — Poids : 72 kg", fill=(40, 40, 40), font=font_info)

    draw.line([(40, 280), (width - 40, 280)], fill=(220, 220, 220), width=1)

    # Corps manuscrit
    draw.text((80, 340), "1) Doliprane 1000 mg cp", fill=(15, 30, 80), font=font_handwriting)
    draw.text((120, 390), "1 comprime en cas de douleur (max 3/jour)", fill=(20, 35, 90), font=font_handwriting)

    draw.text((80, 490), "2) Amoxicilline 500 mg gelules", fill=(15, 30, 80), font=font_handwriting)
    draw.text((120, 540), "1 gelule matin, midi et soir pendant 7 jours", fill=(20, 35, 90), font=font_handwriting)

    draw.text((80, 640), "3) Spasfon 80 mg comprimes", fill=(15, 30, 80), font=font_handwriting)
    draw.text((120, 690), "2 comprimes si spasmes ou crampes abdominales", fill=(20, 35, 90), font=font_handwriting)

    # Tampon et signature
    draw_tampon(draw, 580, 880, "Dr. KOUASSI Jean")
    draw.text((610, 820), "Signature du Médecin :", fill=(80, 80, 80), font=font_info)
    draw.text((630, 980), "J. Kouassi", fill=(10, 20, 70), font=font_sig)

    out_path = os.path.join(STATIC_SAMPLES_DIR, "ordonnance_1_standard.png")
    img.save(out_path)
    print(f"Généré: {out_path}")

def creer_ordonnance_2():
    # Cas 2 : Dosage ambigu (Sécurité / Blocage pharmacien)
    width, height = 900, 1150
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_cadre_ordonnance(draw, width, height)

    font_header_title = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
    font_header_sub = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
    font_info = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
    font_handwriting = ImageFont.truetype('/System/Library/Fonts/Supplemental/Brush Script.ttf', 38)
    font_sig = ImageFont.truetype('/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', 36)

    # En-tête
    draw.text((40, 40), "CENTRE MEDICAL DU PLATEAU", fill=(0, 90, 90), font=font_header_title)
    draw.text((40, 78), "Consultations Spécialisées — Plateau, Immeuble Horizon, Abidjan", fill=(80, 80, 80), font=font_header_sub)
    draw.text((40, 100), "Dr. AMANI Brigitte • Médecin Généraliste", fill=(60, 60, 60), font=font_header_sub)
    draw.text((40, 122), "Tél: +225 27 20 22 15 15", fill=(100, 100, 100), font=font_header_sub)

    # Infos patient
    draw.text((40, 180), "Date : 25 Septembre 2026", fill=(40, 40, 40), font=font_info)
    draw.text((40, 210), "Patiente : BAKAYOKO Aminata (Fictif)", fill=(40, 40, 40), font=font_info)
    draw.text((40, 240), "Âge : 42 ans", fill=(40, 40, 40), font=font_info)

    draw.line([(40, 280), (width - 40, 280)], fill=(220, 220, 220), width=1)

    # Corps manuscrit avec ambiguïté voulue
    draw.text((80, 350), "1) Spasfon 80 mg cp", fill=(15, 30, 80), font=font_handwriting)
    draw.text((120, 400), "2 comprimes en cas de crise", fill=(20, 35, 90), font=font_handwriting)

    # Ligne 2 : Dosage raturé ou ambigu entre 250mg et 500mg
    draw.text((80, 510), "2) Ciprofloxacine 250/500 mg (?)", fill=(20, 30, 90), font=font_handwriting)
    # Dessin d'une rature manuelle réaliste
    draw.line([(320, 525), (420, 528)], fill=(15, 30, 80), width=2)
    draw.text((120, 565), "1 cp matin et soir pendant 5 jours", fill=(20, 35, 90), font=font_handwriting)

    # Tampon et signature
    draw_tampon(draw, 580, 880, "Dr. AMANI Brigitte")
    draw.text((610, 820), "Signature du Médecin :", fill=(80, 80, 80), font=font_info)
    draw.text((630, 980), "B. Amani", fill=(10, 20, 70), font=font_sig)

    out_path = os.path.join(STATIC_SAMPLES_DIR, "ordonnance_2_ambigue.png")
    img.save(out_path)
    print(f"Généré: {out_path}")

def creer_ordonnance_3():
    # Cas 3 : Posologie absente / incomplète (Règle d'or: Ne rien déduire)
    width, height = 900, 1150
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_cadre_ordonnance(draw, width, height)

    font_header_title = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
    font_header_sub = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
    font_info = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
    font_handwriting = ImageFont.truetype('/System/Library/Fonts/Supplemental/Brush Script.ttf', 38)
    font_sig = ImageFont.truetype('/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', 36)

    # En-tête
    draw.text((40, 40), "CABINET MEDICAL SAINT-MICHEL", fill=(0, 90, 90), font=font_header_title)
    draw.text((40, 78), "Médecine Générale & Pédiatrie — Yopougon Maroc, Abidjan", fill=(80, 80, 80), font=font_header_sub)
    draw.text((40, 100), "Dr. TOURE Moussa", fill=(60, 60, 60), font=font_header_sub)
    draw.text((40, 122), "Tél: +225 05 55 44 33 22", fill=(100, 100, 100), font=font_header_sub)

    # Infos patient
    draw.text((40, 180), "Date : 26 Septembre 2026", fill=(40, 40, 40), font=font_info)
    draw.text((40, 210), "Patient : DIARRA Seydou (Fictif)", fill=(40, 40, 40), font=font_info)
    draw.text((40, 240), "Âge : 28 ans", fill=(40, 40, 40), font=font_info)

    draw.line([(40, 280), (width - 40, 280)], fill=(220, 220, 220), width=1)

    # Corps manuscrit : Coartem prescrit SANS posologie indiquée !
    draw.text((80, 360), "1) Coartem 80/480 mg cp bte/6", fill=(15, 30, 80), font=font_handwriting)
    # Ligne de posologie coupée / laissée vide ou pointillée
    draw.text((120, 410), "..................................", fill=(100, 100, 120), font=font_handwriting)

    draw.text((80, 520), "2) Efferalgan 1g comprimes effervescents", fill=(15, 30, 80), font=font_handwriting)
    draw.text((120, 570), "1 cp dans un verre d'eau si fievre", fill=(20, 35, 90), font=font_handwriting)

    # Tampon et signature
    draw_tampon(draw, 580, 880, "Dr. TOURE Moussa")
    draw.text((610, 820), "Signature du Médecin :", fill=(80, 80, 80), font=font_info)
    draw.text((630, 980), "M. Toure", fill=(10, 20, 70), font=font_sig)

    out_path = os.path.join(STATIC_SAMPLES_DIR, "ordonnance_3_incomplete.png")
    img.save(out_path)
    print(f"Généré: {out_path}")

if __name__ == "__main__":
    creer_ordonnance_1()
    creer_ordonnance_2()
    creer_ordonnance_3()
