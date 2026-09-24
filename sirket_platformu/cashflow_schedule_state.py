import reflex as rx
from typing import List, Dict, Any
from .dashboard_state import DashboardState
from .shared_quotes import SHARED_QUOTES

try:
    from .services.db_service import get_all_teklifler_from_db
except ImportError:
    try:
        from services.db_service import get_all_teklifler_from_db
    except ImportError:
        get_all_teklifler_from_db = None


def format_para(val: float) -> str:
    """Türkçe para formatı"""
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


class CashflowScheduleState(rx.State):
    currency: str = "TRY (₺)"
    
    # Proje / Teklif Seçim Alanları
    proje_secenekleri: List[str] = []
    secilen_proje: str = ""
    _quotes_map: Dict[str, Any] = {}

    # KPI Değerleri
    kritik_yol_termin: str = "6 Hafta"
    toplam_proje_suresi: str = "8 Hafta"
    toplam_satis_str: str = "0,00 ₺"
    en_dusuk_kasa_str: str = "0,00 ₺"
    kasa_durum_metni: str = "Hesaplanıyor..."
    kasa_durum_renk: str = "#34d399"

    # S-Curve Verisi
    curve_data: List[Dict[str, Any]] = []

    def set_currency(self, val: Any):
        if isinstance(val, list) and len(val) > 0:
            self.currency = str(val[0])
        else:
            self.currency = str(val)

    async def on_load(self):
        """Dashboard ve DB'deki teklifleri yükler ve ilk teklifi simüle eder."""
        await self.load_projects()

    async def load_projects(self):
        dash_state = await self.get_state(DashboardState)
        raw_list = getattr(dash_state, "raw_quotes", [])

        options = []
        self._quotes_map = {}

        # 1. Dashboard Portföyü
        for q in raw_list:
            kod = q.get("kod") or q.get("teklif_kodu", "")
            musteri = q.get("musteri", "-")
            if kod:
                label = f"{kod} | {musteri}"
                if label not in options:
                    options.append(label)
                    self._quotes_map[label] = q

        # 2. DB'deki Kayıtlar
        if get_all_teklifler_from_db:
            try:
                db_quotes = get_all_teklifler_from_db()
                for q in db_quotes:
                    kod = q.get("kod") or q.get("teklif_kodu", "")
                    musteri = q.get("musteri", "-")
                    if kod:
                        label = f"{kod} | {musteri}"
                        if label not in options:
                            options.append(label)
                            self._quotes_map[label] = q
            except Exception:
                pass

        if not options:
            options = ["PT202600129 | PetroTek"]

        self.proje_secenekleri = options
        if not self.secilen_proje or self.secilen_proje not in options:
            self.secilen_proje = options[0]

        self.hesapla_cashflow()

    def set_secilen_proje(self, val: str):
        self.secilen_proje = val
        self.hesapla_cashflow()

    def hesapla_cashflow(self):
        """Seçilen projenin satış ve maliyetine göre nakit akışını ve S-Curve'ü yeniden hesaplar."""
        quote = self._quotes_map.get(self.secilen_proje, {})
        
        kod = quote.get("kod") or quote.get("teklif_kodu", "")
        satis = float(quote.get("satis_try") or quote.get("satis_orijinal") or 0.0)
        maliyet = float(quote.get("maliyet_try") or 0.0)

        # Eğer kalem listesi varsa toplam maliyeti kalemlerden toparla
        kalemler = quote.get("kalemler", [])
        if not kalemler and kod in SHARED_QUOTES:
            kalemler = SHARED_QUOTES[kod].get("kalemler", [])

        if kalemler and maliyet == 0.0:
            maliyet = sum(float(k.get("birim_maliyet", 0.0)) * float(k.get("miktar", 1.0)) for k in kalemler)

        # Maliyet sıfırsa makul bir mühendislik marjı (%65 maliyet) varsay
        if maliyet == 0.0 and satis > 0:
            maliyet = round(satis * 0.65, 2)
        elif satis == 0.0 and maliyet > 0:
            satis = round(maliyet * 1.30, 2)

        self.toplam_satis_str = format_para(satis)

        # Hakediş ve Harcama Kümülatif Eğrisi (S-Curve)
        # Tahsilat Dağılımı: 1-4. Hafta Avans (%30), 5-6. Hafta Ara Hakediş (%70), 7-8. Hafta Kabul (%100)
        t_avans = round(satis * 0.30, 2)
        t_ara = round(satis * 0.70, 2)
        t_tam = round(satis, 2)

        # Harcama Dağılımı: 1-3. Hafta Ön Sipariş (%38), 4-5. Hafta Teslimat (%80), 6-8. Hafta Montaj/Kabul (%100)
        h_on = round(maliyet * 0.38, 2)
        h_teslim = round(maliyet * 0.80, 2)
        h_tam = round(maliyet, 2)

        self.curve_data = [
            {"hafta": "1. Hafta", "kumulatif_tahsilat": t_avans, "kumulatif_harcama": h_on, "net_kasa": t_avans - h_on},
            {"hafta": "2. Hafta", "kumulatif_tahsilat": t_avans, "kumulatif_harcama": h_on, "net_kasa": t_avans - h_on},
            {"hafta": "3. Hafta", "kumulatif_tahsilat": t_avans, "kumulatif_harcama": h_on, "net_kasa": t_avans - h_on},
            {"hafta": "4. Hafta", "kumulatif_tahsilat": t_avans, "kumulatif_harcama": h_teslim, "net_kasa": t_avans - h_teslim},
            {"hafta": "5. Hafta", "kumulatif_tahsilat": t_ara, "kumulatif_harcama": h_teslim, "net_kasa": t_ara - h_teslim},
            {"hafta": "6. Hafta", "kumulatif_tahsilat": t_ara, "kumulatif_harcama": h_tam, "net_kasa": t_ara - h_tam},
            {"hafta": "7. Hafta", "kumulatif_tahsilat": t_tam, "kumulatif_harcama": h_tam, "net_kasa": t_tam - h_tam},
            {"hafta": "8. Hafta", "kumulatif_tahsilat": t_tam, "kumulatif_harcama": h_tam, "net_kasa": t_tam - h_tam},
        ]

        # En Düşük Kasa Bakiyesi Analizi
        min_kasa = min(row["net_kasa"] for row in self.curve_data) if self.curve_data else 0.0
        if min_kasa >= 0:
            self.en_dusuk_kasa_str = "+" + format_para(min_kasa)
            self.kasa_durum_metni = "Kendi kendini finanse ediyor"
            self.kasa_durum_renk = "#34d399"
        else:
            self.en_dusuk_kasa_str = format_para(min_kasa)
            self.kasa_durum_metni = "Finansman açığı (Kredi/Özsermaye gerekli)"
            self.kasa_durum_renk = "#f87171"