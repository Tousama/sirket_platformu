import reflex as rx
from typing import List

class LaborEngineState(rx.State):
    # Teklif Seçimi
    referans_secenekleri: List[str] = [
        "PT202609201555 Deneme | Shell | Enstruman Temini",
        "PT202609191725-Rev1 | OMC | LP Enstrumantasyon (Rev1)",
        "PT202609191650 | OMC | Radar & Pressure Gauge Temini",
        "PT2026088103 | Doğukan KILIÇ | AVES GÜNEY Motorin Pompası Scully",
        "PT2026088039 | GİZEM AKYILDIZ | DERİNCE SHELL TERMİNALİ UPS BAĞLANTISI",
    ]
    secilen_teklif: str = "PT202609201555 Deneme | Shell | Enstruman Temini"

    # 1. Metraj & Ekipman Sayıları
    kablo_tava_m: float = 50.0
    kablo_cekim_m: float = 250.0
    gland_baglanti_ad: float = 16.0
    enstruman_test_ad: float = 4.0
    saha_panosu_ad: float = 1.0
    ilave_demontaj_as: float = 10.0

    # 2. Ekip & Mobilizasyon
    teknisyen_sayisi: float = 2.0
    supervizor_gun: float = 2.0
    harcirah_gun_tl: float = 750.0
    otel_gece_tl: float = 2500.0
    ulasim_arac_tl: float = 6500.0

    # Elle Ayarlanabilir Hedef Kâr Marjı (%)
    custom_margin_percent: float = 58.6

    # BOM'a Eklenecek Hizmet Adı
    hizmet_aciklamasi: str = "Saha Enstrümantasyon, Kablo Çekimi, Montaj ve Devreye Alma Hizmeti"

    # Setters
    def set_secilen_teklif(self, val: str): self.secilen_teklif = val
    def set_kablo_tava_m(self, val: str): self.kablo_tava_m = float(val) if val else 0.0
    def set_kablo_cekim_m(self, val: str): self.kablo_cekim_m = float(val) if val else 0.0
    def set_gland_baglanti_ad(self, val: str): self.gland_baglanti_ad = float(val) if val else 0.0
    def set_enstruman_test_ad(self, val: str): self.enstruman_test_ad = float(val) if val else 0.0
    def set_saha_panosu_ad(self, val: str): self.saha_panosu_ad = float(val) if val else 0.0
    def set_ilave_demontaj_as(self, val: str): self.ilave_demontaj_as = float(val) if val else 0.0
    def set_teknisyen_sayisi(self, val: str): self.teknisyen_sayisi = float(val) if val else 1.0
    def set_supervizor_gun(self, val: str): self.supervizor_gun = float(val) if val else 0.0
    def set_harcirah_gun_tl(self, val: str): self.harcirah_gun_tl = float(val) if val else 0.0
    def set_otel_gece_tl(self, val: str): self.otel_gece_tl = float(val) if val else 0.0
    def set_ulasim_arac_tl(self, val: str): self.ulasim_arac_tl = float(val) if val else 0.0
    def set_hizmet_aciklamasi(self, val: str): self.hizmet_aciklamasi = val

    def set_custom_margin_percent(self, val: str):
        try:
            m = float(val)
            if m >= 99.0:
                m = 99.0
            elif m < 0.0:
                m = 0.0
            self.custom_margin_percent = round(m, 1)
        except ValueError:
            pass

    # --- HESAPLANAN DEĞERLER (NORM TABANI v2.4) ---
    @rx.var
    def teknisyen_as(self) -> float:
        val = (self.kablo_tava_m * 0.40) + \
              (self.kablo_cekim_m * 0.16) + \
              (self.gland_baglanti_ad * 0.75) + \
              (self.saha_panosu_ad * 6.0) + \
              self.ilave_demontaj_as + \
              (self.enstruman_test_ad * 0.525)
        return round(val, 1)

    @rx.var
    def muhendis_as(self) -> float:
        val = (self.supervizor_gun * 8.0) + (self.enstruman_test_ad * 1.5)
        return round(val, 1)

    @rx.var
    def tahmini_saha_suresi_gun(self) -> float:
        crew = self.teknisyen_sayisi if self.teknisyen_sayisi > 0 else 1.0
        val = self.teknisyen_as / (crew * 8.0)
        return round(val, 1)

    # Temel Maliyetler
    @rx.var
    def cost_teknisyen(self) -> float:
        return round(self.teknisyen_as * 450.0, 2)

    @rx.var
    def cost_muhendis(self) -> float:
        return round(self.muhendis_as * 750.0, 2)

    @rx.var
    def cost_mobilizasyon(self) -> float:
        gun = self.tahmini_saha_suresi_gun
        crew = self.teknisyen_sayisi
        total_people = crew + 1.0
        rooms = (crew / 2.0) + 1.0

        harcirah = total_people * self.harcirah_gun_tl * gun
        konaklama = rooms * self.otel_gece_tl * gun
        return round(harcirah + konaklama + self.ulasim_arac_tl, 2)

    @rx.var
    def cost_total(self) -> float:
        return round(self.cost_teknisyen + self.cost_muhendis + self.cost_mobilizasyon, 2)

    # Satış Fiyatları (Girdiğiniz Hedef Kâr Marjına Göre Hesaplanır)
    @rx.var
    def price_multiplier(self) -> float:
        m = self.custom_margin_percent / 100.0
        if m >= 0.99:
            return 100.0
        return 1.0 / (1.0 - m)

    @rx.var
    def price_teknisyen(self) -> float:
        return round(self.cost_teknisyen * self.price_multiplier, 2)

    @rx.var
    def price_muhendis(self) -> float:
        return round(self.cost_muhendis * self.price_multiplier, 2)

    @rx.var
    def price_mobilizasyon(self) -> float:
        return round(self.cost_mobilizasyon * self.price_multiplier, 2)

    @rx.var
    def price_total(self) -> float:
        return round(self.price_teknisyen + self.price_muhendis + self.price_mobilizasyon, 2)

    # Formatlanmış Değerler
    @rx.var
    def cost_teknisyen_str(self) -> str: return f"{self.cost_teknisyen:,.2f}"
    @rx.var
    def price_teknisyen_str(self) -> str: return f"{self.price_teknisyen:,.2f}"
    @rx.var
    def cost_muhendis_str(self) -> str: return f"{self.cost_muhendis:,.2f}"
    @rx.var
    def price_muhendis_str(self) -> str: return f"{self.price_muhendis:,.2f}"
    @rx.var
    def cost_mobilizasyon_str(self) -> str: return f"{self.cost_mobilizasyon:,.2f}"
    @rx.var
    def price_mobilizasyon_str(self) -> str: return f"{self.price_mobilizasyon:,.2f}"
    @rx.var
    def cost_total_str(self) -> str: return f"{self.cost_total:,.2f}"
    @rx.var
    def price_total_str(self) -> str: return f"{self.price_total:,.2f}"
    @rx.var
    def kar_marji_yuzde(self) -> float:
        return self.custom_margin_percent


    def aktar_bom(self):        
            # 1. Revizyon modülündeki veritabanını import et
            from .revision_diff_state import VERSIONS_DB
    
            target_version = None
            # Seçilen teklif kodunu içeren versiyonu bul
            clean_code = self.secilen_teklif.split("|")[0].strip()
            for v_name in VERSIONS_DB.keys():
                if clean_code in v_name:
                    target_version = v_name
                    break
    
            if target_version and target_version in VERSIONS_DB:
                # İşçilik hizmetini bağımsız bir kalem olarak ilgili versiyonun items listesine ekle
                VERSIONS_DB[target_version]["items"][self.hizmet_aciklamasi] = {
                    "miktar": 1.0,
                    "birim": "Hizmet",
                    "satis": float(self.price_total),
                }
                # Versiyonun toplam maliyet ve satışını güncelle
                VERSIONS_DB[target_version]["maliyet"] = float(self.cost_total)
                VERSIONS_DB[target_version]["satis"] = float(self.price_total)
    
                return rx.toast.success(
                    f"'{self.hizmet_aciklamasi}' kalemi ({self.price_total_str} ₺) '{target_version}' teklifine başarıyla eklendi!",
                    position="top-right"
                )
            else:
                return rx.toast.warning(
                    f"'{clean_code}' koduyla eşleşen bir teklif versiyonu bulunamadı.",
                    position="top-right"
                )