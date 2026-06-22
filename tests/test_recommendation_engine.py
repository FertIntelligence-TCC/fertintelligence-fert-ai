import unittest

from app.recommendation.schemas import RecommendationRequest
from app.recommendation.service import generate_recommendation


class RecommendationEngineTest(unittest.TestCase):
    def test_acidity_salinity_recommendation_calculates_liming(self):
        request = RecommendationRequest(
            recommendation_type="ACIDITY_SALINITY",
            property={"nome": "Fazenda Teste"},
            plot={"nome": "Talhão 1"},
            fertility_analysis={
                "ph": 5.0,
                "ca": 0.4,
                "mg": 0.2,
                "k": 39.1,
                "al": 0.8,
                "h_al": 4.0,
                "prnt": 80,
                "v_desejado": 60,
            },
            saturation_extract_analysis={
                "ce": 4.5,
                "pst": 16,
                "sar": 14,
            },
            fertilizer_group="PRIVATE",
        )

        response = generate_recommendation(request)
        liming = response.correction_recommendation["liming"]

        self.assertEqual(response.status, "AGRONOMIC_RECOMMENDATION_PLANNED")
        self.assertEqual(liming["status"], "CALCULATED")
        self.assertAlmostEqual(liming["liming_need_t_ha"], 2.12, places=2)
        self.assertAlmostEqual(liming["limestone_dose_t_ha"], 2.65, places=2)

    def test_fertilization_recommendation_calculates_npk(self):
        request = RecommendationRequest(
            recommendation_type="FERTILIZATION",
            property={"nome": "Fazenda Teste"},
            plot={"nome": "Talhão 1"},
            fertility_analysis={"p": 8, "k": 45, "mo": 2.1},
            crop={"nome": "Milho"},
            crop_fertilization_table={
                "nome": "Tabela Milho",
                "recommendations": [
                    {"nutriente": "n", "classe": "Médio", "dose": 120},
                    {"nutriente": "p2o5", "classe": "Baixo", "dose": 90},
                    {"nutriente": "k2o", "classe": "Médio", "dose": 60},
                ],
            },
            soil_fertility_interpretation_table={
                "ranges": [
                    {"nutriente": "p", "min": 0, "max": 10, "classe": "Baixo"},
                    {"nutriente": "k", "min": 30.1, "max": 80, "classe": "Médio"},
                    {"nutriente": "mo", "min": 2.1, "max": 4, "classe": "Médio"},
                ],
            },
            fertilizer_group="PRIVATE",
        )

        response = generate_recommendation(request)
        nutrients = response.fertilization_recommendation["nutrient_recommendation"]

        self.assertEqual(nutrients["status"], "CALCULATED_PARTIAL")
        self.assertEqual(nutrients["n_kg_ha"], 120)
        self.assertEqual(nutrients["p2o5_kg_ha"], 90)
        self.assertEqual(nutrients["k2o_kg_ha"], 60)

    def test_fertilizer_solver_suggests_commercial_fertilizers(self):
        request = RecommendationRequest(
            recommendation_type="FERTILIZATION",
            property={"nome": "Fazenda Teste"},
            plot={"nome": "Talhão 1"},
            fertility_analysis={"p": 8, "k": 45, "mo": 2.1},
            crop={"nome": "Milho"},
            crop_fertilization_table={
                "recommendations": [
                    {"nutriente": "n", "classe": "Médio", "dose": 120},
                    {"nutriente": "p2o5", "classe": "Baixo", "dose": 90},
                    {"nutriente": "k2o", "classe": "Médio", "dose": 60},
                ],
            },
            soil_fertility_interpretation_table={
                "ranges": [
                    {"nutriente": "p", "min": 0, "max": 10, "classe": "Baixo"},
                    {"nutriente": "k", "min": 30.1, "max": 80, "classe": "Médio"},
                    {"nutriente": "mo", "min": 2.1, "max": 4, "classe": "Médio"},
                ],
            },
            fertilizer_group="PRIVATE",
            fertilizer_source={
                "fertilizers": [
                    {"nome": "Ureia", "n": 45, "p2o5": 0, "k2o": 0},
                    {"nome": "Superfosfato Triplo", "n": 0, "p2o5": 41, "k2o": 0},
                    {"nome": "Cloreto de Potássio", "n": 0, "p2o5": 0, "k2o": 60},
                ]
            },
        )

        response = generate_recommendation(request)

        names = {item["fertilizer_name"] for item in response.fertilizer_suggestions}

        self.assertIn("Ureia", names)
        self.assertIn("Superfosfato Triplo", names)
        self.assertIn("Cloreto de Potássio", names)


if __name__ == "__main__":
    unittest.main()
