import reflex as rx
from typing import List, Dict, Any
from io import BytesIO
import re

from datetime import datetime
from .shared_quotes import register_quote
from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB

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

    # Tablo Kalemleri
    kalemler: List[Dict[str, Any]] = []

    @rx.var
    def has_file(self) -> bool:
        return self.dosya_yuklendi and len(self.kalemler) > 0

    async def handle_quote_upload(self, files: List[rx.UploadFile]):
        """Yüklenen PDF veya Excel dosyasını parsers.py motorunu kullanarak ayrıştırır."""
        if not files or len(files) == 0:
            return rx.toast.error("Lütfen önce bir dosya seçin!", position="top-right")

        file = files[0]
        self.dosya_adi = file.filename
        content = await file.read()
        if not content:
            return rx.toast.error("Dosya içeriği boş veya okunamadı.", position="top-right")

        file_stream = BytesIO(content)
        # parsers.py dosya adından regex ile PT kodunu yakalayabilsin diye name özniteliği set edilir
        setattr(file_stream, "name", file.filename)

        fn_low = file.filename.lower()
        parsed_result = None

        try:
            # 1. PDF Ayrıştırma
            if fn_low.endswith(".pdf"):
                parsed_result = extract_pdf_full(file_stream)

            # 2. Excel Ayrıştırma
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
            toplam_satis_tl = float(parsed_result.get("toplam_tutar", 0.0))

            # Arayüz tablosu için formatlanmış kalemler listesi
            formatted_kalemler = []
            toplam_maliyet_tl = 0.0

            for k in raw_kalemler:
                mik = float(k.get("miktar", 1.0))
                birim = str(k.get("birim", "Adet"))
                b_fiyat = float(k.get("birim_satis") or k.get("birim_fiyat") or 0.0)
                tutar = float(k.get("toplam_tl") or k.get("toplam") or (mik * b_fiyat))
                pb = str(k.get("para_birimi", "TRY"))
                b_maliyet = float(k.get("birim_maliyet", 0.0))
                m_pb = str(k.get("maliyet_pb", "TRY"))

                # Maliyet hesabı
                if b_maliyet > 0:
                    rate = self.kur_eur if m_pb == "EUR" else (self.kur_usd if m_pb == "USD" else 1.0)
                    toplam_maliyet_tl += (mik * b_maliyet * rate)

                formatted_kalemler.append({
                    "malzeme_adi": k.get("malzeme_adi", "Tanımsız Malzeme"),
                    "miktar": mik,
                    "miktar_str": f"{int(mik) if mik.is_integer() else mik} {birim}",
                    "birim": birim,
                    "birim_fiyat": b_fiyat,
                    "birim_fiyat_str": f"{b_fiyat:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                    "tutar_tl": tutar,
                    "tutar_tl_str": f"{tutar:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                    "para_birimi": pb,
                })

            # Eğer parsers.py dip toplamı 0 hesaplamışsa kalemlerden topla
            if toplam_satis_tl <= 0 and formatted_kalemler:
                toplam_satis_tl = sum(k["tutar_tl"] for k in formatted_kalemler)

            self.kalemler = formatted_kalemler
            self.toplam_satis = round(toplam_satis_tl, 2)
            self.toplam_satis_str = f"{self.toplam_satis:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
            self.toplam_maliyet = round(toplam_maliyet_tl, 2)
            self.toplam_maliyet_str = f"{self.toplam_maliyet:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")

            # Marj hesabı
            if self.toplam_satis > 0 and self.toplam_maliyet > 0:
                marj = ((self.toplam_satis - self.toplam_maliyet) / self.toplam_satis) * 100
                self.kar_marji_str = f"%{marj:.1f} Marj"
            else:
                self.kar_marji_str = "%100.0 Marj"

            self.dosya_yuklendi = True

            if formatted_kalemler:
                return rx.toast.success(
                    f"'{file.filename}' başarıyla ayrıştırıldı: {len(formatted_kalemler)} kalem listelendi!",
                    position="top-right"
                )
            else:
                return rx.toast.warning(
                    f"'{file.filename}' okundu ancak kalem tablosu tespit edilemedi.",
                    position="top-right"
                )

        except Exception as err:
            return rx.toast.error(f"Ayrıştırma hatası: {str(err)}", position="top-right")


    async def teklifi_portala_kaydet(self):
        """Ayrıştırılan teklifi hem sisteme hem de paylaşılan ortak teklif havuzuna kaydeder."""
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
        evrensel_kalemler = []
        for k in self.kalemler:
            ad = k.get("malzeme_adi") or k.get("tanim") or k.get("malzeme") or "Tanımsız Kalem"
            mik = float(k.get("miktar", 1.0))
            birim = str(k.get("birim", "Adet"))
            b_fiyat = float(k.get("birim_fiyat") or k.get("birim_satis") or 0.0)
            tutar = float(k.get("tutar_tl") or k.get("toplam_tl") or k.get("toplam") or (mik * b_fiyat))
            pb = str(k.get("para_birimi", "TRY"))

            evrensel_kalemler.append({
                # Her iki modülün beklediği tüm varyasyonlar:
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
                "birim_fiyat_str": f"{b_fiyat:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                "tutar_tl": tutar,
                "toplam": tutar,
                "toplam_tl": tutar,
                "tutar_tl_str": f"{tutar:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                "para_birimi": pb,
            })

        # -------------------------------------------------------------
        # 3. Ortak Teklif Havuzuna Kaydet
        # -------------------------------------------------------------
        # 1. SQLite ve Ortak Havuza Kaydet
        try:
            extra_bilgi = {
                "konu": self.konu,
                "teklif_tarihi": self.teklif_tarihi,
                "sorumlu": sorumlu_kisi,
                "durum": "Müşteride",
                "yaslanma_gun": yaslanma_gun,
                "satis_try": self.toplam_satis,
                "maliyet_try": self.toplam_maliyet,
            }
            register_quote(
                kod=self.teklif_kodu,
                baslik=f"{self.teklif_kodu} - {self.musteri}",
                kalemler=evrensel_kalemler,
                musteri=self.musteri,
                extra_data=extra_bilgi
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
            "toplam": self.toplam_satis,
            "musteri": self.musteri,
            "tarih": self.teklif_tarihi,
            "sorumlu": sorumlu_kisi,
            "muhendis": sorumlu_kisi,
            "yaslanma_gun": yaslanma_gun,
        }

        # -------------------------------------------------------------
        # 5. DashboardState Canlı Listesini Güncelle
        # -------------------------------------------------------------
        try:
            dash_state = await self.get_state(DashboardState)
            if hasattr(dash_state, "raw_quotes"):
                marj_val = 100.0 if self.toplam_maliyet == 0 else round(((self.toplam_satis - self.toplam_maliyet) / self.toplam_satis) * 100, 1)

                yeni_teklif_obj = {
                    "kod": self.teklif_kodu,
                    "teklif_kodu": self.teklif_kodu,
                    "musteri": self.musteri,
                    "konu": self.konu,
                    "tarih": self.teklif_tarihi,
                    "sorumlu": sorumlu_kisi,
                    "muhendis": sorumlu_kisi,
                    "sorumlu_muhendis": sorumlu_kisi,
                    "satis_try": self.toplam_satis,
                    "maliyet_try": self.toplam_maliyet,
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
            f"'{self.teklif_kodu}' teklifi portala ve karşılaştırma havuzuna başarıyla kaydedildi!",
            position="top-right",
        )
        """Ayrıştırılan teklifi hem sisteme hem de paylaşılan ortak teklif havuzuna kaydeder."""
        if not self.kalemler or not self.teklif_kodu:
            return rx.toast.error("Kaydedilecek geçerli bir teklif bulunamadı.", position="top-right")

        sorumlu_kisi = self.muhendis or "Mustafa GÜRBÜZ"

        # -------------------------------------------------------------
        # 1. Yaşlanma Günü (yaslanma_gun) Hesabı
        # -------------------------------------------------------------
        yaslanma_gun = 0
        try:
            # Tarih formatlarını dene (7.01.2026, 07.01.2026, 2026-01-07 vb.)
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
        # 2. Ortak Teklif Havuzuna Kaydet
        # -------------------------------------------------------------
        try:
            register_quote(
                kod=self.teklif_kodu,
                baslik=f"{self.teklif_kodu} - {self.musteri}",
                kalemler=self.kalemler,
                musteri=self.musteri,
            )
        except Exception:
            pass

        # -------------------------------------------------------------
        # 3. VERSIONS_DB Kaydı
        # -------------------------------------------------------------
        VERSIONS_DB[self.teklif_kodu] = {
            "items": {
                k["malzeme_adi"]: {
                    "miktar": k["miktar"],
                    "birim": k["birim"],
                    "fiyat": k["birim_fiyat"],
                    "tutar": k["tutar_tl"],
                }
                for k in self.kalemler
            },
            "toplam": self.toplam_satis,
            "musteri": self.musteri,
            "tarih": self.teklif_tarihi,
            "sorumlu": sorumlu_kisi,
            "muhendis": sorumlu_kisi,
            "yaslanma_gun": yaslanma_gun,
        }

        # -------------------------------------------------------------
        # 4. DashboardState Listesine Eksiksiz Şema ile Kaydet
        # -------------------------------------------------------------
        try:
            dash_state = await self.get_state(DashboardState)
            if hasattr(dash_state, "raw_quotes"):
                marj_val = 100.0 if self.toplam_maliyet == 0 else round(((self.toplam_satis - self.toplam_maliyet) / self.toplam_satis) * 100, 1)

                yeni_teklif_obj = {
                    "kod": self.teklif_kodu,
                    "teklif_kodu": self.teklif_kodu,
                    "musteri": self.musteri,
                    "konu": self.konu,
                    "tarih": self.teklif_tarihi,
                    "sorumlu": sorumlu_kisi,
                    "muhendis": sorumlu_kisi,
                    "sorumlu_muhendis": sorumlu_kisi,
                    "satis_try": self.toplam_satis,
                    "maliyet_try": self.toplam_maliyet,
                    "marj": marj_val,
                    "kar_marji": marj_val,
                    "durum": "Müşteride",                    # <-- "Teklif Verildi" yerine "Müşteride" yapıldı
                    "yaslanma_gun": yaslanma_gun,
                    "kalemler": self.kalemler,
                }

                # Mevcut teklif varsa güncelle, yoksa en başa ekle
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
            f"'{self.teklif_kodu}' teklifi portala ve karşılaştırma havuzuna başarıyla kaydedildi!",
            position="top-right",
        )