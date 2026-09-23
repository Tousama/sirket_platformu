import reflex as rx
import os
import re
from typing import List, Dict, Any
from io import BytesIO

from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB

from .services.parsers import extract_excel_full_with_cost_sheets, extract_pdf_full
from .services.tcmb import get_tcmb_kurlar


class QuoteUploadState(rx.State):
    has_file: bool = False
    dosya_adi: str = ""
    teklif_kodu: str = ""
    musteri: str = ""
    konu: str = ""
    sorumlu: str = "Muhammed Güner"
    
    # TCMB kurları dinamik başlatılır
    _kurlar = get_tcmb_kurlar()
    kur_usd: float = _kurlar.get("USD", 48.7479)
    kur_eur: float = _kurlar.get("EUR", 55.9390)
    
    toplam_val: float = 0.0
    toplam_str: str = "0,00 ₺"
    
    maliyet_val: float = 0.0
    maliyet_str: str = "0,00 ₺"
    kar_marji_str: str = "%0.0"

    # Kalem listesi
    kalemler: List[Dict[str, Any]] = []

    async def handle_upload(self, files: List[rx.UploadFile]):
        """Yüklenen gerçek PDF veya Excel dosyasını parser ile okur."""
        if not files:
            return

        file = files[0]
        self.dosya_adi = file.filename
        upload_data = await file.read()
        file_stream = BytesIO(upload_data)
        file_stream.name = file.filename

        fn_lower = file.filename.lower()
        sonuc = {}

        try:
            if fn_lower.endswith((".xlsx", ".xls")):
                sonuc = extract_excel_full_with_cost_sheets(file_stream, self.kur_usd, self.kur_eur)
            elif fn_lower.endswith(".pdf"):
                sonuc = extract_pdf_full(file_stream)
        except Exception as e:
            return rx.toast.error(f"Dosya ayrıştırılırken hata oluştu: {str(e)}", position="top-right")

        # Üst bilgileri aktar
        ham_ad = os.path.splitext(file.filename)[0]
        dosya_adi_konu = re.sub(r"^(?:PT)?\d+[\-_]?", "", ham_ad, flags=re.IGNORECASE).replace("-", " ").replace("_", " ").strip()
        
        self.teklif_kodu = str(sonuc.get("teklif_kodu") or "").strip()
        if not self.teklif_kodu:
            m_pt = re.search(r"PT\d+", ham_ad, re.IGNORECASE)
            self.teklif_kodu = m_pt.group(0).upper() if m_pt else "PT2026092301"

        # Müşteri tespiti
        mus = str(sonuc.get("musteri") or "").strip()
        if not mus or mus == "-":
            ham_upper = ham_ad.upper()
            if "SHELL" in ham_upper:
                mus = "SHELL & TURCAS PETROL A.Ş. - DERİNCE" if "DERİNCE" in ham_upper or "DERINCE" in ham_upper else "SHELL & TURCAS PETROL A.Ş."
            elif "OMC" in ham_upper:
                mus = "OMC Sıvı Depolama Terminali"
            elif "AVES" in ham_upper:
                mus = "AVES ENERJİ YAĞ VE GIDA SANAYİ A.Ş."
            elif "TÜPRAŞ" in ham_upper or "TUPRAS" in ham_upper:
                mus = "TÜRKİYE PETROL RAFİNERİLERİ A.Ş."
            else:
                mus = "PetroTek Müşterisi"
        self.musteri = mus

        self.konu = str(sonuc.get("konu") or "").strip() or dosya_adi_konu
        self.sorumlu = str(sonuc.get("muhendis") or "").strip() or "Muhammed Güner"

        # Kalemleri al
        parsed_kalemler = sonuc.get("kalemler", [])
        self.kalemler = []
        for idx, k in enumerate(parsed_kalemler):
            mik = float(k.get("miktar", 1.0))
            b_sat = float(k.get("birim_satis", 0.0) or k.get("birim_fiyat", 0.0))
            b_mal = float(k.get("birim_maliyet", 0.0))
            pb = str(k.get("para_birimi", "TRY")).upper()
            
            toplam_sat = round(mik * b_sat, 2)
            self.kalemler.append({
                "id": idx + 1,
                "malzeme_adi": k.get("malzeme_adi", f"Kalem {idx+1}"),
                "miktar": mik,
                "birim": k.get("birim", "Adet"),
                "birim_satis": b_sat,
                "birim_satis_str": f"{b_sat:,.2f}",
                "birim_maliyet": b_mal,
                "birim_maliyet_str": str(b_mal) if b_mal > 0 else "0.0",
                "toplam_satis": toplam_sat,
                "toplam_satis_str": f"{toplam_sat:,.2f}",
                "para_birimi": pb,
            })

        self.has_file = True
        self._recalculate_totals()

        return rx.toast.success(
            f"'{file.filename}' başarıyla okundu! {len(self.kalemler)} kalem tespit edildi.",
            position="top-right"
        )

    def update_item_maliyet(self, item_id: int, val: str):
        """Kullanıcı tablodan kalemin birim maliyetini güncellediğinde çalışır."""
        try:
            clean = val.replace("₺", "").replace(" ", "").replace(",", ".")
            new_cost = float(clean) if clean else 0.0
        except ValueError:
            new_cost = 0.0

        for k in self.kalemler:
            if k["id"] == item_id:
                k["birim_maliyet"] = new_cost
                k["birim_maliyet_str"] = val
                break

        self._recalculate_totals()

    def _recalculate_totals(self):
        tot_sale = 0.0
        tot_cost = 0.0

        for k in self.kalemler:
            pb = k["para_birimi"]
            rate = self.kur_eur if pb == "EUR" else (self.kur_usd if pb == "USD" else 1.0)
            mik = float(k["miktar"])
            
            tot_sale += (mik * float(k["birim_satis"]) * rate)
            tot_cost += (mik * float(k["birim_maliyet"]) * rate)

        self.toplam_val = round(tot_sale, 2)
        self.maliyet_val = round(tot_cost, 2)
        self.toplam_str = f"{self.toplam_val:,.2f} ₺"
        self.maliyet_str = f"{self.maliyet_val:,.2f} ₺"

        marj = ((tot_sale - tot_cost) / tot_sale * 100) if tot_sale > 0 else 0.0
        self.kar_marji_str = f"%{marj:.1f}"

    def simule_et(self):
        """Görseldeki Shell Derince örneğini birebir simüle eder."""
        self.dosya_adi = "SHELL DERİNCE SCULLY TEMİNİ VE DEĞİŞİMİ.xlsx"
        self.teklif_kodu = "PT202609201558"
        self.musteri = "SHELL & TURCAS PETROL A.Ş. - DERİNCE"
        self.konu = "SHELL DERİNCE SCULLY TEMİNİ VE DEĞİŞİMİ"
        self.sorumlu = "Muhammed Güner"

        self.kalemler = [
            {
                "id": 1,
                "malzeme_adi": "Scully Optik Sıvı Taşma Sensörü & Soket Seti",
                "miktar": 4.0,
                "birim": "Adet",
                "birim_satis": 28500.00,
                "birim_satis_str": "28,500.00",
                "birim_maliyet": 19200.00,
                "birim_maliyet_str": "19200.00",
                "toplam_satis": 114000.00,
                "toplam_satis_str": "114,000.00",
                "para_birimi": "TRY",
            },
            {
                "id": 2,
                "malzeme_adi": "Scully Topraklama Pensi ve Spiral Kablo (Ex-Proof)",
                "miktar": 2.0,
                "birim": "Set",
                "birim_satis": 22500.00,
                "birim_satis_str": "22,500.00",
                "birim_maliyet": 14500.00,
                "birim_maliyet_str": "14500.00",
                "toplam_satis": 45000.00,
                "toplam_satis_str": "45,000.00",
                "para_birimi": "TRY",
            },
            {
                "id": 3,
                "malzeme_adi": "Saha Demontaj, Montaj, Test ve Devreye Alma Hizmeti",
                "miktar": 1.0,
                "birim": "Hizmet",
                "birim_satis": 86000.00,
                "birim_satis_str": "86,000.00",
                "birim_maliyet": 42000.00,
                "birim_maliyet_str": "42000.00",
                "toplam_satis": 86000.00,
                "toplam_satis_str": "86,000.00",
                "para_birimi": "TRY",
            },
        ]
        self.has_file = True
        self._recalculate_totals()

        return rx.toast.info("Shell Derince Scully teklifi ve kalemleri yüklendi.", position="top-right")

    async def portala_kaydet(self):
        """Tüm kalemleri ve hesaplanan maliyetleri Dashboard ve VERSIONS_DB'ye işler."""
        if not self.teklif_kodu or not self.musteri:
            return rx.toast.error("Teklif kodu veya müşteri adı eksik!", position="top-right")

        marj = round(((self.toplam_val - self.maliyet_val) / self.toplam_val * 100), 1) if self.toplam_val > 0 else 0.0

        yeni_kayit = {
            "kod": self.teklif_kodu,
            "musteri": self.musteri,
            "konu": self.konu,
            "sorumlu": self.sorumlu,
            "durum": "Hazırlanıyor",
            "maliyet_try": self.maliyet_val,
            "satis_try": self.toplam_val,
            "marj": marj,
            "tarih": "2026-09-23",
            "yaslanma_gun": 0,
            "para_birimi": "TRY",
        }

        dash_state = await self.get_state(DashboardState)
        if hasattr(dash_state, "raw_quotes"):
            dash_state.raw_quotes.insert(0, yeni_kayit)

        # Kalemleri VERSIONS_DB formatında hazırla
        db_items = {}
        for k in self.kalemler:
            db_items[k["malzeme_adi"]] = {
                "miktar": float(k["miktar"]),
                "birim": k["birim"],
                "birim_maliyet": float(k["birim_maliyet"]),
                "birim_satis": float(k["birim_satis"]),
            }

        VERSIONS_DB[f"{self.teklif_kodu} (Rev 0 - Orijinal)"] = {
            "musteri": self.musteri,
            "konu": self.konu,
            "sorumlu": self.sorumlu,
            "maliyet": self.maliyet_val,
            "satis": self.toplam_val,
            "items": db_items,
        }

        return rx.toast.success(
            f"'{self.teklif_kodu}' teklifi {len(self.kalemler)} kalemiyle birlikte portala kaydedildi!",
            position="top-right"
        )