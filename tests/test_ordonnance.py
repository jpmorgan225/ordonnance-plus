import unittest
from gemini_service import chercher_medicament_catalogue

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

    def test_recherche_catalogue_introuvable(self):
        res = chercher_medicament_catalogue("MedicamentTotalementInexistant12345", "")
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
