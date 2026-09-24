import reflex as rx
from typing import List, Dict, Any, Tuple
from io import BytesIO
import re

from pypdf import PdfReader
from datetime import datetime
from .shared_quotes import register_quote
from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB


try:
    from .services.db_service import save_teklif_to_db
except ImportError:
    try:
        from services.db_service import save_teklif_to_db
    except ImportError:
        save_teklif_to_db = None


try:
    from .procurement_coverage_state import ProcurementCoverageState
except ImportError:
    try:
        from procurement_coverage_state import ProcurementCoverageState
    except ImportError:
        ProcurementCoverageState = None


try:
    from .services.parsers import (
        extract_pdf_full,
        extract_excel_full_with_cost_sheets,
        parse_sayi,
    )
except ImportError:
    from services.parsers import (
        extract_pdf_full,
        extract_excel_full_with_cost_sheets,
        parse_sayi,
    )

UPLOAD_ID = "quote_upload_input_id"


def detect_currency_and_symbol(raw_text: str) -> Tuple[str, str]:
    """
    Belgenin ana para birimini tespit eder.
    'Toplam Fiyat Teklifi TL' gibi bilgilendirme kolonları yerine
    asıl teklif para birimini (EUR / USD) önceliklendirir.
    """
    t = raw_text.lower()

    # 1. EURO Tespiti (€ simgesi veya Fiyat sütunundaki EUR/Euro ifadesi)
    if "€" in raw_text or "\x80" in raw_text or "\u20ac" in raw_text:
        return "EUR", "€"
    if re.search(r"\b(eur|euro|avro)\b", t):
        return "EUR", "€"
    if re.search(r"(fiyat|tutar|birim|toplam)\s*\(?eur", t):
        return "EUR", "€"

    # 2. USD Tespiti ($ simgesi veya USD ifadesi)
    if "$" in raw_text:
        return "USD", "$"
    if re.search(r"\b(usd|dolar|dollar)\b", t):
        return "USD", "$"
    if re.search(r"(fiyat|tutar|birim|toplam)\s*\(?usd", t):
        return "USD", "$"

    # 3. Yalnızca döviz sembolü/ibaresi yoksa ve açıkça TL/₺ varsa TRY kabul edilir
    if "₺" in raw_text or re.search(r"\b(tl|try|türk lirası|turk lirasi)\b", t):
        return "TRY", "₺"

    return "TRY", "₺"


def format_currency_str(val: float, symbol: str) -> str:
    """Sayısal tutarı Türkçe basamak formatında ve para sembolüyle döndürür."""
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" {symbol}"


