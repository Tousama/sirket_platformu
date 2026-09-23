import pdfplumber
import re
import pandas as pd

def tr_lower(metin: str) -> str:
    if not metin:
        return ""
    donusum = {"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"}
    for b, k in donusum.items():
        metin = metin.replace(b, k)
    return metin.lower().strip()

def parse_sayi(deger) -> float:
    if not deger:
        return 0.0
    val = str(deger).strip()
    val = re.sub(r"[^\d,\.-]", "", val)
    if not val:
        return 0.0
    if "," in val and "." in val:
        if val.rfind(",") > val.rfind("."):
            val = val.replace(".", "").replace(",", ".")
        else:
            val = val.replace(",", "")
    elif "," in val:
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return 0.0

def extract_pdf_full(pdf_file):
    bos_sonuc = {
        "teklif_kodu": "",
        "musteri": "",
        "musteri_iletisim": "",
        "teklif_tarihi": "",
        "muhendis": "",
        "konu": "",
        "kur_usd": 46.3293,
        "kur_eur": 53.21,
        "toplam_tutar": 0.0,
        "para_birimi": "TRY",
        "kalemler": [],
        "tam_metin": ""
    }

    try:
        kalemler = []
        toplam_tutar = 0.0
        teklif_kodu = ""
        musteri_adi = ""
        musteri_iletisim = ""
        teklif_tarihi = ""
        muhendis_adi = ""
        konu_adi = ""
        raw_tables = []

        # 1. Dosya adından teklif kodunu ve konuyu yakala
        dosya_adi = getattr(pdf_file, "name", "")
        if dosya_adi:
            fn_match = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
            if fn_match:
                teklif_kodu = fn_match.group(0).upper()

        # 2. PDF sayfalarını ve tabloları oku
        with pdfplumber.open(pdf_file) as pdf:
            metin_parcalari = []
            for page in pdf.pages:
                txt = page.extract_text(layout=False)
                if txt:
                    metin_parcalari.append(txt)
                tables = page.extract_tables()
                if tables:
                    raw_tables.extend(tables)
            tam_metin = "\n".join(metin_parcalari)

        # 3. Kurları Oku (Örn: USD: 46,3293 / EURO: 53,21)
        kur_usd = 46.3293
        kur_eur = 53.21
        m_kur = re.search(r"USD\s*:\s*([0-9\.,]+).*?EUR(?:O)?\s*:\s*([0-9\.,]+)", tam_metin, re.IGNORECASE)
        if m_kur:
            usd_s = m_kur.group(1).replace(".", "").replace(",", ".") if "," in m_kur.group(1) else m_kur.group(1)
            eur_s = m_kur.group(2).replace(".", "").replace(",", ".") if "," in m_kur.group(2) else m_kur.group(2)
            kur_usd = parse_sayi(usd_s) or kur_usd
            kur_eur = parse_sayi(eur_s) or kur_eur

        # 4. Teklif Kodu
        if not teklif_kodu and tam_metin:
            pt_match = re.search(r"PT\s*[-_:/]?\s*(\d{6,14})|PT\d+", tam_metin, re.IGNORECASE)
            if pt_match:
                teklif_kodu = (pt_match.group(0) or "").replace(" ", "").replace("-", "").upper()

        # 5. Müşteri
        mus_match = re.search(r"(?:Sayın|Sayin|Sn\.|Müşteri|Firma|Tesis|Teklif Talep Eden Kişi/Firma)\s*[:\s]*([^\n\r]+)", tam_metin, re.IGNORECASE)
        if mus_match:
            m_ad = mus_match.group(1).strip()
            m_ad = re.sub(r"(Yetkili|Tarih|Teklif No|Konu|Teklif Talep Eden).*", "", m_ad, flags=re.IGNORECASE).strip()
            if len(m_ad) > 2:
                musteri_adi = m_ad

        # 6. Konu
        konu_match = re.search(r"(?:Teklifin Konusu|Konu)\s*[:\s]*([^\n\r]+)", tam_metin, re.IGNORECASE)
        if konu_match:
            konu_adi = konu_match.group(1).strip()

        # 7. Mühendis
        muh_match = re.search(r"(?:Teklifi\s+Hazırlayan|Hazırlayan|Sorumlu\s+Mühendis)\s*[:\s]*([^\n\r]+)", tam_metin, re.IGNORECASE)
        if muh_match:
            m_satir = muh_match.group(1).strip()
            m_satir = re.sub(r"(Teklif\s*Tarihi|İletişim|Mail|Tel|Konu|Teklif\s*No).*", "", m_satir, flags=re.IGNORECASE).strip()
            if len(m_satir) > 3:
                muhendis_adi = m_satir

        # 8. Kesin Dip Teklif Toplamı (Görsel 2'deki "Teklif Toplamı ₺: 882.641,86 ₺")
        toplam_regex = re.search(r"Teklif\s+Toplam[ıi]\s*(?:₺|TL)?\s*[:\s]*([0-9\.,]+)", tam_metin, re.IGNORECASE)
        if toplam_regex:
            toplam_tutar = parse_sayi(toplam_regex.group(1))

        # 9. PetroTek Tablo Formatını Sütun Başlıklarına Göre Ayrıştır
        for tbl in raw_tables:
            if not tbl:
                continue

            # Başlık satırını bulup sütun indekslerini dinamik belirleyelim
            col_fiyat_idx = -1
            col_toplam_idx = -1
            col_doviz_toplam_idx = -1
            header_found = False

            for row_idx, row in enumerate(tbl):
                row_str = " ".join([str(c).replace("\n", " ").strip() for c in row if c]).lower()
                
                # Tablo Başlık Satırı Kontrolü
                if "açıklama" in row_str and ("fiyat" in row_str or "miktar" in row_str):
                    header_found = True
                    headers = [str(c).replace("\n", " ").strip().lower() if c else "" for c in row]
                    for idx, h in enumerate(headers):
                        if h == "fiyat" or ("birim fiyat" in h and "toplam" not in h):
                            col_fiyat_idx = idx
                        elif "döviz toplam" in h:
                            col_doviz_toplam_idx = idx
                        elif "toplam fiyat" in h or h == "toplam":
                            col_toplam_idx = idx
                    continue

                if not header_found or not row:
                    continue

                r_cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in row]
                row_str = " ".join(r_cells).lower()

                # Alt özet satırlarını atla
                if any(x in row_str for x in ["güncel kur", "döviz toplam", "tl toplam", "teklif toplamı", "kdv dahil", "opsiyon", "ödeme"]):
                    continue

                try:
                    # Hücreleri listele
                    valid_cells = [c for c in r_cells if c != ""]
                    if len(valid_cells) < 4:
                        continue

                    # 1. TOPLAM SATIŞ (TL) -> En son sütun
                    toplam_tl_str = r_cells[col_toplam_idx] if col_toplam_idx != -1 else valid_cells[-1]
                    satir_toplam_tl = parse_sayi(toplam_tl_str.replace("₺", "").replace("TL", ""))

                    # 2. DOĞRUDAN 'FİYAT' SÜTUNU:
                    # Başlıkta bulunduysa o sütun, bulunamadıysa:
                    # 7 sütunlu yapıda (Döviz Toplam varsa) sondan 3., 6 sütunlu yapıda sondan 2. hücredir.
                    if col_fiyat_idx != -1 and col_fiyat_idx < len(r_cells) and r_cells[col_fiyat_idx]:
                        fiyat_cell = r_cells[col_fiyat_idx]
                    else:
                        if len(valid_cells) >= 6:
                            # [S.NO, Açıklama, Miktar, Birim, FİYAT, Döviz Toplam, Toplam TL]
                            fiyat_cell = valid_cells[-3]
                        else:
                            fiyat_cell = valid_cells[-2]

                    birim_fiyat_val = parse_sayi(fiyat_cell.replace("₺", "").replace("TL", ""))

                    # 3. MİKTAR VE BİRİM TESPİTİ
                    mik = 0.0
                    birim = "Adet"
                    for idx, cell in enumerate(valid_cells):
                        m_birim = re.search(r"^(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S)$", cell, re.IGNORECASE)
                        if m_birim:
                            birim = cell
                            if idx > 0:
                                mik = parse_sayi(valid_cells[idx - 1])
                            break

                    if mik <= 0:
                        for cell in valid_cells[1:4]:
                            val = parse_sayi(cell)
                            if val > 0:
                                mik = val
                                break

                    if mik <= 0:
                        mik = 1.0

                    # 4. PARA BİRİMİ TESPİTİ
                    pb = "TRY"
                    if "€" in fiyat_cell or "EUR" in fiyat_cell.upper():
                        pb = "EUR"
                    elif "$" in fiyat_cell or "USD" in fiyat_cell.upper():
                        pb = "USD"
                    elif satir_toplam_tl > 0 and (mik * birim_fiyat_val) > 0:
                        oran = satir_toplam_tl / (mik * birim_fiyat_val)
                        if abs(oran - kur_eur) < 1.0 or abs(oran - 56.16) < 2.0:
                            pb = "EUR"
                        elif abs(oran - kur_usd) < 1.0 or abs(oran - 48.66) < 2.0:
                            pb = "USD"

                    # 5. AÇIKLAMA / MALZEME TANIMI
                    tanim = valid_cells[1] if not re.match(r"^\d+$", valid_cells[1]) else valid_cells[0]
                    tanim = re.sub(r"^\d+\s*[-_.]?\s*", "", tanim).strip()

                    # Geçerli satır ise ekle
                    if tanim and (birim_fiyat_val > 0 or satir_toplam_tl > 0):
                        kalemler.append({
                            "malzeme_adi": tanim,
                            "miktar": mik,
                            "birim": birim,
                            "birim_satis": birim_fiyat_val,   # <-- Doğrudan 450,00 ₺ olan Fiyat hücresi
                            "birim_fiyat": birim_fiyat_val,
                            "toplam": satir_toplam_tl,        # <-- 900,00 ₺ olan Toplam TL hücresi
                            "toplam_tl": satir_toplam_tl,
                            "para_birimi": pb,
                            "birim_maliyet": 0.0,
                            "maliyet_pb": pb,
                        })
                except Exception:
                    continue

        # Eğer dip toplam metinden alınamadıysa kalemlerin gerçek toplamını al
        if toplam_tutar <= 0 and kalemler:
            toplam_tutar = round(sum(k["toplam_tl"] for k in kalemler), 2)

        return {
            "teklif_kodu": teklif_kodu or "PT202600129",
            "musteri": musteri_adi or "Modüler Sistem Müşterisi",
            "musteri_iletisim": musteri_iletisim,
            "teklif_tarihi": teklif_tarihi,
            "muhendis": muhendis_adi or "Muhammed GÜNER",
            "konu": konu_adi or "MODÜLER MALZEME TEMİNİ",
            "kur_usd": kur_usd,
            "kur_eur": kur_eur,
            "toplam_tutar": round(toplam_tutar, 2),
            "para_birimi": "TRY",
            "kalemler": kalemler,
            "tam_metin": tam_metin
        }

    except Exception:
        return bos_sonuc



