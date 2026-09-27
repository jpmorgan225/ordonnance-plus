import unittest
from gemini_service import chercher_medicament_catalogue, PRESETS_ANALYSES

class TestOrdonnancePlus(unittest.TestCase):
    def test_recherche_catalogue_doliprane(self):
        res = chercher_medicament_catalogue("Doliprane", "1000 mg")
        self.assertIsNotNone(res)
        self.assertIn("DOLIPRANE", res["nom"])
        self.assertGreater(res["prix_fcfa"], 0)

    def test_recherche_catalogue_spasfon(self):
        res = chercher_medicament_catalogue("Spasfon", "80 mg")
        self.assertIsNotNone(res)
        self.assertIn("SPASFON", res["nom"])
        self.assertGreater(res["prix_fcfa"], 0)

    def test_recherche_catalogue_amoxicilline(self):
        res = chercher_medicament_catalogue("Amoxicilline", "500 mg")
        self.assertIsNotNone(res)
        self.assertIn("AMOXICILLINE", res["nom"])
        self.assertGreater(res["prix_fcfa"], 0)

    def test_preset_sample_2_douteux(self):
        data = PRESETS_ANALYSES["sample_2"]
        lignes = data["lignes"]
        self.assertEqual(len(lignes), 2)
        # La ligne 2 doit comporter un doute
        self.assertEqual(lignes[1]["confiance"], "douteux")
        self.assertFalse(lignes[1]["valide_par_pharmacien"])
        self.assertEqual(data["statut_global"], "contient_doutes")

    def test_preset_sample_3_posologie_inconnue(self):
        data = PRESETS_ANALYSES["sample_3"]
        lignes = data["lignes"]
        # Posologie de Coartem ne doit rien inventer
        self.assertEqual(lignes[0]["posologie_recopiee"], "À confirmer auprès du pharmacien")

if __name__ == "__main__":
    unittest.main()
