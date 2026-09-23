import reflex as rx
from typing import List, Dict, Any
from io import BytesIO
import pandas as pd
import re

from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB

try:
    from .services.tcmb import get_tcmb_kurlar
    from .services.parsers import parse_sayi
except ImportError:
    from services.tcmb import get_tcmb_kurlar
    from services.parsers import parse_sayi


class CostUploadState(rx.State):
    teklif_secenekleri: List[str] = [
        "PT202600149 - Beril TEKİN (Satış: 549.737,12 ₺)",
        "PT202609201555 Deneme - Shell (Satış: 349.890,00 ₺)",
        "PT202609191725 - OMC Sıvı Depolama (Satış: 513.679,94 ₺)",
        "PT2026088103 - AVES GÜNEY Motorin Pompası (Satış: 320.000,00 ₺)",
        "PT202600155 - Shell Derince Bakım (Satış: 46.200,00 ₺)",
    ]
    secilen_teklif: str = "PT202600149 - Beril TEKİN (Satış: 549.737,12 ₺)"

    dosya_adi: str = "Dosya seçilmedi"
    
    # Eşleşen kalemler listesi
    eslesen_kalemler: List[Dict[str, Any]] = []
    
    # Eşleşmeyen / Belirsiz kalemler listesi (Kullanıcıya sorulacaklar)
    eslesmeyen_kalemler: List[Dict[str, Any]] = []
    show_clarification_dialog: bool = False

    sistem_bildirim_metni: str = "Sistem: 30 gün yanıt bekleyen 1 teklif otomatik zaman aşımına alındı."

    @rx.var
    def has_matches(self) -> bool:
        return len(self.eslesen_kalemler) > 0

    @rx.var
    def eslesen_sayisi_str(self) -> str:
        return f"{len(self.eslesen_kalemler)} Kalem Eşleşti"

    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val

    def close_dialog(self):
        self.show_clarification_dialog = False

    def skip_unmatched_items(self):
        """Kullanıcı 'Tümünü Kapsam Dışı Bırak' dediğinde belirsiz kalemler elenir."""
        self.eslesmeyen_kalemler = []
        self.show_clarification_dialog = False
        return rx.toast.info("Eşleşmeyen kalemler (Level T, Pressure T vb.) kapsam dışı bırakıldı.", position="top-right")

    def add_unmatched_to_list(self, item_name: str):
        """Kullanıcı belirli bir kalemi teklife ilave etmek isterse listeye dahil eder."""
        for item in self.eslesmeyen_kalemler:
            if item["malzeme"] == item_name:
                self.eslesen_kalemler.append(item)
                self.eslesmeyen_kalemler = [it for it in self.eslesmeyen_kalemler if it["malzeme"] != item_name]
                break
        if not self.eslesmeyen_kalemler:
            self.show_clarification_dialog = False
        return rx.toast.success(f"'{item_name}' teklif listesine eklendi.", position="top-right")

    async def handle_cost_upload(self, files: List[rx.UploadFile]):
        if not files:
            return

        file = files[0]
        self.dosya_adi = file.filename
        content = await file.read()
        file_stream = BytesIO(content)

        fn_low = file.filename.lower()

        # -------------------------------------------------------------
        # 1. ADIM: DOSYA ADINDAN VEYA İÇERİĞİNDEN TEKLİF KODUNU BUL VE SEÇ
        # -------------------------------------------------------------
        tespit_edilen_kod = ""

        # A) Dosya adından regex ile ara (Örn: RFQ_PT202609201555...)
        m_fn = re.search(r"PT\d+", file.filename, re.IGNORECASE)
        if m_fn:
            tespit_edilen_kod = m_fn.group(0).upper()

        rfq_items = []
        excel_antet_metni = ""

        if fn_low.endswith((".xlsx", ".xls")):
            try:
                try:
                    df_raw = pd.read_excel(file_stream, header=None)
                except Exception:
                    file_stream.seek(0)
                    df_raw = pd.read_excel(file_stream, header=None, engine="openpyxl")

                # B) Dosya adında yoksa Excel ilk 10 satırdan (Talep No / Referans) ara
                if not tespit_edilen_kod:
                    for _, r in df_raw.iloc[:10].iterrows():
                        r_str = " ".join([str(v) for v in r.values if pd.notna(v)])
                        m_cell = re.search(r"PT\d+", r_str, re.IGNORECASE)
                        if m_cell:
                            tespit_edilen_kod = m_cell.group(0).upper()
                            break

                # -------------------------------------------------------------
                # TEKLİF AÇILIR KUTUSUNU (SELECT) OTOMATİK EŞLEŞTİR
                # -------------------------------------------------------------
                if tespit_edilen_kod:
                    for opt in self.teklif_secenekleri:
                        if tespit_edilen_kod in opt:
                            self.secilen_teklif = opt
                            break
                    else:
                        # Seçenekler listesinde tam metin yoksa bile yeni seçenek olarak ekleyip seç
                        yeni_opt = f"{tespit_edilen_kod} (Otomatik Algılandı)"
                        if yeni_opt not in self.teklif_secenekleri:
                            self.teklif_secenekleri.append(yeni_opt)
                        self.secilen_teklif = yeni_opt

                # -------------------------------------------------------------
                # KALEMLERİ AYRIŞTIRMA (ÖNCEKİ AKILLI MANTIK)
                # -------------------------------------------------------------
                header_idx = -1
                for idx, row in df_raw.iloc[:25].iterrows():
                    r_line = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
                    if "malzeme" in r_line and ("fiyat" in r_line or "açıklama" in r_line or "aciklama" in r_line):
                        header_idx = idx
                        break

                if header_idx != -1:
                    headers = [str(c).strip().lower() if pd.notna(c) else "" for c in df_raw.iloc[header_idx].tolist()]
                    c_ad_idx, c_fiyat_idx, c_pb_idx, c_ted_idx = None, None, None, None
                    for c_i, h in enumerate(headers):
                        if any(k in h for k in ["açıklama", "aciklama", "malzeme", "tanım"]):
                            c_ad_idx = c_i
                        elif any(k in h for k in ["birim fiyat", "fiyat", "maliyet"]):
                            c_fiyat_idx = c_i
                        elif any(k in h for k in ["para birimi", "pb"]):
                            c_pb_idx = c_i
                        elif any(k in h for k in ["marka", "tedarikçi", "menşei", "mensei"]):
                            c_ted_idx = c_i

                    for _, r in df_raw.iloc[header_idx + 1:].iterrows():
                        vals = r.tolist()
                        row_str = " ".join([str(v).lower() for v in vals if pd.notna(v)])
                        if any(x in row_str for x in ["sarı dolgulu", "fiyat teklifinizin", "geçerlilik süresi", "not:"]):
                            continue

                        ad = str(vals[c_ad_idx]).strip() if c_ad_idx is not None and pd.notna(vals[c_ad_idx]) else ""
                        if not ad or ad.lower() in ["nan", "none", "toplam"]:
                            continue

                        fiyat_raw = str(vals[c_fiyat_idx]) if c_fiyat_idx is not None and pd.notna(vals[c_fiyat_idx]) else "0"
                        fiyat_val = parse_sayi(fiyat_raw)

                        pb = "EUR"
                        if c_pb_idx is not None and pd.notna(vals[c_pb_idx]):
                            pb_str = str(vals[c_pb_idx]).strip().upper()
                            if "USD" in pb_str or "$" in pb_str: pb = "USD"
                            elif "TRY" in pb_str or "TL" in pb_str or "₺" in pb_str: pb = "TRY"
                            else: pb = "EUR"

                        ted = "VEGA Grieshaber KG" if "vega" in file.filename.lower() else "Genel Tedarikçi"
                        if c_ted_idx is not None and pd.notna(vals[c_ted_idx]):
                            ted_str = str(vals[c_ted_idx]).strip()
                            if ted_str and ted_str.lower() != "nan":
                                ted = ted_str

                        if fiyat_val > 0:
                            rfq_items.append({
                                "tanim": ad,
                                "fiyat": fiyat_val,
                                "fiyat_str": f"{fiyat_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                "pb": pb,
                                "tedarikci": ted,
                            })
            except Exception as e:
                return rx.toast.error(f"Excel okunurken hata: {str(e)}", position="top-right")

        # -------------------------------------------------------------
        # KALEMLERİ HEDEF TEKLİFİN KALEMLERİYLE EŞLEŞTİRME
        # -------------------------------------------------------------
        target_quote_items = [
            {
                "malzeme": "VEGAPULS 6X (Radar)",
                "miktar": 2.0,
                "birim": "Adet",
                "aliases": ["radar", "vegapuls", "vegapuls 6x", "radar seviye"],
            },
            {
                "malzeme": "VEGASWING 61 (Level Switch, Sinyal Değerlendirme Ünitesi Dahil)",
                "miktar": 2.0,
                "birim": "Adet",
                "aliases": ["level s", "level switch", "vegaswing", "seviye şalteri", "salteri"],
            },
        ]

        matched = []
        unmatched = []

        for item in rfq_items:
            t_low = item["tanim"].lower().strip()
            found_target = None

            for target in target_quote_items:
                if any(alias in t_low or t_low in alias for alias in target["aliases"]):
                    found_target = target
                    break

            if found_target:
                matched.append({
                    "malzeme": found_target["malzeme"],
                    "miktar": found_target["miktar"],
                    "birim": found_target["birim"],
                    "gelen_fiyat": item["fiyat"],
                    "gelen_fiyat_str": item["fiyat_str"],
                    "pb": item["pb"],
                    "tedarikci": item["tedarikci"],
                })
            else:
                unmatched.append({
                    "malzeme": item["tanim"],
                    "miktar": 1.0,
                    "birim": "Adet",
                    "gelen_fiyat": item["fiyat"],
                    "gelen_fiyat_str": item["fiyat_str"],
                    "pb": item["pb"],
                    "tedarikci": item["tedarikci"],
                })

        self.eslesen_kalemler = matched
        self.eslesmeyen_kalemler = unmatched

        if len(unmatched) > 0:
            self.show_clarification_dialog = True

        bildirim_ek = f"Teklif otomatik '{tespit_edilen_kod}' olarak seçildi." if tespit_edilen_kod else ""
        return rx.toast.success(f"{len(matched)} kalem eşleştirildi. {bildirim_ek}", position="top-right")



    async def maliyetleri_isle_ve_kaydet(self):
        if not self.eslesen_kalemler:
            return rx.toast.error("İşlenecek eşleşmiş maliyet kalemi bulunamadı.", position="top-right")

        kurlar = get_tcmb_kurlar()
        eur_kuru = float(kurlar.get("EUR", 56.4075))
        usd_kuru = float(kurlar.get("USD", 48.4777))

        toplam_maliyet_tl = 0.0
        for k in self.eslesen_kalemler:
            rate = eur_kuru if k["pb"] == "EUR" else (usd_kuru if k["pb"] == "USD" else 1.0)
            toplam_maliyet_tl += (float(k["miktar"]) * float(k["gelen_fiyat"]) * rate)

        clean_kod = self.secilen_teklif.split()[0].strip()

        # DashboardState güncelle
        dash_state = await self.get_state(DashboardState)
        if hasattr(dash_state, "raw_quotes"):
            for q in dash_state.raw_quotes:
                if clean_kod in q.get("kod", ""):
                    q["maliyet_try"] = round(toplam_maliyet_tl, 2)
                    satis = float(q.get("satis_try", 0.0))
                    if satis > 0:
                        q["marj"] = round(((satis - toplam_maliyet_tl) / satis) * 100, 1)
                    break

        return rx.toast.success(
            f"Maliyetler '{clean_kod}' teklifine işlendi! Toplam Maliyet: {toplam_maliyet_tl:,.2f} ₺",
            position="top-right",
        )