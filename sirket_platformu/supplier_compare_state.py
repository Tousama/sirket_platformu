import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .services.db_service import get_all_teklifler_from_db, get_teklif_by_kod, save_teklif_to_db

# Bilinen endüstriyel tedarikçi ve marka havuzu
VENDORS_CATALOG = {
    "kablo": [
        {"vendor": "Prysmian", "factor": 1.05},
        {"vendor": "2M Kablo", "factor": 0.95},
        {"vendor": "Nexans", "factor": 1.08},
    ],
    "box": [
        {"vendor": "Cortem (Ex-Proof)", "factor": 1.10},
        {"vendor": "Weidmüller Klippon", "factor": 1.00},
        {"vendor": "Rose Systemtechnik", "factor": 0.94},
    ],
    "tava": [
        {"vendor": "EAE Elektrik", "factor": 0.93},
        {"vendor": "Gersan", "factor": 0.97},
        {"vendor": "Bticino", "factor": 1.06},
    ],
    "enstruman": [
        {"vendor": "TechnipFMC / Smith Meter", "factor": 1.00},
        {"vendor": "Emerson / Rosemount", "factor": 1.04},
        {"vendor": "Endress+Hauser", "factor": 1.02},
    ],
    "genel": [
        {"vendor": "A Tedarikçisi", "factor": 0.96},
        {"vendor": "B Tedarikçisi", "factor": 1.02},
        {"vendor": "C Tedarikçisi", "factor": 0.98},
    ]
}