def extract_excel_full_with_cost_sheets(excel_file, kur_usd=48.7479, kur_eur=55.9390):
    sonuc = {
        "teklif_kodu": "",
        "musteri": "",
        "musteri_iletisim": "",
        "teklif_tarihi": "",
        "muhendis": "",
        "konu": "",
        "kur_usd": kur_usd,
        "kur_eur": kur_eur,
        "toplam_tutar": 0.0,
        "para_birimi": "TRY",
        "kalemler": [],
        "maliyet_sayfasi_bulundu": False,
        "bulunan_maliyet_sayfasi": ""
    }

    try:
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, header=None)
    except Exception:
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, header=None, engine="openpyxl")

    if not excel_sheets:
        return sonuc

    # 1. Aşama: Satış Sayfasını Bul
    satis_sheet_name = None
    df_satis = None

    for s_name, df_s in excel_sheets.items():
        tam_str = " ".join([str(v) for v in df_s.values.flatten() if pd.notna(v)]).lower()
        if any(k in tam_str for k in ["teklif no", "fiyat/teklif formu", "teklif talep", "toplam fiyat teklifi"]):
            satis_sheet_name = s_name
            df_satis = df_s
            break

    if df_satis is None:
        satis_sheet_name = list(excel_sheets.keys())[0]
        df_satis = excel_sheets[satis_sheet_name]

    # --- 2. Aşama: ANTETİ HÜCRE BAZINDA KESİN AYRIŞTIRMA ---
    # Başlıkları satır satır tara: Bir hücrede anahtar kelime varsa, sağındaki dolu hücre değerdir.
    for r_idx, row in df_satis.iloc[:25].iterrows():
        cells = [str(c).strip() for c in row.values if pd.notna(c) and str(c).strip() != ""]
        if not cells:
            continue

        for c_idx, cell in enumerate(cells):
            c_low = cell.lower().replace(":", "").strip()

            # Değer hücresini bulma (genelde bir sonraki hücredir, başında ':' olabilir)
            val = ""
            if c_idx + 1 < len(cells):
                val = cells[c_idx + 1].lstrip(":").strip()
            elif ":" in cell:
                # Başlık ve değer aynı hücreye yazılmışsa (Örn: "Teklif No : PT202600155")
                val = cell.split(":", 1)[1].strip()

            if not val or val.lower() in ["nan", "none"]:
                continue

            # Müşteri / Firma
            if any(k == c_low for k in ["teklif talep eden kişi/firma", "teklif talep eden kisi/firma", "müşteri", "musteri", "firma"]) and not sonuc["musteri"]:
                sonuc["musteri"] = val

            # Müşteri İletişim
            elif any(k in c_low for k in ["teklif talep eden iletişim", "teklif talep eden iletisim", "müşteri iletişim"]) and not sonuc["musteri_iletisim"]:
                sonuc["musteri_iletisim"] = val

            # Teklifin Konusu
            elif any(k in c_low for k in ["teklifin konusu", "konu", "işin adı", "isin adi"]) and not sonuc["konu"]:
                sonuc["konu"] = val

            # Teklif Tarihi
            elif any(k in c_low for k in ["teklif tarihi", "tarih"]) and not sonuc["teklif_tarihi"]:
                # 2026-09-16 00:00:00 formatındaki saat kısmını temizle
                clean_date = str(val).split()[0].replace("-", ".")
                sonuc["teklif_tarihi"] = clean_date

            # Teklif No
            elif any(k in c_low for k in ["teklif no", "teklif numarası", "teklif kodu"]) and not sonuc["teklif_kodu"]:
                m_kod = re.search(r"PT\d+", val, re.IGNORECASE)
                sonuc["teklif_kodu"] = m_kod.group(0).upper() if m_kod else val

            # Hazırlayan / Sorumlu Mühendis
            elif any(k in c_low for k in ["teklifi hazırlayan", "teklifi hazirlayan", "sorumlu mühendis", "hazırlayan"]) and not sonuc["muhendis"]:
                sonuc["muhendis"] = val

    # Dosya adından yedek kontrol
    if not sonuc["teklif_kodu"]:
        dosya_adi = getattr(excel_file, "name", "")
        m_fn = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
        if m_fn:
            sonuc["teklif_kodu"] = m_fn.group(0).upper()

    # --- 3. Aşama: Kalem Tablosu Başlık Satırını Bulma ve Kalemleri Çıkarma ---
    baslik_idx = -1
    for idx, row in df_satis.iloc[:35].iterrows():
        r_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
        if ("açıklama" in r_str or "aciklama" in r_str or "malzeme" in r_str) and any(f in r_str for f in ["fiyat", "miktar", "tutar"]):
            baslik_idx = idx
            break

    kalemler = []
    if baslik_idx != -1:
        for r_i, r in df_satis.iloc[baslik_idx + 1:].iterrows():
            # Satırdaki NaN olmayan dolu hücreleri sırayla alalım
            raw_cells = [str(c).replace("\n", " ").strip() for c in r.values if pd.notna(c) and str(c).strip() not in ["", "nan", "None"]]
            if len(raw_cells) < 3:
                continue

            row_line = " ".join(raw_cells).lower()
            # Alt bilgi ve dip toplam satırlarını kesinlikle atla
            if any(x in row_line for x in [
                "toplam", "güncel kur", "döviz toplam", "tl toplam", "teklif toplamı", 
                "kdv dahil", "opsiyon", "ödeme", "teslim süresi", "notlar"
            ]):
                continue

            # 1. Satır Numarasını (S.NO) Temizle
            if re.match(r"^\d+$", raw_cells[0]) and len(raw_cells) > 1:
                # İlk hücre sıra no ise geriye kalanları işle
                data_cells = raw_cells[1:]
            else:
                data_cells = raw_cells

            if len(data_cells) < 3:
                continue

            # 2. Malzeme Açıklamasını Bul (İçinde harf olan en uzun ilk hücre veya birleşim)
            tanim_parcalari = []
            kalan_hucreler = []
            tanim_bitti = False

            for c in data_cells:
                # Eğer hücre sadece sayısal/miktar/para birimi değilse tanımdır
                is_num = (parse_sayi(c) > 0 and re.match(r"^[\d\.,\s₺$€TL]+$", c))
                is_unit = bool(re.match(r"^(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S)$", c, re.IGNORECASE))

                if not tanim_bitti and not is_num and not is_unit:
                    tanim_parcalari.append(c)
                else:
                    tanim_bitti = True
                    kalan_hucreler.append(c)

            tanim = " ".join(tanim_parcalari).strip()
            if not tanim:
                continue

            # 3. Kalan Hücrelerden Miktar, Birim, Fiyat ve Toplamı Çek
            birim = "Adet"
            sayisal_degerler = []

            for c in kalan_hucreler:
                m_birim = re.search(r"\b(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S)\b", c, re.IGNORECASE)
                if m_birim:
                    birim = m_birim.group(1).capitalize()
                
                # Para veya miktar sayılarını topla
                val_num = parse_sayi(c)
                if val_num > 0 or c in ["0", "0,00", "0.00"]:
                    sayisal_degerler.append(val_num)

            if not sayisal_degerler:
                continue

            # Excel PetroTek Düzeni:
            # sayisal_degerler sırasıyla: [Miktar, Birim Fiyat, (varsa Döviz Toplam), Toplam TL]
            if len(sayisal_degerler) == 1:
                mik = 1.0
                b_fiyat = sayisal_degerler[0]
                toplam_tl = b_fiyat
            elif len(sayisal_degerler) == 2:
                mik = sayisal_degerler[0]
                b_fiyat = sayisal_degerler[1]
                toplam_tl = round(mik * b_fiyat, 2)
            elif len(sayisal_degerler) == 3:
                # [Miktar, Birim Fiyat, Toplam TL]
                mik = sayisal_degerler[0]
                b_fiyat = sayisal_degerler[1]
                toplam_tl = sayisal_degerler[2]
            else:
                # [Miktar, Birim Fiyat, Döviz Toplam, Toplam TL] (4 veya daha fazla)
                mik = sayisal_degerler[0]
                b_fiyat = sayisal_degerler[1]       # <-- İkinci sayı DOĞRUDAN Birim Fiyat sütunudur!
                toplam_tl = sayisal_degerler[-1]     # <-- En son sayı Toplam TL'dir

            if mik <= 0:
                mik = 1.0

            # 4. Para Birimi Kontrolü
            pb = "TRY"
            if "€" in row_line or "eur" in row_line:
                pb = "EUR"
            elif "$" in row_line or "usd" in row_line:
                pb = "USD"
            elif toplam_tl > 0 and (mik * b_fiyat) > 0:
                oran = toplam_tl / (mik * b_fiyat)
                if abs(oran - kur_eur) < 1.0 or abs(oran - 56.16) < 2.5:
                    pb = "EUR"
                elif abs(oran - kur_usd) < 1.0 or abs(oran - 48.66) < 2.5:
                    pb = "USD"

            kalemler.append({
                "malzeme_adi": tanim,
                "miktar": mik,
                "birim": birim,
                "birim_satis": b_fiyat,             # Gerçek birim satış fiyatı
                "birim_fiyat": b_fiyat,
                "toplam": toplam_tl,                # Gerçek toplam satış tutarı
                "toplam_tl": toplam_tl,
                "para_birimi": pb,
                "birim_maliyet": 0.0,
                "maliyet_pb": pb,
            })

    # --- 4. Aşama: Varsa Maliyet Sayfasından Eşleştirme ---
    maliyet_eslesen_adet = 0
    bulunan_sayfa = ""

    for s_name, df_other in excel_sheets.items():
        if s_name == satis_sheet_name:
            continue
        
        for _, r_oth in df_other.iterrows():
            oth_vals = [str(v).strip() for v in r_oth.values if pd.notna(v)]
            oth_line = " ".join(oth_vals).lower()
            
            for k in kalemler:
                k_ad_low = k["malzeme_adi"].lower()[:12]
                if k_ad_low in oth_line and k["birim_maliyet"] == 0.0:
                    nums = [parse_sayi(v) for v in oth_vals if parse_sayi(v) > 0]
                    if nums:
                        bulunan_maliyet = nums[0] if len(nums) == 1 else (nums[1] if nums[0] == k["miktar"] else nums[0])
                        k["birim_maliyet"] = bulunan_maliyet
                        if any(x in oth_line for x in ["€", "eur"]): k["maliyet_pb"] = "EUR"
                        elif any(x in oth_line for x in ["$", "usd"]): k["maliyet_pb"] = "USD"
                        else: k["maliyet_pb"] = "TRY"

                        maliyet_eslesen_adet += 1
                        bulunan_sayfa = s_name

    sonuc["kalemler"] = kalemler
    sonuc["toplam_tutar"] = sum(k["toplam_tl"] for k in kalemler)
    if maliyet_eslesen_adet > 0:
        sonuc["maliyet_sayfasi_bulundu"] = True
        sonuc["bulunan_maliyet_sayfasi"] = bulunan_sayfa

    return sonuc


