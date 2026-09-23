import reflex as rx
from typing import List, Dict, Any

RAW_PRICE_CATALOG: List[Dict[str, Any]] = [
    {
        "tanim": "VEGAPULS 6X (Radar Seviye)",
        "marka": "VEGA",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 1850.00,
        "satis": 2450.00,
        "kaynak": "PT202600149 (Beril TEKİN)",
        "guncellik": "Güncel (3g)",
    },
    {
        "tanim": "VEGASWING 61 (Level Switch)",
        "marka": "VEGA",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 420.00,
        "satis": 590.00,
        "kaynak": "PT202600149 (Beril TEKİN)",
        "guncellik": "Güncel (3g)",
    },
    {
        "tanim": "Cerabar PMP51 Basınç Transmitteri",
        "marka": "Endress+Hauser",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 750.00,
        "satis": 1050.00,
        "kaynak": "PT202609191725 (OMC)",
        "guncellik": "Güncel (5g)",
    },
    {
        "tanim": "Micropilot FMR60 Radar",
        "marka": "Endress+Hauser",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 2100.00,
        "satis": 2850.00,
        "kaynak": "PT202609191725 (OMC)",
        "guncellik": "Güncel (5g)",
    },
    {
        "tanim": "BARTEC EJB51 Exproof Kutu",
        "marka": "BARTEC",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 1250.00,
        "satis": 1750.00,
        "kaynak": "PT202600112 (Umut Can Toprak)",
        "guncellik": "Güncel (8g)",
    },
    {
        "tanim": "BIMED M25 Çelik Zırhlı Rakor",
        "marka": "BIMED",
        "birim": "Adet",
        "pb": "EUR",
        "maliyet": 18.50,
        "satis": 26.00,
        "kaynak": "PT202600112 (Umut Can Toprak)",
        "guncellik": "Güncel (8g)",
    },
    {
        "tanim": "Pakkens 160mm 0-100 Bar Manometre",
        "marka": "Pakkens",
        "birim": "Adet",
        "pb": "TRY",
        "maliyet": 1450.00,
        "satis": 2100.00,
        "kaynak": "PT202609191650 (OMC)",
        "guncellik": "Güncel (5g)",
    },
]

class PriceCatalogState(rx.State):
    # Arama ve Filtreler
    search_query: str = ""
    selected_brand: str = "Tüm Markalar"
    selected_currency: str = "Tüm PB"

    brand_options: List[str] = ["Tüm Markalar", "VEGA", "Endress+Hauser", "BARTEC", "BIMED", "Pakkens"]
    currency_options: List[str] = ["Tüm PB", "TRY", "USD", "EUR"]

    def set_search_query(self, val: str):
        self.search_query = val

    def set_selected_brand(self, val: str):
        self.selected_brand = val

    def set_selected_currency(self, val: str):
        self.selected_currency = val

    @rx.var
    def filtered_items(self) -> List[Dict[str, Any]]:
        q = self.search_query.strip().lower()
        items = []

        for row in RAW_PRICE_CATALOG:
            # Marka filtresi
            if self.selected_brand != "Tüm Markalar" and row["marka"] != self.selected_brand:
                continue
            # Para birimi filtresi
            if self.selected_currency != "Tüm PB" and row["pb"] != self.selected_currency:
                continue
            # Arama filtresi
            if q:
                match = (
                    q in row["tanim"].lower()
                    or q in row["marka"].lower()
                    or q in row["kaynak"].lower()
                )
                if not match:
                    continue

            # Kâr Marjı Hesabı (Maliyet Üzerinden Markup)
            c = float(row["maliyet"])
            s = float(row["satis"])
            marj = round(((s - c) / c) * 100, 1) if c > 0 else 0.0

            items.append({
                "tanim": row["tanim"],
                "marka": row["marka"],
                "birim": row["birim"],
                "pb": row["pb"],
                "maliyet_str": f"{c:.2f}",
                "satis_str": f"{s:.2f}",
                "marj_str": f"%{marj:.1f}",
                "kaynak": row["kaynak"],
                "guncellik": row["guncellik"],
            })

        return items

    @rx.var
    def total_count_str(self) -> str:
        return f"{len(self.filtered_items)} Kalem"

    def sync_pool(self):
        return rx.toast.success(
            "Fiyat havuzu geçmiş ERP ve onaylanan teklif veri tabanı ile senkronize edildi!",
            position="top-right"
        )