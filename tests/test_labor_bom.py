import tempfile
import unittest
from pathlib import Path

from sirket_platformu.services import db_service


class LaborBomTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db_service.DB_PATH
        db_service.DB_PATH = str(Path(self.temp_dir.name) / "test.db")
        db_service.init_db()

        db_service.save_teklif_full(
            {
                "kod": "TK-TEST-1",
                "musteri": "Test Musteri",
                "konu": "Test Teklifi",
                "satis_toplam": 1000.0,
                "maliyet_toplam": 600.0,
                "durum": "Hazirlaniyor",
            },
            [
                {
                    "malzeme_adi": "Malzeme",
                    "miktar": 1.0,
                    "birim": "Adet",
                    "birim_satis": 1000.0,
                    "toplam_tl": 1000.0,
                    "birim_maliyet": 600.0,
                }
            ],
        )

    def tearDown(self):
        db_service.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_labor_item_increases_quote_totals_and_is_persisted(self):
        totals = db_service.upsert_teklif_kalemi(
            "TK-TEST-1", "Saha Isciligi", 1.0, "Hizmet", 200.0, 100.0
        )

        self.assertEqual(totals, {"satis_toplam": 1200.0, "maliyet_toplam": 700.0})
        quote = db_service.get_teklif_by_kod("TK-TEST-1")
        self.assertEqual(quote["satis_toplam"], 1200.0)
        self.assertEqual(quote["maliyet_toplam"], 700.0)
        labor = next(k for k in quote["kalemler"] if k["malzeme_adi"] == "Saha Isciligi")
        self.assertEqual(labor["toplam_tl"], 200.0)
        self.assertEqual(labor["birim_maliyet"], 100.0)

    def test_same_labor_item_updates_by_delta_instead_of_double_counting(self):
        db_service.upsert_teklif_kalemi(
            "TK-TEST-1", "Saha Isciligi", 1.0, "Hizmet", 200.0, 100.0
        )
        totals = db_service.upsert_teklif_kalemi(
            "TK-TEST-1", "Saha Isciligi", 1.0, "Hizmet", 250.0, 120.0
        )

        self.assertEqual(totals, {"satis_toplam": 1250.0, "maliyet_toplam": 720.0})
        quote = db_service.get_teklif_by_kod("TK-TEST-1")
        matching = [k for k in quote["kalemler"] if k["malzeme_adi"] == "Saha Isciligi"]
        self.assertEqual(len(matching), 1)


if __name__ == "__main__":
    unittest.main()