class QuoteUploadState(rx.State):
    # Dosya durumu
    dosya_adi: str = "Dosya seçilmedi"
    dosya_yuklendi: bool = False

    # Teklif Antet Bilgileri
    teklif_kodu: str = ""
    musteri: str = ""
    musteri_iletisim: str = ""
    konu: str = ""
    teklif_tarihi: str = ""
    muhendis: str = ""

    # Kurlar
    kur_usd: float = 46.3293
    kur_eur: float = 53.21

    # Finansal Göstergeler
    toplam_satis: float = 0.0
    toplam_satis_str: str = "0,00 ₺"
    toplam_maliyet: float = 0.0
    toplam_maliyet_str: str = "0,00 ₺"
    kar_marji_str: str = "%100.0 Marj"

    # Para Birimi ve Çevrim Değişkenleri
    para_birimi: str = "TRY"
    para_birimi_sembol: str = "₺"
    satis_tutari_orijinal: float = 0.0
    satis_tutari_try: float = 0.0
    satis_tutari_str: str = "0,00 ₺"

    # Tablo Kalemleri
    kalemler: List[Dict[str, Any]] = []

    @rx.var
    def has_file(self) -> bool:
        return self.dosya_yuklendi and len(self.kalemler) > 0

    async def handle_quote_upload(self, files: List[rx.UploadFile]):
        """Yüklenen PDF veya Excel dosyasını parsers.py motorunu kullanarak ayrıştırır ve para birimini işler."""
        if not files or len(files) == 0:
            return rx.toast.error("Lütfen önce bir dosya seçin!", position="top-right")

        file = files[0]
        self.dosya_adi = file.filename
        content = await file.read()
        if not content:
            return rx.toast.error("Dosya içeriği boş veya okunamadı.", position="top-right")

        file_stream = BytesIO(content)
        setattr(file_stream, "name", file.filename)

        fn_low = file.filename.lower()
        parsed_result = None

        try:
            full_raw_text = ""
            if fn_low.endswith(".pdf"):
                file_stream.seek(0)
                parsed_result = extract_pdf_full(file_stream)
                
                # PDF metnini doğrudan da oku (Karakter kodlaması / Para birimi analizi için)
                file_stream.seek(0)
                try:
                    pdf_reader = PdfReader(file_stream)
                    for page in pdf_reader.pages:
                        t = page.extract_text()
                        if t:
                            full_raw_text += t + " "
                except Exception:
                    pass

            elif fn_low.endswith((".xlsx", ".xls")):
                parsed_result = extract_excel_full_with_cost_sheets(file_stream)

            else:
                return rx.toast.error("Yalnızca .pdf ve .xlsx formatları desteklenmektedir.", position="top-right")

            if not parsed_result:
                return rx.toast.error("Dosya ayrıştırılamadı.", position="top-right")

            # parsers.py'den gelen antet ve kur verilerini ata
            self.teklif_kodu = parsed_result.get("teklif_kodu") or re.search(r"PT\d+", file.filename, re.I).group(0)
            self.musteri = parsed_result.get("musteri") or "Müşteri Firması"
            self.musteri_iletisim = parsed_result.get("musteri_iletisim") or ""
            self.konu = parsed_result.get("konu") or "Endüstriyel Ekipman ve Saha Hizmeti"
            self.teklif_tarihi = parsed_result.get("teklif_tarihi") or "23.09.2026"
            self.muhendis = parsed_result.get("muhendis") or "Muhammed GÜNER"
            self.kur_usd = float(parsed_result.get("kur_usd", 46.3293))
            self.kur_eur = float(parsed_result.get("kur_eur", 53.21))

            raw_kalemler = parsed_result.get("kalemler", [])
            parsed_toplam = float(parsed_result.get("toplam_tutar", 0.0))

            # =========================================================
            # 2. KISIM: KESİN PARA BİRİMİ VE KUR TESPİTİ
            # =========================================================
            # Kalemlerdeki para birimlerini topla
            kalem_pb_list = [str(k.get("para_birimi", "TRY")).upper() for k in raw_kalemler]
            try_count = sum(1 for pb in kalem_pb_list if pb == "TRY")
            eur_count = sum(1 for pb in kalem_pb_list if pb == "EUR")
            usd_count = sum(1 for pb in kalem_pb_list if pb == "USD")

            # Eğer kalemlerin çoğu TL ise (örneğin 12 kalemin 12'si de TL ise), üst kart ASLA Euro olamaz!
            if try_count >= len(raw_kalemler) / 2 and try_count > 0:
                self.para_birimi = "TRY"
                self.para_birimi_sembol = "₺"
            elif eur_count > usd_count and eur_count > 0:
                self.para_birimi = "EUR"
                self.para_birimi_sembol = "€"
            elif usd_count > 0:
                self.para_birimi = "USD"
                self.para_birimi_sembol = "$"
            else:
                # Yedek tespit
                self.para_birimi = parsed_result.get("para_birimi", "TRY")
                self.para_birimi_sembol = "€" if self.para_birimi == "EUR" else ("$" if self.para_birimi == "USD" else "₺")

            # Geçerli kur çarpanı
            aktif_kur = self.kur_eur if self.para_birimi == "EUR" else (self.kur_usd if self.para_birimi == "USD" else 1.0)

            # Arayüz tablosu kalemleri
            formatted_kalemler = []
            toplam_maliyet_tl = 0.0
            toplam_satis_orijinal = 0.0

            for k in raw_kalemler:
                mik = float(k.get("miktar", 1.0))
                birim = str(k.get("birim", "Adet"))
                b_fiyat = float(k.get("birim_satis") or k.get("birim_fiyat") or 0.0)
                satir_tutar_orijinal = float(k.get("toplam") or k.get("toplam_tutar") or (mik * b_fiyat))
                
                # Kalemin para birimini genel para birimine eşitle (böylece üst ve alt asla çelişmez)
                kalem_pb = self.para_birimi
                kalem_sembol = self.para_birimi_sembol

                ham_ad = str(k.get("malzeme_adi") or k.get("tanim") or "Tanımsız Malzeme")
                temiz_ad = re.sub(r"\s*[-–—]\s*\d+\s*(?:set|adet|ad\.?)?$", "", ham_ad, flags=re.IGNORECASE).strip()
    
                satir_tutar_tl = satir_tutar_orijinal if self.para_birimi == "TRY" else (satir_tutar_orijinal * aktif_kur)
    
                b_maliyet = float(k.get("birim_maliyet", 0.0))
                m_pb = str(k.get("maliyet_pb", "TRY")).upper()
    
                if b_maliyet > 0:
                    rate = self.kur_eur if "EUR" in m_pb else (self.kur_usd if "USD" in m_pb else 1.0)
                    toplam_maliyet_tl += (mik * b_maliyet * rate)
    
                toplam_satis_orijinal += satir_tutar_orijinal
    
                formatted_kalemler.append({
                    "malzeme_adi": temiz_ad,
                    "miktar": mik,
                    "miktar_str": f"{int(mik) if mik.is_integer() else mik} {birim}",
                    "birim": birim,
                    "birim_fiyat": b_fiyat,
                    "birim_fiyat_str": format_currency_str(b_fiyat, kalem_sembol),
                    "tutar_orijinal": satir_tutar_orijinal,
                    "tutar_tl": satir_tutar_tl,
                    "tutar_tl_str": format_currency_str(satir_tutar_tl, "₺"),
                    "satir_toplam_str": format_currency_str(satir_tutar_orijinal, kalem_sembol),
                    "para_birimi": kalem_pb,
                })

            if parsed_toplam > 0 and self.para_birimi == parsed_result.get("para_birimi"):
                self.satis_tutari_orijinal = round(parsed_toplam, 2)
            else:
                self.satis_tutari_orijinal = round(toplam_satis_orijinal, 2)

            # TL ve Döviz Değerleri
            self.satis_tutari_try = round(self.satis_tutari_orijinal * aktif_kur, 2)
            self.toplam_satis = self.satis_tutari_try

            # Ekranda gösterilecek formatlar
            self.satis_tutari_str = format_currency_str(self.satis_tutari_orijinal, self.para_birimi_sembol)
            self.toplam_satis_str = self.satis_tutari_str

            self.toplam_maliyet = round(toplam_maliyet_tl, 2)
            self.toplam_maliyet_str = format_currency_str(self.toplam_maliyet, "₺")

            # Kar marjı
            if self.toplam_satis > 0 and self.toplam_maliyet > 0:
                marj = ((self.toplam_satis - self.toplam_maliyet) / self.toplam_satis) * 100
                self.kar_marji_str = f"%{marj:.1f} Marj"
            else:
                self.kar_marji_str = "%100.0 Marj"

            self.kalemler = formatted_kalemler
            self.dosya_yuklendi = True

            return rx.toast.success(
                f"Teklif ayrıştırıldı! Para Birimi: {self.para_birimi} ({self.para_birimi_sembol})",
                position="top-right"
            )

        except Exception as err:
            return rx.toast.error(f"Ayrıştırma hatası: {str(err)}", position="top-right")
        
        
    async def teklifi_portala_kaydet(self):
        """Ayrıştırılan teklifi hem sisteme hem de paylaşılan ortak teklif havuzuna döviz ve TL bilgisiyle kaydeder."""
        if not self.kalemler or not self.teklif_kodu:
            return rx.toast.error("Kaydedilecek geçerli bir teklif bulunamadı.", position="top-right")

        sorumlu_kisi = self.muhendis or "Mustafa GÜRBÜZ"

        # -------------------------------------------------------------
        # 1. Yaşlanma Günü (yaslanma_gun) Hesabı
        # -------------------------------------------------------------
        yaslanma_gun = 0
        try:
            t_str = self.teklif_tarihi.strip()
            t_obj = None
            for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    t_obj = datetime.strptime(t_str, fmt)
                    break
                except ValueError:
                    continue
            if t_obj:
                bugun = datetime.now()
                fark = (bugun - t_obj).days
                yaslanma_gun = max(0, fark)
            else:
                yaslanma_gun = 12
        except Exception:
            yaslanma_gun = 0

        # -------------------------------------------------------------
        # 2. Akıllı Tedarikçi ve Diğer Modüller İçin Evrensel Kalem Listesi
        # -------------------------------------------------------------
        aktif_kur = self.kur_usd if self.para_birimi == "USD" else (self.kur_eur if self.para_birimi == "EUR" else 1.0)
        evrensel_kalemler = []
        for k in self.kalemler:
            ad = k.get("malzeme_adi") or k.get("tanim") or k.get("malzeme") or "Tanımsız Kalem"
            mik = float(k.get("miktar", 1.0))
            birim = str(k.get("birim", "Adet"))
            b_fiyat = float(k.get("birim_fiyat") or k.get("birim_satis") or 0.0)
            tutar_orj = float(k.get("tutar_orijinal") or (mik * b_fiyat))
            tutar_tl = float(k.get("tutar_tl") or (tutar_orj * aktif_kur))

            # Kalemin kendi para birimi sembolü
            k_pb = k.get("para_birimi") or self.para_birimi
            k_sembol = "€" if k_pb == "EUR" else ("$" if k_pb == "USD" else "₺")

            evrensel_kalemler.append({
                "malzeme_adi": ad,
                "malzeme": ad,
                "tanim": ad,
                "aciklama": ad,
                "miktar": mik,
                "miktar_str": f"{int(mik) if mik.is_integer() else mik} {birim}",
                "birim": birim,
                "birim_fiyat": b_fiyat,
                "birim_satis": b_fiyat,
                "fiyat": b_fiyat,
                "birim_fiyat_str": format_currency_str(b_fiyat, k_sembol),
                "tutar_orijinal": tutar_orj,
                "tutar_tl": tutar_tl,
                "toplam": tutar_orj,
                "toplam_tl": tutar_tl,
                "tutar_tl_str": format_currency_str(tutar_tl, "₺"),
                "para_birimi": k_pb,
            })

        # -------------------------------------------------------------
        # 3. Ortak Teklif Havuzuna Kaydet
        # -------------------------------------------------------------
        try:
            extra_bilgi = {
                "konu": self.konu,
                "teklif_tarihi": self.teklif_tarihi,
                "sorumlu": sorumlu_kisi,
                "durum": "Müşteride",
                "yaslanma_gun": yaslanma_gun,
                "para_birimi": self.para_birimi,
                "para_birimi_sembol": self.para_birimi_sembol,
                "satis_orijinal": self.satis_tutari_orijinal,
                "satis_toplam": self.satis_tutari_try,
                "satis_try": self.satis_tutari_try,
                "maliyet_toplam": self.toplam_maliyet,
                "maliyet_try": self.toplam_maliyet,
            }
            register_quote(
                kod=self.teklif_kodu,
                baslik=f"{self.teklif_kodu} - {self.musteri}",
                kalemler=evrensel_kalemler,
                musteri=self.musteri,
                extra_data=extra_bilgi,
            )
        except Exception:
            pass
        
        # -------------------------------------------------------------
        # 3.1 Kalıcı Veritabanına (DB) Kaydet
        # -------------------------------------------------------------
        if save_teklif_to_db:
            try:
                save_teklif_to_db(
                    kod=self.teklif_kodu,
                    musteri=self.musteri,
                    konu=self.konu,
                    tarih=self.teklif_tarihi,
                    sorumlu=sorumlu_kisi,
                    satis_try=self.satis_tutari_try,
                    maliyet_try=self.toplam_maliyet,
                    marj=100.0 if self.toplam_maliyet == 0 else round(((self.satis_tutari_try - self.toplam_maliyet) / self.satis_tutari_try) * 100, 1),
                    kalemler=evrensel_kalemler,
                )
            except Exception:
                pass
        
        # -------------------------------------------------------------
        # 4. VERSIONS_DB Kaydı
        # -------------------------------------------------------------
        VERSIONS_DB[self.teklif_kodu] = {
            "items": {
                k["malzeme_adi"]: {
                    "miktar": k["miktar"],
                    "birim": k["birim"],
                    "fiyat": k["birim_fiyat"],
                    "tutar": k["tutar_tl"],
                }
                for k in evrensel_kalemler
            },
            "toplam": self.satis_tutari_try,
            "musteri": self.musteri,
            "tarih": self.teklif_tarihi,
            "sorumlu": sorumlu_kisi,
            "muhendis": sorumlu_kisi,
            "yaslanma_gun": yaslanma_gun,
            "para_birimi": self.para_birimi,
        }

        # -------------------------------------------------------------
        # 5. DashboardState Canlı Listesini Güncelle
        # -------------------------------------------------------------
        try:
            dash_state = await self.get_state(DashboardState)
            if hasattr(dash_state, "raw_quotes"):
                marj_val = (
                    100.0
                    if self.toplam_maliyet == 0
                    else round(((self.satis_tutari_try - self.toplam_maliyet) / self.satis_tutari_try) * 100, 1)
                )

                yeni_teklif_obj = {
                    "kod": self.teklif_kodu,
                    "teklif_kodu": self.teklif_kodu,
                    "musteri": self.musteri,
                    "konu": self.konu,
                    "tarih": self.teklif_tarihi,
                    "sorumlu": sorumlu_kisi,
                    "muhendis": sorumlu_kisi,
                    "sorumlu_muhendis": sorumlu_kisi,
                    "para_birimi": self.para_birimi,
                    "para_birimi_sembol": self.para_birimi_sembol,
                    "satis_orijinal": self.satis_tutari_orijinal,
                    "satis_try": self.satis_tutari_try,
                    "satis_str": format_currency_str(self.satis_tutari_try, "₺"),
                    "maliyet_try": self.toplam_maliyet,
                    "maliyet_str": format_currency_str(self.toplam_maliyet, "₺"),
                    "marj": marj_val,
                    "kar_marji": marj_val,
                    "durum": "Müşteride",
                    "yaslanma_gun": yaslanma_gun,
                    "kalemler": evrensel_kalemler,
                }

                mevcut_idx = -1
                for i, q in enumerate(dash_state.raw_quotes):
                    if q.get("kod") == self.teklif_kodu or q.get("teklif_kodu") == self.teklif_kodu:
                        mevcut_idx = i
                        break

                if mevcut_idx != -1:
                    dash_state.raw_quotes[mevcut_idx] = yeni_teklif_obj
                else:
                    dash_state.raw_quotes.insert(0, yeni_teklif_obj)

        except Exception as err:
            return rx.toast.error(f"Portala kayıt sırasında hata: {str(err)}", position="top-right")

        return rx.toast.success(
            f"'{self.teklif_kodu}' teklifi portala ve karşılaştırma havuzuna başarıyla kaydedildi ({self.para_birimi_sembol})!",
            position="top-right",
        )
        # -------------------------------------------------------------
        # 6. Satınalma Kapsama Raporunu Canlı Güncelle
        # -------------------------------------------------------------
        try:
            if ProcurementCoverageState:
                proc_state = await self.get_state(ProcurementCoverageState)
                await proc_state.sync_from_dashboard()
        except Exception:
            pass