class SupplierCompareState(rx.State):
    # Base Vars (Reflex @rx.var ile çakışmayacak temiz değişkenler)
    teklif_kodlari: List[str] = []
    secilen_teklif_kodu: str = ""
    is_loading: bool = False
    
    # Karşılaştırma Matrisi ve Fiyat Listeleri
    karsilastirma_matrisi: List[Dict[str, Any]] = []
    
    # Finansal Özet Metrikleri
    toplam_liste_fiyati: float = 0.0
    en_iyi_sepet_toplami: float = 0.0
    elde_edilen_tasarruf: float = 0.0
    tasarruf_orani_str: str = "%0.0"
    para_birimi_sembol: str = "₺"

    # =========================================================================
    # VERİTABANI SENKRONİZASYONU
    # =========================================================================
    async def teklifleri_guncelle(self):
        """SQLite veritabanındaki tüm teklifleri çeker ve dropdown listesini yeniler."""
        self.is_loading = True
        yield

        try:
            db_teklifler = get_all_teklifler_from_db()
            kodlar = [t["kod"] for t in db_teklifler if "kod" in t]
            self.teklif_kodlari = list(dict.fromkeys(kodlar))

            if self.teklif_kodlari:
                if not self.secilen_teklif_kodu or self.secilen_teklif_kodu not in self.teklif_kodlari:
                    self.secilen_teklif_kodu = self.teklif_kodlari[0]
                await self.load_quote_matrix(self.secilen_teklif_kodu)
            else:
                self.karsilastirma_matrisi = []
                self._sifirla_ozet()
        except Exception:
            self.karsilastirma_matrisi = []
            self._sifirla_ozet()

        self.is_loading = False
        yield

    async def set_teklif(self, kod: str):
        """Dropdown üzerinden farklı bir teklif seçildiğinde matrisi yeniden kurar."""
        self.secilen_teklif_kodu = kod
        await self.load_quote_matrix(kod)

    # =========================================================================
    # ÇOKLU TEDARİKÇİ VE EN İYİ SEPET MATRİS MOTORU
    # =========================================================================
    async def load_quote_matrix(self, kod: str):
        teklif = get_teklif_by_kod(kod)
        if not teklif:
            self.karsilastirma_matrisi = []
            self._sifirla_ozet()
            return

        kalemler = teklif.get("kalemler", [])
        self.para_birimi_sembol = teklif.get("para_birimi_sembol", "₺")

        yeni_matris = []
        toplam_liste = 0.0
        en_iyi_toplam = 0.0

        for idx, k in enumerate(kalemler):
            ad = k.get("malzeme_adi") or k.get("tanim") or k.get("aciklama") or f"Kalem {idx+1}"
            mik = float(k.get("miktar", 1.0))
            birim = str(k.get("birim", "Adet"))
            b_fiyat = float(k.get("birim_fiyat") or k.get("birim_satis") or 0.0)
            
            # Baz liste maliyeti
            baz_birim_maliyet = b_fiyat * 0.70 if b_fiyat > 0 else 100.0

            # Malzeme türüne göre tedarikçi alternatiflerini türet
            ad_low = ad.lower()
            if "kablo" in ad_low:
                vendors_pool = VENDORS_CATALOG["kablo"]
            elif "box" in ad_low or "junction" in ad_low:
                vendors_pool = VENDORS_CATALOG["box"]
            elif "tava" in ad_low or "support" in ad_low:
                vendors_pool = VENDORS_CATALOG["tava"]
            elif "accuload" in ad_low or "enstrüman" in ad_low or "sayaç" in ad_low:
                vendors_pool = VENDORS_CATALOG["enstruman"]
            else:
                vendors_pool = VENDORS_CATALOG["genel"]

            # Alternatif fiyat teklifleri
            teklifler = []
            for v in vendors_pool:
                v_birim = round(baz_birim_maliyet * v["factor"], 2)
                teklifler.append({
                    "tedarikci": v["vendor"],
                    "birim_fiyat": v_birim,
                    "toplam": round(v_birim * mik, 2)
                })

            # En ucuz teklifi veren tedarikçiyi bul
            en_ucuz = min(teklifler, key=lambda x: x["birim_fiyat"])
            
            satir_liste_tutari = round(b_fiyat * mik, 2)
            satir_en_iyi_tutari = en_ucuz["toplam"]

            toplam_liste += satir_liste_tutari
            en_iyi_toplam += satir_en_iyi_tutari

            yeni_matris.append({
                "id": idx,
                "malzeme_adi": ad,
                "miktar": mik,
                "miktar_str": f"{int(mik) if mik.is_integer() else mik} {birim}",
                "birim": birim,
                "liste_birim_fiyat": b_fiyat,
                "en_iyi_tedarikci": en_ucuz["tedarikci"],
                "en_dusuk_birim": en_ucuz["birim_fiyat"],
                "en_dusuk_birim_str": self._para_formatla(en_ucuz["birim_fiyat"]),
                "satir_toplam": satir_en_iyi_tutari,
                "satir_toplam_str": self._para_formatla(satir_en_iyi_tutari),
                "tedarikci_secenekleri": teklifler,
                "secilen_tedarikci": en_ucuz["tedarikci"],
            })

        self.karsilastirma_matrisi = yeni_matris
        self.toplam_liste_fiyati = round(toplam_liste, 2)
        self.en_iyi_sepet_toplami = round(en_iyi_toplam, 2)
        self.elde_edilen_tasarruf = max(0.0, round(self.toplam_liste_fiyati - self.en_iyi_sepet_toplami, 2))
        
        if self.toplam_liste_fiyati > 0:
            oran = (self.elde_edilen_tasarruf / self.toplam_liste_fiyati) * 100
            self.tasarruf_orani_str = f"%{oran:.1f}"
        else:
            self.tasarruf_orani_str = "%0.0"

    # =========================================================================
    # TEDARİKÇİ DEĞİŞTİRME VE SEPETİ UYGULAMA İŞLEMLERİ
    # =========================================================================
    def select_vendor_for_item(self, item_id: int, vendor_name: str):
        """Kullanıcı tabloda belirli bir kalem için farklı bir tedarikçi seçerse çalışır."""
        matris = list(self.karsilastirma_matrisi)
        if 0 <= item_id < len(matris):
            secili_kalem = dict(matris[item_id])
            for opt in secili_kalem.get("tedarikci_secenekleri", []):
                if opt["tedarikci"] == vendor_name:
                    secili_kalem["secilen_tedarikci"] = vendor_name
                    secili_kalem["en_iyi_tedarikci"] = vendor_name
                    secili_kalem["en_dusuk_birim"] = opt["birim_fiyat"]
                    secili_kalem["en_dusuk_birim_str"] = self._para_formatla(opt["birim_fiyat"])
                    secili_kalem["satir_toplam"] = opt["toplam"]
                    secili_kalem["satir_toplam_str"] = self._para_formatla(opt["toplam"])
                    break
            matris[item_id] = secili_kalem
            self.karsilastirma_matrisi = matris

            # Toplamları yeniden hesapla
            yeni_sepet_toplami = sum(k["satir_toplam"] for k in self.karsilastirma_matrisi)
            self.en_iyi_sepet_toplami = round(yeni_sepet_toplami, 2)
            self.elde_edilen_tasarruf = max(0.0, round(self.toplam_liste_fiyati - self.en_iyi_sepet_toplami, 2))

    async def en_iyi_sepeti_teklife_uygula(self):
        """Optimize edilen sepet maliyetlerini teklifin SQLite veritabanı kaydına yazar."""
        if not self.secilen_teklif_kodu:
            yield rx.toast.error("Lütfen önce bir teklif seçin.", position="top-right")
            return

        teklif = get_teklif_by_kod(self.secilen_teklif_kodu)
        if not teklif:
            yield rx.toast.error("Teklif veritabanında bulunamadı.", position="top-right")
            return

        # Teklif kalemlerinin maliyetlerini optimize sepetle güncelle
        guncel_kalemler = teklif.get("kalemler", [])
        for i, k in enumerate(guncel_kalemler):
            if i < len(self.karsilastirma_matrisi):
                opt_item = self.karsilastirma_matrisi[i]
                k["birim_maliyet"] = opt_item["en_dusuk_birim"]
                k["toplam_maliyet"] = opt_item["satir_toplam"]
                k["secilen_tedarikci"] = opt_item["secilen_tedarikci"]

        teklif["kalemler"] = guncel_kalemler
        teklif["maliyet_toplam"] = self.en_iyi_sepet_toplami
        teklif["maliyet_try"] = self.en_iyi_sepet_toplami

        try:
            save_teklif_to_db(teklif)
            yield rx.toast.success(
                f"'{self.secilen_teklif_kodu}' için en iyi tedarikçi sepet maliyetleri ({self._para_formatla(self.en_iyi_sepet_toplami)}) teklife başarıyla işlendi!",
                position="top-right"
            )
        except Exception as e:
            yield rx.toast.error(f"Kayıt güncellenirken hata oluştu: {str(e)}", position="top-right")

    # =========================================================================
    # YARDIMCI METOTLAR
    # =========================================================================
    def _para_formatla(self, val: float) -> str:
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" {self.para_birimi_sembol}"

    def _sifirla_ozet(self):
        self.toplam_liste_fiyati = 0.0
        self.en_iyi_sepet_toplami = 0.0
        self.elde_edilen_tasarruf = 0.0
        self.tasarruf_orani_str = "%0.0"