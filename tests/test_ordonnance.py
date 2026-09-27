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
        # Requête sans coordonnées (commune par défaut Cocody)
        res = client.get("/api/pharmacies-garde")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["commune_active"], "Cocody")
        self.assertGreater(data["count"], 0)
        self.assertFalse(data["geolocalise"])
        for p in data["pharmacies"]:
            self.assertEqual(p["commune"], "Cocody")

        # Requête avec commune explicite (Yopougon)
        res_yop = client.get("/api/pharmacies-garde?commune=Yopougon")
        self.assertEqual(res_yop.status_code, 200)
        data_yop = res_yop.json()
        self.assertEqual(data_yop["commune_active"], "Yopougon")
        for p in data_yop["pharmacies"]:
            self.assertEqual(p["commune"], "Yopougon")

        # Requête avec filtre service de garde
        res_garde = client.get("/api/pharmacies-garde?commune=Cocody&service=garde")
        self.assertEqual(res_garde.status_code, 200)
        data_garde = res_garde.json()
        for p in data_garde["pharmacies"]:
            self.assertTrue(p["est_de_garde"])

        # Requête avec géolocalisation
        res_geo = client.get("/api/pharmacies-garde?lat=5.35&lon=-4.00")
        self.assertEqual(res_geo.status_code, 200)
        data_geo = res_geo.json()
        self.assertTrue(data_geo["geolocalise"])
        self.assertIsNotNone(data_geo["pharmacies"][0]["distance_km"])
        # Doit être trié par distance croissante
        dists = [p["distance_km"] for p in data_geo["pharmacies"]]
        self.assertEqual(dists, sorted(dists))
        # Toutes les pharmacies retournées doivent être de la commune détectée
        for p in data_geo["pharmacies"]:
            self.assertEqual(p["commune"], data_geo["commune_active"])

    def test_endpoint_tts(self):
        from app import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        res = client.get("/api/tts?text=12ml%20x2j&voice=vivienne")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "audio/mpeg")
        self.assertGreater(len(res.content), 1000)

    def test_traduction_abreviations_medicales(self):
        from gemini_service import traduire_abreviations_medicales

        # Test cas d'abréviations médicales réelles
        t1 = traduire_abreviations_medicales("12ml x2j pdt 5j")
        self.assertIn("12 millilitres", t1)
        self.assertIn("deux fois par jour", t1)
        self.assertIn("matin et le soir", t1)
        self.assertIn("pendant 5 jours", t1)

        t2 = traduire_abreviations_medicales("1 cp x 3/j av rep")
        self.assertIn("comprimé", t2)
        self.assertIn("trois fois par jour", t2)
        self.assertIn("avant le repas", t2)

        t3 = traduire_abreviations_medicales("1/2 cp mat/soir")
        self.assertIn("un demi-comprimé", t3)
        self.assertIn("le matin et le soir", t3)

        t4 = traduire_abreviations_medicales("1 dose-poids x3/j")
        self.assertIn("pipette graduée", t4)

    def test_adaptation_vers_ivoirien(self):
        from gemini_service import adapter_vers_ivoirien

        t1 = adapter_vers_ivoirien("Prenez 1 cp x2j av rep pdt 5j")
        self.assertIn("faut prendre", t1)
        self.assertIn("deux fois dans la journée", t1)
        self.assertIn("avant de manger", t1)
        self.assertIn("sans sauter de jour", t1)

        t2 = adapter_vers_ivoirien("1 sachet à dissoudre dans un verre d'eau au coucher")
        self.assertIn("bien mélanger dans un verre d'eau", t2)
        self.assertIn("la nuit avant d'aller dormir", t2)

if __name__ == "__main__":
    unittest.main()


