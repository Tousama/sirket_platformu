import io
import reflex as rx
import pandas as pd
from typing import List, Dict, Any

from .dashboard_state import DashboardState
from .shared_quotes import SHARED_QUOTES


def format_currency_str(val: float) -> str:
    """Türkçe para formatı"""
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


class ProcurementCoverageState(rx.State):
    currency: str = "TRY (₺)"
    quotes: List[Dict[str, Any]] = []
    missing_items: List[Dict[str, Any]] = []

    genel_kapsama_ortalamasi: str = "%0.0"
    tam_maliyetli_sayisi: int = 0
    kismi_maliyetli_sayisi: int = 0
    eksik_kalem_sayisi: int = 0

    def set_currency(self, cur: str):
        self.currency = cur

    async def on_load(self):
        """Sayfa açıldığında doğrudan Dashboard portföyündeki kayıtlı teklifleri çeker."""
        await self.sync_from_dashboard()

    async def sync_from_dashboard(self):
        """Yalnızca Dashboard'daki Kayıtlı Teklif Portföyünü baz alarak raporu hesaplar."""
        dash_state = await self.get_state(DashboardState)
        raw_list = getattr(dash_state, "raw_quotes", [])

        parsed_quotes = []
        missing_rows = []
        toplam_kapsama_puani = 0.0
        tam_adet = 0
        kismi_adet = 0
        toplam_eksik_kalem = 0

        # Yalnızca Dashboard portföyündeki gerçek teklifleri dolaş
        for q in raw_list:
            kod = q.get("kod") or q.get("teklif_kodu", "")
            if not kod:
                continue

            musteri = q.get("musteri", "-")
            satis_tutari = float(q.get("satis_try") or q.get("satis_orijinal") or 0.0)

            # Kalem listesini al (varsa teklif nesnesinden veya ortak havuzdan)
            kalemler = q.get("kalemler", [])
            if not kalemler and kod in SHARED_QUOTES:
                kalemler = SHARED_QUOTES[kod].get("kalemler", [])

            toplam_k = len(kalemler)

            # Kalem detayları henüz ayrıştırılmamış/yüklenmemişse:
            if toplam_k == 0:
                toplam_k = 1
                maliyet_val = float(q.get("maliyet_try", 0.0))
                fiyati_olan = 1 if maliyet_val > 0 else 0
                eksik_kalan = 0 if maliyet_val > 0 else 1
                kapsama_orani = 100.0 if maliyet_val > 0 else 0.0

                if eksik_kalan > 0:
                    missing_rows.append({
                        "Teklif No": kod,
                        "Müşteri": musteri,
                        "Kalem Açıklaması": q.get("konu", "Teklif Genel Kapsamı"),
                        "Miktar": 1,
                        "Birim": "Set",
                        "Durum": "Satınalma Maliyeti Bekleniyor",
                    })
            else:
                fiyati_olan = sum(1 for k in kalemler if float(k.get("birim_maliyet", 0.0)) > 0)
                eksik_kalan = toplam_k - fiyati_olan
                kapsama_orani = round((fiyati_olan / toplam_k) * 100.0, 1)

                for k in kalemler:
                    if float(k.get("birim_maliyet", 0.0)) <= 0:
                        missing_rows.append({
                            "Teklif No": kod,
                            "Müşteri": musteri,
                            "Kalem Açıklaması": k.get("malzeme_adi") or k.get("tanim", "Tanımsız Kalem"),
                            "Miktar": k.get("miktar", 1),
                            "Birim": k.get("birim", "Adet"),
                            "Durum": "Birim Maliyet Eksik",
                        })

            toplam_kapsama_puani += kapsama_orani
            toplam_eksik_kalem += eksik_kalan

            if kapsama_orani >= 100.0:
                tam_adet += 1
                color = "#10B981"  # Yeşil
            elif kapsama_orani > 0:
                kismi_adet += 1
                color = "#F59E0B"  # Turuncu
            else:
                color = "#EF4444"  # Kırmızı

            parsed_quotes.append({
                "kapsama": kapsama_orani,
                "kapsama_str": f"%{int(kapsama_orani) if kapsama_orani.is_integer() else kapsama_orani}",
                "teklif_no": kod,
                "musteri": musteri,
                "toplam_kalem": toplam_k,
                "fiyati_olan": fiyati_olan,
                "eksik_kalan": eksik_kalan,
                "teklif_tutari": format_currency_str(satis_tutari),
                "status_color": color,
                "is_missing": eksik_kalan > 0,
            })

        self.quotes = parsed_quotes
        self.missing_items = missing_rows
        self.tam_maliyetli_sayisi = tam_adet
        self.kismi_maliyetli_sayisi = kismi_adet
        self.eksik_kalem_sayisi = toplam_eksik_kalem

        if parsed_quotes:
            avg = round(toplam_kapsama_puani / len(parsed_quotes), 1)
            self.genel_kapsama_ortalamasi = f"%{avg}"
        else:
            self.genel_kapsama_ortalamasi = "%0.0"

    def export_excel_missing(self):
        """Eksik Fiyat Kalemleri Raporunu Excel (.xlsx) olarak hazırlar ve indirir"""
        if not self.missing_items:
            return rx.toast.info("Eksik maliyetli kalem bulunamadı.", position="top-right")

        df = pd.DataFrame(self.missing_items)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Eksik Fiyat Kalemleri")

        return rx.download(
            data=output.getvalue(),
            filename="Satinalma_Eksik_Fiyat_Kalemleri.xlsx"
        )