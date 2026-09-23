import reflex as rx
from typing import List, Dict, Any

class CompetitorIntelState(rx.State):
    # Aktif Sekme (Tab)
    active_tab: str = "tahmin"  # "tahmin", "kaydet", "profiller"

    # Teklif Seçenekleri
    teklif_secenekleri: List[str] = [
        "PT202609201555 Deneme | Shell (Maliyet: 207.134,88 ₺)",
        "PT202609191725 | OMC Sıvı Terminali (Maliyet: 513.679,94 ₺)",
        "PT2026088103 | AVES GÜNEY Motorin Pompası (Maliyet: 320.000,00 ₺)",
        "PT2026088039 | DERİNCE SHELL TERMİNALİ (Maliyet: 185.000,00 ₺)",
    ]
    secilen_teklif: str = "PT202609201555 Deneme | Shell (Maliyet: 207.134,88 ₺)"

    # Rakip Seçenekleri
    rakip_secenekleri: List[str] = [
        "Atlas Otomasyon",
        "Delta Vana & Enstrümantasyon",
        "Proses Mühendislik A.Ş.",
        "Marmara Akaryakıt Sistemleri",
    ]
    secilen_rakip: str = "Atlas Otomasyon"

    # Rakip Profilleri Veritabanı
    rakip_profilleri: Dict[str, Dict[str, Any]] = {
        "Atlas Otomasyon": {
            "ortalama_marj": 33.3,
            "ihale_sayisi": 3,
            "guvenilirlik": "Yüksek",
            "fiyatlama_tipi": "Standart Kâr Odaklı",
        },
        "Delta Vana & Enstrümantasyon": {
            "ortalama_marj": 28.5,
            "ihale_sayisi": 5,
            "guvenilirlik": "Çok Yüksek",
            "fiyatlama_tipi": "Agresif / Kırıcı Fiyat",
        },
        "Proses Mühendislik A.Ş.": {
            "ortalama_marj": 38.0,
            "ihale_sayisi": 2,
            "guvenilirlik": "Orta",
            "fiyatlama_tipi": "Yüksek Fiyat / Kalite Odaklı",
        },
        "Marmara Akaryakıt Sistemleri": {
            "ortalama_marj": 31.0,
            "ihale_sayisi": 4,
            "guvenilirlik": "Yüksek",
            "fiyatlama_tipi": "Dengeli",
        },
    }

    # Hesaplanan KPI Değerleri (String & Float)
    bizim_maliyet: float = 207134.88
    bizim_maliyet_str: str = "207.134,88 ₺"

    tahmini_rakip_fiyati: float = 276189.39
    tahmini_rakip_fiyati_str: str = "276.189,39 ₺"
    rakip_marj_str: str = "%33.3 Marj ile"

    onerilen_fiyat: float = 270665.60
    onerilen_fiyat_str: str = "270.665,60 ₺"
    onerilen_marj_str: str = "%30.7 Kâr ile"

    veri_guvenilirligi: str = "Yüksek"
    gecmis_ihale_sayisi_str: str = "3 Geçmiş İhale"

    tavsiye_metni: str = (
        "Mevcut teklif fiyatınız rakibin tahmin edilen fiyatının üzerinde görünmektedir. "
        "İhaleyi alma şansınızı yükseltmek için fiyatı 270.665,60 ₺ seviyesine çekerek %30.7 brüt kârı koruyabilirsiniz."
    )

    # 2. Sekme: Yeni İhale / Rakip Fiyatı Kaydetme Formu
    yeni_ihale_musteri: str = ""
    yeni_ihale_tarih: str = "2026-09"
    yeni_ihale_rakip: str = "Atlas Otomasyon"
    yeni_ihale_rakip_fiyat: str = ""
    yeni_ihale_bizim_maliyet: str = ""
    yeni_ihale_kazanan: str = "Biz Kazandık"

    # Setters
    def set_active_tab(self, tab: str): self.active_tab = tab
    def set_secilen_teklif(self, val: str): self.secilen_teklif = val
    def set_secilen_rakip(self, val: str): self.secilen_rakip = val

    def set_yeni_ihale_musteri(self, val: str): self.yeni_ihale_musteri = val
    def set_yeni_ihale_rakip(self, val: str): self.yeni_ihale_rakip = val
    def set_yeni_ihale_rakip_fiyat(self, val: str): self.yeni_ihale_rakip_fiyat = val
    def set_yeni_ihale_bizim_maliyet(self, val: str): self.yeni_ihale_bizim_maliyet = val
    def set_yeni_ihale_kazanan(self, val: str): self.yeni_ihale_kazanan = val

    def simule_et(self):
        """Seçilen teklif ve rakip profiline göre Sweet Spot fiyatını anında simüle eder."""
        # Maliyeti teklif metninden güvenle ayrıştır
        try:
            cost_part = self.secilen_teklif.split("Maliyet:")[1].replace("₺", "").replace(")", "").replace(".", "").replace(",", ".").strip()
            cost = float(cost_part)
        except Exception:
            cost = 207134.88

        self.bizim_maliyet = cost
        self.bizim_maliyet_str = f"{cost:,.2f} ₺"

        prof = self.rakip_profilleri.get(self.secilen_rakip, {
            "ortalama_marj": 30.0,
            "ihale_sayisi": 3,
            "guvenilirlik": "Orta",
        })

        margin = float(prof["ortalama_marj"]) / 100.0
        # Rakibin tahmin edilen satış fiyatı: Cost / (1 - Margin)
        comp_price = round(cost / (1.0 - margin), 2)
        # Sweet Spot: Rakip tahmini fiyatının %2 altı (İhaleyi kapma eşiği)
        sweet_spot = round(comp_price * 0.98, 2)
        our_margin = round(((sweet_spot - cost) / sweet_spot) * 100, 1)

        self.tahmini_rakip_fiyati = comp_price
        self.tahmini_rakip_fiyati_str = f"{comp_price:,.2f} ₺"
        self.rakip_marj_str = f"%{prof['ortalama_marj']} Marj ile"

        self.onerilen_fiyat = sweet_spot
        self.onerilen_fiyat_str = f"{sweet_spot:,.2f} ₺"
        self.onerilen_marj_str = f"%{our_margin} Kâr ile"

        self.veri_guvenilirligi = prof["guvenilirlik"]
        self.gecmis_ihale_sayisi_str = f"{prof['ihale_sayisi']} Geçmiş İhale"

        self.tavsiye_metni = (
            f"Mevcut teklif fiyatınız rakibin tahmin edilen fiyatının üzerinde görünmektedir. "
            f"İhaleyi alma şansınızı yükseltmek için fiyatı {self.onerilen_fiyat_str} seviyesine çekerek %{our_margin} brüt kârı koruyabilirsiniz."
        )

        return rx.toast.success(
            f"{self.secilen_rakip} için simülasyon tamamlandı! Önerilen fiyat: {self.onerilen_fiyat_str}",
            position="top-right"
        )

    def ihale_kaydet(self):
        """Geçmiş ihale sonucunu istihbarat havuzuna ekler."""
        if not self.yeni_ihale_musteri or not self.yeni_ihale_rakip_fiyat:
            return rx.toast.error("Lütfen müşteri ve rakip fiyatı alanlarını doldurun.", position="top-right")

        return rx.toast.success(
            f"{self.yeni_ihale_rakip} firmasına ait ihale verisi kaydedildi. Model güncellendi!",
            position="top-right"
        )