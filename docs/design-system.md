# Design System — Ordonnance+

## Identity
- **Nom :** Ordonnance+
- **Positionnement :** Assistant de lecture et transcription pour pharmaciens en Côte d'Ivoire.
- **Ton :** Médical, rigoureux, sécurisant, épuré, moderne (style Doctolib / Alan).

## Typography
- **Police Principale :** `Plus Jakarta Sans`, sans-serif (lisibilité optimale pour données médicales).
- **Police Chiffres / Prix / Codes :** `JetBrains Mono`, monospace (précision des montants en FCFA et codes CIS).

## Color Palette
- **Fond principal :** Dark Slate (`#020617` / `#0f172a`) pour un confort visuel prolongé en officine.
- **Teinte de Marque / Succès :** Émeraude médicale (`#10b981` / `#059669`).
- **Alerte Sécurité / Doute :** Ambre lumineux (`#f59e0b` / `#d97706`) pour attirer l'attention sur les ratures ou dosages incertains sans être anxiogène.
- **Danger / Bloquant :** Rose / Rouge doux (`#ef4444`).
- **Impression Fiche Patient :** Fond blanc immaculé (`#ffffff`), texte noir profond (`#0f172a`), bordures vert officiel de pharmacie.

## Key UI Components
1. **Document Split-Screen :** Visualiseur d'ordonnance à gauche avec zoom continu (0.5x à 3.0x), espace d'édition et de validation à droite.
2. **Safety Banner :** Bandeau dynamique en tête de formulaire indiquant si des incertitudes subsistent.
3. **Line Card :** Carte interactive par médicament permettant l'édition inline et la confirmation par le pharmacien en 1 clic.
4. **Printable Modal :** Fiche de dispensation au format A4 officiel prête à imprimer avec Visa du pharmacien.
