import reflex as rx
from typing import List, Dict, Any, Union

try:
    from .services.db_service import get_all_teklifler_from_db, upsert_teklif_kalemi, get_teklif_by_kod
except ImportError:
    get_all_teklifler_from_db = None
    upsert_teklif_kalemi = None
    get_teklif_by_kod = None


class LaborEngineState(rx.State):
    # Teklif Seçimi
    referans_secenekleri: List[str] = [
        "PT202600137 | Emre DÖNMEZ | Dolum Adası AC/DC Box Revizyonu",
        "PT202600164 | Eti Maden İşletmeleri | Buhar Kazanına Ait DCS Sisteminin Yıllık Bakımı",
        "PT202609201555 Deneme | Shell | Enstruman Temini",
        "PT202609191725-Rev1 | OMC | LP Enstrumantasyon (Rev1)",
        "PT202609191650 | OMC | Radar & Pressure Gauge Temini",
        "PT2026088103 | Doğukan KILIÇ | AVES GÜNEY Motorin Pompası Scully",
        "PT2026088039 | GİZEM AKYILDIZ | DERİNCE SHELL TERMİNALİ UPS BAĞLANTISI",
    ]
    secilen_teklif: str = "PT202600137 | Emre DÖNMEZ | Dolum Adası AC/DC Box Revizyonu"

    # Para Birimi Seçimi
    para_birimi: str = "TRY"
    kur_usd: float = 38.50
    kur_eur: float = 42.00

    # 1. Metraj & Ekipman Sayıları (Norm Tabanı v2.4)
    kablo_tava_m: float = 50.0
    kablo_cekim_m: float = 250.0
    gland_baglanti_ad: float = 16.0
    enstruman_test_ad: float = 4.0
    saha_panosu_ad: float = 2.0
    ilave_demontaj_as: float = 16.0

    # 2. Ekip & Mobilizasyon
    teknisyen_sayisi: float = 2.0
    supervizor_gun: float = 2.0
    harcirah_gun_tl: float = 750.0
    otel_gece_tl: float = 2500.0
    ulasim_arac_tl: float = 6500.0

    # Elle Ayarlanabilir Kâr Oranı (%) — MALİYET ÜZERİNE (markup)
    custom_margin_percent: float = 50.0

    # BOM'a Eklenecek Hizmet Adı
    hizmet_aciklamasi: str = "Gebze Terminali Ada-5 AC/DC Box, Zırhlı Kablo Çekimi, Tava ve TAS Devreye Alma İşçiliği"

    # Onay Modalı Durumu
    onay_modal_acik: bool = False
    onay_baslik: str = ""
    onay_mesaj: str = ""

    # Dahili Teklif Veritabanı Önbelleği
    _db_quotes_cache: Dict[str, Dict[str, Any]] = {}

    # Setters
    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val
        self.sync_with_selected_quote()

    def set_para_birimi(self, val: Union[str, List[str]]):
        if isinstance(val, list):
            self.para_birimi = val[0] if val else "TRY"
        else:
            self.para_birimi = val

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
        """Kâr oranı % — MALİYET ÜZERİNE (markup)."""
        try:
            m = float(val)
            if m > 500.0:
                m = 500.0
            elif m < 0.0:
                m = 0.0
            self.custom_margin_percent = round(m, 1)
        except ValueError:
            pass

    def set_onay_modal_acik(self, val=False):
        """
        Modal açma/kapama. alert_dialog çağrısında bool veya liste gelebilir.
        Reflex event handler olarak çağrılabilir (alt çizgi YOK).
        """
        try:
            if isinstance(val, list):
                val = val[0] if val else False
            self.onay_modal_acik = bool(val)
        except Exception:
            self.onay_modal_acik = False

    async def on_load(self):
        """Veritabanındaki güncel teklifleri listeye yükler."""
        if get_all_teklifler_from_db:
            try:
                db_quotes = get_all_teklifler_from_db()
                options = []
                self._db_quotes_cache = {}
                for q in db_quotes:
                    kod = q.get("kod", "")
                    musteri = q.get("musteri", "-")
                    konu = q.get("konu", "-")
                    label = f"{kod} | {musteri} | {konu}"
                    options.append(label)
                    self._db_quotes_cache[label] = q
                if options:
                    self.referans_secenekleri = options
                    if self.secilen_teklif not in options:
                        self.secilen_teklif = options[0]
                    self.sync_with_selected_quote()
            except Exception:
                pass

    def sync_with_selected_quote(self):
        clean_code = self.secilen_teklif.split("|")[0].strip()
        t_low = self.secilen_teklif.lower()

        if "PT202600164" in clean_code or "dcs" in t_low or "buhar kazanı" in t_low:
            self.kablo_tava_m = 0.0
            self.kablo_cekim_m = 0.0
            self.gland_baglanti_ad = 0.0
            self.saha_panosu_ad = 1.0
            self.enstruman_test_ad = 8.0
            self.ilave_demontaj_as = 0.0
            self.teknisyen_sayisi = 1.0
            self.supervizor_gun = 5.0
            self.ulasim_arac_tl = 8500.0
            self.hizmet_aciklamasi = "GE&NEXUS DCS Kontrol Sistemi 1 Yıllık Periyodik Genel Bakım, Yedekleme ve Uzaktan Destek Hizmeti"
            return

        if "PT202600137" in clean_code or "dolum adası" in t_low or "junction box" in t_low:
            self.kablo_tava_m = 50.0
            self.kablo_cekim_m = 250.0
            self.gland_baglanti_ad = 16.0
            self.saha_panosu_ad = 2.0
            self.enstruman_test_ad = 4.0
            self.ilave_demontaj_as = 16.0
            self.teknisyen_sayisi = 2.0
            self.supervizor_gun = 2.0
            self.ulasim_arac_tl = 6500.0
            self.hizmet_aciklamasi = "Gebze Terminali Ada-5 AC/DC Box, Zırhlı Kablo Çekimi, Tava ve TAS Devreye Alma İşçiliği"
            return

        selected_data = self._db_quotes_cache.get(self.secilen_teklif)
        if selected_data:
            kalemler = selected_data.get("kalemler", [])
            tot_kablo = 0.0
            tot_gland = 0.0
            tot_enstruman = 0.0
            tot_pano = 0.0

            for k in kalemler:
                tanim = (k.get("malzeme_adi") or k.get("tanim", "")).lower()
                miktar = float(k.get("miktar", 1.0))

                if "kablo" in tanim and "gland" not in tanim and "rakor" not in tanim:
                    tot_kablo += miktar if miktar > 10 else 100.0
                elif "gland" in tanim or "rakor" in tanim:
                    tot_gland += miktar
                elif any(x in tanim for x in ["transmitter", "şalter", "switch", "radar", "gauge", "enstrüman"]):
                    tot_enstruman += miktar
                elif any(x in tanim for x in ["pano", "box", "kutu"]):
                    tot_pano += miktar

            self.kablo_cekim_m = tot_kablo if tot_kablo > 0 else 150.0
            self.kablo_tava_m = round(self.kablo_cekim_m * 0.20, 1)
            self.gland_baglanti_ad = tot_gland if tot_gland > 0 else 8.0
            self.enstruman_test_ad = tot_enstruman if tot_enstruman > 0 else 2.0
            self.saha_panosu_ad = tot_pano if tot_pano > 0 else 1.0
            self.ilave_demontaj_as = 8.0
            self.teknisyen_sayisi = 2.0
            self.supervizor_gun = 2.0
            self.ulasim_arac_tl = 6000.0
            self.hizmet_aciklamasi = f"{selected_data.get('konu', 'Saha Montaj')} Saha İşçilik ve Devreye Alma Hizmeti"

    def sync_from_scope(self, proje_tipi: str, scope_text: str):
        t_low = scope_text.lower()
        if "dcs" in t_low or "ge&nexus" in t_low or "periyodik bakım" in t_low:
            self.kablo_tava_m = 0.0
            self.kablo_cekim_m = 0.0
            self.gland_baglanti_ad = 0.0
            self.saha_panosu_ad = 1.0
            self.enstruman_test_ad = 8.0
            self.ilave_demontaj_as = 0.0
            self.teknisyen_sayisi = 1.0
            self.supervizor_gun = 5.0
            self.ulasim_arac_tl = 8500.0
            self.hizmet_aciklamasi = "DCS Kontrol Sistemi Yıllık Periyodik Bakım, Yedekleme ve 10 Saat Uzaktan Destek Hizmeti"
        elif "dolum adası" in t_low or "junction box" in t_low or "kablo tesisatı" in t_low:
            self.kablo_tava_m = 50.0
            self.kablo_cekim_m = 250.0
            self.gland_baglanti_ad = 16.0
            self.saha_panosu_ad = 2.0
            self.enstruman_test_ad = 4.0
            self.ilave_demontaj_as = 16.0
            self.teknisyen_sayisi = 2.0
            self.supervizor_gun = 2.0
            self.ulasim_arac_tl = 6500.0
            self.hizmet_aciklamasi = "Gebze Terminali Ada-5 AC/DC Box, Zırhlı Kablo Çekimi, Tava ve TAS Devreye Alma İşçiliği"

    # --- DAHİLİ HESAPLAMALAR ---
    def _calc_teknisyen_as(self) -> float:
        return (self.kablo_tava_m * 0.40) + \
               (self.kablo_cekim_m * 0.16) + \
               (self.gland_baglanti_ad * 0.75) + \
               (self.saha_panosu_ad * 6.0) + \
               self.ilave_demontaj_as + \
               (self.enstruman_test_ad * 0.525)

    def _calc_muhendis_as(self) -> float:
        return (self.supervizor_gun * 8.0) + (self.enstruman_test_ad * 1.5)

    def _calc_saha_gun(self) -> float:
        crew = self.teknisyen_sayisi if self.teknisyen_sayisi > 0 else 1.0
        val = self._calc_teknisyen_as() / (crew * 8.0)
        if self.supervizor_gun > val:
            val = self.supervizor_gun
        return round(val, 1)

    def _calc_cost_total_raw(self) -> float:
        cost_tek = self._calc_teknisyen_as() * 450.0
        cost_muh = self._calc_muhendis_as() * 750.0
        gun = self._calc_saha_gun()
        crew = self.teknisyen_sayisi
        total_people = crew + 1.0
        rooms = (crew / 2.0) + 1.0

        harcirah = total_people * self.harcirah_gun_tl * gun
        konaklama = rooms * self.otel_gece_tl * gun
        return cost_tek + cost_muh + harcirah + konaklama + self.ulasim_arac_tl

    def _calc_price_multiplier(self) -> float:
        """MALİYET ÜZERİNE KÂR (markup) çarpanı."""
        m = self.custom_margin_percent / 100.0
        if m < 0.0:
            m = 0.0
        return 1.0 + m

    def _calc_currency_rate(self) -> float:
        if self.para_birimi == "USD":
            return self.kur_usd if self.kur_usd > 0 else 38.50
        elif self.para_birimi == "EUR":
            return self.kur_eur if self.kur_eur > 0 else 42.00
        return 1.0

    @staticmethod
    def _fmt(val: float) -> str:
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # --- REFLEX COMPUTED VARS ---
    @rx.var
    def teknisyen_as(self) -> float: return round(self._calc_teknisyen_as(), 1)

    @rx.var
    def muhendis_as(self) -> float: return round(self._calc_muhendis_as(), 1)

    @rx.var
    def tahmini_saha_suresi_gun(self) -> float: return self._calc_saha_gun()

    @rx.var
    def currency_symbol(self) -> str:
        if self.para_birimi == "USD":
            return "$"
        elif self.para_birimi == "EUR":
            return "€"
        return "₺"

    @rx.var
    def cost_teknisyen_str(self) -> str:
        val = (self._calc_teknisyen_as() * 450.0) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def price_teknisyen_str(self) -> str:
        val = ((self._calc_teknisyen_as() * 450.0) * self._calc_price_multiplier()) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def cost_muhendis_str(self) -> str:
        val = (self._calc_muhendis_as() * 750.0) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def price_muhendis_str(self) -> str:
        val = ((self._calc_muhendis_as() * 750.0) * self._calc_price_multiplier()) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def cost_mobilizasyon_str(self) -> str:
        cost_mob = self._calc_cost_total_raw() - (self._calc_teknisyen_as() * 450.0) - (self._calc_muhendis_as() * 750.0)
        val = cost_mob / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def price_mobilizasyon_str(self) -> str:
        cost_mob = self._calc_cost_total_raw() - (self._calc_teknisyen_as() * 450.0) - (self._calc_muhendis_as() * 750.0)
        val = (cost_mob * self._calc_price_multiplier()) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def cost_total_str(self) -> str:
        val = self._calc_cost_total_raw() / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def price_total_str(self) -> str:
        val = (self._calc_cost_total_raw() * self._calc_price_multiplier()) / self._calc_currency_rate()
        return f"{self._fmt(val)} {self.currency_symbol}"

    @rx.var
    def kar_marji_yuzde(self) -> float:
        return self.custom_margin_percent

    @rx.var
    def kar_tutari_tl(self) -> float:
        cost = self._calc_cost_total_raw()
        kar = cost * (self.custom_margin_percent / 100.0)
        return round(kar, 2)

    @rx.var
    def kar_tutari_display(self) -> float:
        return round(self.kar_tutari_tl / self._calc_currency_rate(), 2)

    @rx.var
    def kar_tutari_str(self) -> str:
        return f"{self._fmt(self.kar_tutari_display)} {self.currency_symbol}"

    # ---------------------------------------------------------------
    # BOM AKTARMA — Onay Mekanizmalı
    # ---------------------------------------------------------------
    def _mevcut_kalem_bul(self) -> dict | None:
        """Aynı hizmet adıyla kayıtlı bir kalem varsa döner."""
        clean_code = self.secilen_teklif.split("|")[0].strip()
        hizmet_adi = self.hizmet_aciklamasi.strip().lower()
        if not (clean_code and hizmet_adi):
            return None

        # Önce cache'ten dene
        selected_data = self._db_quotes_cache.get(self.secilen_teklif)
        kalemler = (selected_data or {}).get("kalemler", []) or []

        # Cache'te yoksa DB'den taze çek
        if not kalemler and get_teklif_by_kod:
            try:
                t = get_teklif_by_kod(clean_code)
                kalemler = t.get("kalemler", []) or []
            except Exception:
                kalemler = []

        for k in kalemler:
            ad = (k.get("malzeme_adi") or k.get("tanim") or "").strip().lower()
            if ad == hizmet_adi:
                return k
        return None

    def _gercek_aktar(self) -> Dict[str, Any]:
        """Senkron aktarım — sonuç dict döner. Toast çağıran taraf gösterir."""
        clean_code = self.secilen_teklif.split("|")[0].strip()
        hizmet_adi = self.hizmet_aciklamasi.strip()

        rate = self._calc_currency_rate()
        multiplier = self._calc_price_multiplier()
        cost_raw = self._calc_cost_total_raw()

        gorunen_satis = round(float((cost_raw * multiplier) / rate), 2)
        satis_tl = round(float(cost_raw * multiplier), 2)
        maliyet_tl = round(float(cost_raw), 2)

        try:
            if not upsert_teklif_kalemi:
                return {"success": False, "mesaj": "Teklif veritabanı servisi kullanılamıyor."}

            toplamlar = upsert_teklif_kalemi(
                teklif_kodu=clean_code,
                malzeme_adi=hizmet_adi,
                miktar=1.0,
                birim="Hizmet",
                birim_satis=satis_tl,
                birim_maliyet=maliyet_tl,
                para_birimi="TRY",
            )
            yeni_toplam_satis = toplamlar["satis_toplam"]
            yeni_toplam_maliyet = toplamlar["maliyet_toplam"]

            # Cache tazele
            refreshed = get_all_teklifler_from_db() if get_all_teklifler_from_db else []
            for quote in refreshed:
                if quote.get("kod") == clean_code:
                    self._db_quotes_cache[self.secilen_teklif] = quote
                    break

            return {
                "success": True,
                "mesaj": (
                    f"İşçilik eklendi: {self._fmt(gorunen_satis)} {self.currency_symbol}. "
                    f"Teklifin yeni toplamı: {self._fmt(yeni_toplam_satis)} ₺ "
                    f"(toplam maliyet: {self._fmt(yeni_toplam_maliyet)} ₺)"
                ),
            }
        except Exception as e:
            return {"success": False, "mesaj": f"BOM aktarımı yapılamadı: {str(e)}"}

    async def aktar_bom(self):
        """
        Butona basıldığında çağrılır.
        - Aynı isimli kalem YOKSA → doğrudan ekler.
        - Aynı isimli kalem VARSA → onay modalı açar, kullanıcı onaylamadan eklemez.
        """
        mevcut = self._mevcut_kalem_bul()

        if mevcut:
            # Onay iste
            mevcut_satis = float(mevcut.get("birim_satis", 0.0) or 0.0)
            mevcut_maliyet = float(mevcut.get("birim_maliyet", 0.0) or 0.0)

            # Yeni hesaplanan değerler
            cost_raw = self._calc_cost_total_raw()
            yeni_satis_tl = round(cost_raw * self._calc_price_multiplier(), 2)
            yeni_maliyet_tl = round(cost_raw, 2)

            self.onay_baslik = "⚠️ Kalem Zaten Var — Üzerine Yazılsın mı?"
            self.onay_mesaj = (
                f"Bu teklifte '{self.hizmet_aciklamasi[:70]}...' isimli bir kalem zaten kayıtlı.\n\n"
                f"Mevcut Satış: {self._fmt(mevcut_satis)} ₺\n"
                f"Yeni Satış: {self._fmt(yeni_satis_tl)} ₺\n\n"
                f"Mevcut Maliyet: {self._fmt(mevcut_maliyet)} ₺\n"
                f"Yeni Maliyet: {self._fmt(yeni_maliyet_tl)} ₺\n\n"
                f"Devam ederseniz mevcut kalem güncellenecek."
            )
            self.onay_modal_acik = True
            return

        # Yeni kalem → doğrudan ekle
        sonuc = self._gercek_aktar()

        # Dashboard'u tazele
        try:
            from .dashboard_state import DashboardState
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        if sonuc["success"]:
            yield rx.toast.success(sonuc["mesaj"], position="top-right")
        else:
            yield rx.toast.error(sonuc["mesaj"], position="top-right")

    async def onayli_aktar_bom(self):
        """Modal onaylandığında çağrılır."""
        self.onay_modal_acik = False
        sonuc = self._gercek_aktar()

        try:
            from .dashboard_state import DashboardState
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        if sonuc["success"]:
            yield rx.toast.success(sonuc["mesaj"], position="top-right")
        else:
            yield rx.toast.error(sonuc["mesaj"], position="top-right")