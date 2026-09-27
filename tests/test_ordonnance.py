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

    def test_calcul_distance_et_pharmacies_garde(self):
        from app import app, calculer_distance_km
        from fastapi.testclient import TestClient

        # Distance entre 2 points connus d'Abidjan
        d = calculer_distance_km(5.3482, -4.0041, 5.3621, -3.9985)
        self.assertGreater(d, 1.0)
        self.assertLess(d, 2.5)

        client = TestClient(app)
        # Requête sans coordonnées
        res = client.get("/api/pharmacies-garde")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["count"], 25)
        self.assertFalse(data["geolocalise"])

        # Requête avec géolocalisation
        res_geo = client.get("/api/pharmacies-garde?lat=5.35&lon=-4.00")
        self.assertEqual(res_geo.status_code, 200)
        data_geo = res_geo.json()
        self.assertTrue(data_geo["geolocalise"])
        self.assertIsNotNone(data_geo["pharmacies"][0]["distance_km"])
        # Doit être trié par distance croissante
        dists = [p["distance_km"] for p in data_geo["pharmacies"]]
        self.assertEqual(dists, sorted(dists))

if __name__ == "__main__":
    unittest.main()
