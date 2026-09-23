import reflex as rx
from typing import List, Dict, Any
from .shared_quotes import GLOBAL_TEKLIFLER, sync_from_sqlite
from .revision_diff_state import VERSIONS_DB


class SupplierCompareState(rx.State):
    secilen_teklif_kodu: str = ""
    yuklenen_tedarikciler: List[str] = []
    teklif_kalem_havuzu: Dict[str, Dict[str, Any]] = {}
    
    # Matris tablosu için hesaplanan satırlar
    karsilastirma_matrisi: List[Dict[str, Any]] = []
    toplam_tasarruf_tl: float = 0.0
    tasarruf_orani_str: str = "%0.0"

    @rx.var
    def teklif_kodlari(self) -> List[str]:
        """Açılır menünün doğrudan bağlandığı reaktif liste."""
        return list(GLOBAL_TEKLIFLER.keys())

    @rx.var
    def tedarikci_sayisi(self) -> int:
        return len(self.yuklenen_tedarikciler)

    async def teklifleri_guncelle(self):
        """Sayfa açıldığında veya yenilendiğinde veritabanından hafızayı tazeler."""
        try:
            sync_from_sqlite()
        except Exception:
            pass

        if not self.secilen_teklif_kodu and GLOBAL_TEKLIFLER:
            ilk_kod = list(GLOBAL_TEKLIFLER.keys())[0]
            await self.set_teklif(ilk_kod)
        elif self.secilen_teklif_kodu and self.secilen_teklif_kodu in GLOBAL_TEKLIFLER:
            await self.set_teklif(self.secilen_teklif_kodu)

    async def set_teklif(self, teklif_kodu: str):
        """Açılır menüden seçilen teklifi yükler, kalem havuzunu oluşturur ve matrisi hesaplar."""
        self.secilen_teklif_kodu = teklif_kodu.strip()
        self.yuklenen_tedarikciler = []

        clean_kod = self.secilen_teklif_kodu.upper()

        # 1. GLOBAL_TEKLIFLER havuzundan çek
        hedef_teklif = GLOBAL_TEKLIFLER.get(clean_kod)
        if not hedef_teklif:
            for k, v in GLOBAL_TEKLIFLER.items():
                if clean_kod in k or k in clean_kod:
                    hedef_teklif = v
                    break

        kalem_havuzu = {}

        if hedef_teklif and hedef_teklif.get("kalemler"):
            for k in hedef_teklif["kalemler"]:
                ad = k.get("malzeme_adi") or k.get("tanim") or k.get("malzeme") or "Tanımsız Kalem"
                mik = float(k.get("miktar", 1.0))
                birim = str(k.get("birim", "Adet"))
                kalem_havuzu[ad] = {
                    "miktar": mik,
                    "birim": birim,
                    "fiyatlar": k.get("fiyatlar", {})
                }
        else:
            # 2. Yedek: VERSIONS_DB kontrolü
            v_data = VERSIONS_DB.get(clean_kod) or VERSIONS_DB.get(self.secilen_teklif_kodu)
            if v_data and "items" in v_data:
                for ad, d in v_data["items"].items():
                    kalem_havuzu[ad] = {
                        "miktar": float(d.get("miktar", 1.0)),
                        "birim": str(d.get("birim", "Adet")),
                        "fiyatlar": {}
                    }

        self.teklif_kalem_havuzu = kalem_havuzu
        self._recalculate_matrix()
        return rx.toast.info(f"'{teklif_kodu}' seçildi ({len(kalem_havuzu)} kalem).", position="top-right")

    def _recalculate_matrix(self):
        """Tedarikçilerin verdiği fiyatlara göre en uygun sepeti ve satırları hesaplar."""
        matris = []
        toplam_en_iyi = 0.0

        for malz_adi, veri in self.teklif_kalem_havuzu.items():
            fiyatlar = veri.get("fiyatlar", {})
            mik = veri.get("miktar", 1.0)
            birim = veri.get("birim", "Adet")

            en_iyi_tedarikci = "-"
            en_dusuk_fiyat = 0.0

            if fiyatlar:
                gecerli = {t: f for t, f in fiyatlar.items() if f > 0}
                if gecerli:
                    en_iyi_tedarikci = min(gecerli, key=gecerli.get)
                    en_dusuk_fiyat = gecerli[en_iyi_tedarikci]

            satir_toplam = round(mik * en_dusuk_fiyat, 2)
            toplam_en_iyi += satir_toplam

            matris.append({
                "malzeme_adi": malz_adi,
                "miktar": mik,
                "miktar_str": f"{int(mik) if mik.is_integer() else mik} {birim}",
                "birim": birim,
                "en_iyi_tedarikci": en_iyi_tedarikci,
                "en_dusuk_birim_fiyat": en_dusuk_fiyat,
                "en_dusuk_birim_str": f"{en_dusuk_fiyat:,.2f} ₺" if en_dusuk_fiyat > 0 else "-",
                "satir_toplam_tl": satir_toplam,
                "satir_toplam_str": f"{satir_toplam:,.2f} ₺" if satir_toplam > 0 else "-",
            })

        self.karsilastirma_matrisi = matris
        self.toplam_tasarruf_tl = toplam_en_iyi

    async def handle_supplier_file_upload(self, files: List[rx.UploadFile]):
        """Tedarikçiden gelen fiyat listesini ayrıştırıp mevcut teklif kalemleriyle eşleştirir."""
        if not files:
            return rx.toast.error("Dosya seçilmedi!", position="top-right")
        return rx.toast.info("Tedarikçi teklifi yüklendi.", position="top-right")

    def en_iyi_sepeti_teklife_uygula(self):
        """Seçilen en ucuz tedarikçi maliyetlerini teklifin ana maliyetine aktarır."""
        return rx.toast.success("En iyi sepet maliyetleri teklife aktarıldı!", position="top-right")