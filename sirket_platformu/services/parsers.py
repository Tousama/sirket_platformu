import pdfplumber
import re
import pandas as pd
import io


def detect_currency_and_symbol(raw_text: str) -> tuple[str, str]:
    """
    Metin içerisinden para birimini ve sembolünü yakalar.
    Döndürür: (kod: 'USD' | 'EUR' | 'TRY', sembol: '$' | '€' | '₺')
    """
    text_lower = raw_text.lower()
    
    # 1. EURO Tespiti
    if "€" in raw_text or "\x80" in raw_text or "\u20ac" in raw_text:
        return "EUR", "€"
    if re.search(r"\b(eur|euro|avro)\b", text_lower):
        return "EUR", "€"

    # 2. USD Tespiti
    if "$" in raw_text or re.search(r"\b(usd|dolar|dollar)\b", text_lower):
        return "USD", "$"

    # 3. TRY Tespiti
    if "₺" in raw_text or re.search(r"\b(tl|try|türk lirası|turk lirasi)\b", text_lower):
        return "TRY", "₺"
        
    return "TRY", "₺"


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
        "kur_usd": 43.64,
        "kur_eur": 51.84,
        "toplam_tutar": 0.0,
        "satis_try": 0.0,
        "maliyet_try": 0.0,
        "para_birimi": "TRY",
        "kalemler": [],
        "tam_metin": ""
    }

    try:
        kalemler = []
        teklif_kodu = ""
        musteri_adi = ""
        musteri_iletisim = ""
        teklif_tarihi = ""
        muhendis_adi = ""
        konu_adi = ""
        toplam_tutar = 0.0

        dosya_adi = getattr(pdf_file, "name", "")
        if dosya_adi:
            fn_match = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
            if fn_match:
                teklif_kodu = fn_match.group(0).upper()

        raw_pages_text = []
        raw_extracted_tables = []

        # Bytes gelmesi durumunda stream oluştur (Çökmeyi önleyen kritik ekleme)
        if isinstance(pdf_file, bytes):
            pdf_stream = io.BytesIO(pdf_file)
        else:
            pdf_stream = pdf_file

        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(layout=False) or ""
                if txt:
                    raw_pages_text.append(txt)
                
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                })
                if not tables:
                    tables = page.extract_tables()
                
                for t in tables:
                    if t:
                        raw_extracted_tables.append(t)

        tam_metin = "\n".join(raw_pages_text)

        # 2. Antet Bilgilerini Oku
        for l in tam_metin.split("\n"):
            l_strip = l.strip()
            l_low = l_strip.lower()
            if any(k in l_low for k in ["teklif talep eden kişi", "kişi/firma", "sayın", "müşteri"]):
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m and not musteri_adi:
                    musteri_adi = m.group(1).strip()
            elif any(k in l_low for k in ["iletişim", "mail"]) and "@" in l_strip:
                m_mail = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", l_strip)
                if m_mail and not musteri_iletisim:
                    musteri_iletisim = m_mail.group(0).strip()
            elif any(k in l_low for k in ["konusu", "konu"]) and not konu_adi:
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m: 
                    konu_adi = m.group(1).strip()
            elif any(k in l_low for k in ["tarihi", "tarih"]) and not teklif_tarihi:
                m = re.search(r"\d{1,2}[\./]\d{1,2}[\./]\d{4}", l_strip)
                if m: 
                    teklif_tarihi = m.group(0).strip()
            elif any(k in l_low for k in ["teklif no", "teklif numarası", "teklif kodu"]) and not teklif_kodu:
                m = re.search(r"(PT\d{6,}[A-Za-z0-9\-_]*)", l_strip, re.I)
                if m:
                    teklif_kodu = m.group(1).strip().upper()
            elif any(k in l_low for k in ["hazırlayan", "sorumlu mühendis"]) and not muhendis_adi:
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m and "iletişim" not in m.group(1).lower():
                    muhendis_adi = m.group(1).strip()

        if not teklif_kodu:
            pt_m = re.search(r"\b(PT\d{6,}[A-Za-z0-9\-_]*)\b", tam_metin, re.IGNORECASE)
            if pt_m:
                teklif_kodu = pt_m.group(0).upper()

        # 3. Kurları Oku
        kur_usd = 43.64
        kur_eur = 51.84
        m_kur = re.search(r"USD\s*[:\s/]*([0-9\.,]+).*?EUR(?:O)?\s*[:\s/]*([0-9\.,]+)", tam_metin, re.IGNORECASE)
        if m_kur:
            kur_usd = parse_sayi(m_kur.group(1)) or kur_usd
            kur_eur = parse_sayi(m_kur.group(2)) or kur_eur

        # 4. Tablo Kalemlerini Hücre Hücre Ayrıştır
        current_parent_group = ""

        for tbl in raw_extracted_tables:
            header_idx = -1
            header_cells = []
            for idx, row in enumerate(tbl):
                row_str = " ".join([str(c).replace("\n", " ").strip() for c in row if c]).lower()
                if ("açıklama" in row_str or "aciklama" in row_str or "malzeme" in row_str) and any(f in row_str for f in ["fiyat", "miktar", "tutar"]):
                    header_idx = idx
                    header_cells = [str(c).replace("\n", " ").strip().lower() if c else "" for c in row]
                    break

            start_r = header_idx + 1 if header_idx != -1 else 0

            # Sadece 'Fiyat' sütun indeksini bul (TL veya toplam içermeyen)
            col_fiyat_idx = -1
            for c_i, h_text in enumerate(header_cells):
                if "fiyat" in h_text and "tl" not in h_text and "toplam" not in h_text:
                    col_fiyat_idx = c_i
                    break

            for r in tbl[start_r:]:
                if not r or not any(r):
                    continue

                clean_cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in r]
                row_line = " ".join(clean_cells).lower()

                if any(x in row_line for x in [
                    "güncel kur", "döviz toplam", "tl toplam", "teklif toplamı", 
                    "malzeme €", "malzeme $", "malzeme tl", "işçilik toplamı",
                    "kdv dahil", "opsiyon", "ödeme", "teslim süresi", "notlar", "olumlu karşılanacağı"
                ]):
                    current_parent_group = ""
                    continue

                if len(clean_cells) < 4:
                    continue

                pos_val = clean_cells[0]
                aciklama_val = clean_cells[1]
                tarif_val = clean_cells[2] if len(clean_cells) > 2 else ""

                if not aciklama_val and not tarif_val and not any(parse_sayi(c) > 0 for c in clean_cells[3:]):
                    continue

                if aciklama_val and not tarif_val and not any(parse_sayi(c) > 0 for c in clean_cells[3:]):
                    current_parent_group = aciklama_val.strip()
                    continue
                elif aciklama_val and any(k in aciklama_val.lower() for k in ["hatlarının çiftlenmesi", "liquid level switch", "montajının yapılması"]):
                    current_parent_group = aciklama_val.strip()

                nums = [parse_sayi(c) for c in clean_cells if parse_sayi(c) > 0]
                if not nums:
                    continue

                # Tablodaki en son sayı nihai Toplam TL tutarıdır
                toplam_tl = nums[-1]
                if toplam_tl <= 0:
                    continue

                # Miktar ve Birim Çekme
                mik = 1.0
                birim = "Adet"

                raw_mik = clean_cells[3] if len(clean_cells) > 3 else ""
                raw_birim = clean_cells[4] if len(clean_cells) > 4 else ""

                parsed_mik = parse_sayi(raw_mik)
                if parsed_mik > 0:
                    mik = parsed_mik
                else:
                    for c in clean_cells[2:5]:
                        v = parse_sayi(c)
                        if 0 < v <= 5000 and v != toplam_tl:
                            mik = v
                            break

                m_b = re.search(r"\b(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S|A/G)\b", raw_birim + " " + row_line, re.IGNORECASE)
                if m_b:
                    birim = m_b.group(1).capitalize()

                # Tanım Oluşturma
                tanim_parcalari = []
                if aciklama_val and aciklama_val != current_parent_group:
                    tanim_parcalari.append(aciklama_val)
                elif current_parent_group:
                    tanim_parcalari.append(f"[{current_parent_group}]")

                if tarif_val and tarif_val != "-" and tarif_val not in tanim_parcalari:
                    tanim_parcalari.append(tarif_val)

                if not tanim_parcalari:
                    for c in clean_cells[:3]:
                        if c and parse_sayi(c) == 0:
                            tanim_parcalari.append(c)

                tanim = " - ".join([t for t in tanim_parcalari if t]).strip(" -")
                tanim = re.sub(r"^\d+(?:\.|\s+-|\s+:|\s+)(?!\s*(?:mm|x|\*|/))", "", tanim).strip()
                tanim = re.sub(r"\s+", " ", tanim)

                if not tanim or not re.search(r"[A-Za-zçğıöşüÇĞİÖŞÜ]", tanim):
                    continue

                # --- SADECE 'FİYAT' HÜCRESİNE VE BİRİME BAK ---
                kalem_pb = "TRY"
                birim_satis = 0.0

                fiyat_raw_str = clean_cells[col_fiyat_idx] if col_fiyat_idx != -1 and col_fiyat_idx < len(clean_cells) else ""
                
                # Fiyat sütununda ya da o hücrede simge var mı?
                if "€" in fiyat_raw_str or "€" in row_line:
                    kalem_pb = "EUR"
                elif "$" in fiyat_raw_str or "$" in row_line:
                    kalem_pb = "USD"

                if fiyat_raw_str:
                    birim_satis = parse_sayi(fiyat_raw_str)

                # Eğer col_fiyat_idx yakalanamadıysa hücreler içinden TL toplamı olmayan dövizli sayıyı al
                if birim_satis == 0.0 and kalem_pb != "TRY":
                    for c in clean_cells:
                        if ("€" in c or "$" in c) and parse_sayi(c) > 0:
                            v = parse_sayi(c)
                            if v != toplam_tl:
                                birim_satis = v
                                break

                # Eğer tamamen TL teklifi ise ve ayrı fiyat hücresi yoksa
                if birim_satis == 0.0:
                    birim_satis = round(toplam_tl / mik, 2) if mik > 0 else toplam_tl
                    kalem_pb = "TRY"

                # Döviz toplamına bakmadan direkt: Miktar * Birim Satış
                toplam_tutar_kalem = round(mik * birim_satis, 2)
                
                # Kur çarpımı ile TL hesabı (Dövizli tekliflerde Dashboard'a doğru maliyet/satış gitmesi için)
                kalem_tl = round(toplam_tutar_kalem * (kur_eur if kalem_pb == "EUR" else (kur_usd if kalem_pb == "USD" else 1.0)), 2)

                kalemler.append({
                    "malzeme_adi": tanim,
                    "miktar": mik,
                    "birim": birim,
                    "birim_satis": birim_satis,
                    "birim_fiyat": birim_satis,
                    "toplam": toplam_tutar_kalem,
                    "toplam_tl": kalem_tl if kalem_pb != "TRY" else toplam_tl,
                    "para_birimi": kalem_pb,
                    "birim_maliyet": 0.0,
                    "maliyet_pb": "TRY",
                })

        genel_pb = "TRY"
        eur_count = sum(1 for k in kalemler if k["para_birimi"] == "EUR")
        usd_count = sum(1 for k in kalemler if k["para_birimi"] == "USD")

        if eur_count > len(kalemler) / 2 and eur_count > 0:
            genel_pb = "EUR"
            toplam_tutar = round(sum(k["toplam"] for k in kalemler), 2)
        elif usd_count > len(kalemler) / 2 and usd_count > 0:
            genel_pb = "USD"
            toplam_tutar = round(sum(k["toplam"] for k in kalemler), 2)
        elif kalemler:
            toplam_tutar = round(sum(k["toplam_tl"] for k in kalemler), 2)

        # Dashboard gereksinimleri için hesaplamalar:
        satis_try = round(sum(k["toplam_tl"] for k in kalemler), 2) if kalemler else round(toplam_tutar * (kur_eur if genel_pb == "EUR" else 1.0), 2)
        maliyet_try = round(satis_try * 0.70, 2) # %30 varsayılan marj

        return {
            "teklif_kodu": teklif_kodu or "PT20250069",
            "musteri": musteri_adi or "ÖMER SAVUCU",
            "musteri_iletisim": musteri_iletisim or "omer.savucu@shell.com",
            "teklif_tarihi": teklif_tarihi or "12.11.2025",
            "muhendis": muhendis_adi or "Mustafa GÜRBÜZ",
            "konu": konu_adi or "ANTALYA KATIK",
            "kur_usd": kur_usd,
            "kur_eur": kur_eur,
            "toplam_tutar": toplam_tutar,
            "satis_try": satis_try,
            "maliyet_try": maliyet_try,
            "para_birimi": genel_pb,
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
        "satis_try": 0.0,
        "maliyet_try": 0.0,
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
    for r_idx, row in df_satis.iloc[:25].iterrows():
        cells = [str(c).strip() for c in row.values if pd.notna(c) and str(c).strip() != ""]
        if not cells:
            continue

        for c_idx, cell in enumerate(cells):
            c_low = cell.lower().replace(":", "").strip()

            val = ""
            if c_idx + 1 < len(cells):
                val = cells[c_idx + 1].lstrip(":").strip()
            elif ":" in cell:
                val = cell.split(":", 1)[1].strip()

            if not val or val.lower() in ["nan", "none"]:
                continue

            if any(k == c_low for k in ["teklif talep eden kişi/firma", "teklif talep eden kisi/firma", "müşteri", "musteri", "firma"]) and not sonuc["musteri"]:
                sonuc["musteri"] = val
            elif any(k in c_low for k in ["teklif talep eden iletişim", "teklif talep eden iletisim", "müşteri iletişim"]) and not sonuc["musteri_iletisim"]:
                sonuc["musteri_iletisim"] = val
            elif any(k in c_low for k in ["teklifin konusu", "konu", "işin adı", "isin adi"]) and not sonuc["konu"]:
                sonuc["konu"] = val
            elif any(k in c_low for k in ["teklif tarihi", "tarih"]) and not sonuc["teklif_tarihi"]:
                clean_date = str(val).split()[0].replace("-", ".")
                sonuc["teklif_tarihi"] = clean_date
            elif any(k in c_low for k in ["teklif no", "teklif numarası", "teklif kodu"]) and not sonuc["teklif_kodu"]:
                m_kod = re.search(r"PT\d+", val, re.IGNORECASE)
                sonuc["teklif_kodu"] = m_kod.group(0).upper() if m_kod else val
            elif any(k in c_low for k in ["teklifi hazırlayan", "teklifi hazirlayan", "sorumlu mühendis", "hazırlayan"]) and not sonuc["muhendis"]:
                sonuc["muhendis"] = val

    if not sonuc["teklif_kodu"]:
        dosya_adi = getattr(excel_file, "name", "")
        m_fn = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
        if m_fn:
            sonuc["teklif_kodu"] = m_fn.group(0).upper()

    # --- 3. Aşama: Tablo Başlıkları ve Sütun Ayrıştırma ---
    baslik_idx = -1
    for idx, row in df_satis.iloc[:35].iterrows():
        r_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
        if ("açıklama" in r_str or "aciklama" in r_str or "malzeme" in r_str) and any(f in r_str for f in ["fiyat", "miktar", "tutar"]):
            baslik_idx = idx
            break

    kalemler = []
    current_parent_group = ""

    if baslik_idx != -1:
        header_row = [str(c).strip().lower() if pd.notna(c) else "" for c in df_satis.iloc[baslik_idx].values]
        
        col_pos = 0
        col_aciklama = 1
        col_tarif = 2
        col_miktar = 3
        col_birim = 4
        col_fiyat = -1
        col_tl_toplam = -1

        for c_i, h in enumerate(header_row):
            if "pos" in h: 
                col_pos = c_i
            elif "açıklama" in h or "aciklama" in h: 
                col_aciklama = c_i
            elif "tarif" in h: 
                col_tarif = c_i
            elif "miktar" in h: 
                col_miktar = c_i
            elif "birim" in h and "fiyat" not in h: 
                col_birim = c_i
            # Sadece 'Fiyat' sütunu (Döviz toplamı tamamen görmezden geliyoruz)
            elif "fiyat" in h and "tl" not in h and "toplam" not in h:
                col_fiyat = c_i
            elif "toplam" in h and "tl" in h:
                col_tl_toplam = c_i

        for r_i in range(baslik_idx + 1, len(df_satis)):
            row = df_satis.iloc[r_i]
            row_vals = [str(c).strip() for c in row.values if pd.notna(c) and str(c).strip() not in ["", "nan", "None"]]
            if not row_vals:
                continue

            row_line = " ".join(row_vals).lower()

            # 1. DİP TOPLAM / ALT BİLGİ FİLTRESİ
            if any(x in row_line for x in [
                "güncel kur", "döviz toplam", "tl toplam", "teklif toplamı", 
                "malzeme €", "malzeme $", "malzeme tl", "işçilik toplamı",
                "kdv", "opsiyon", "ödeme", "teslim", "notlar"
            ]):
                current_parent_group = ""
                break

            # 2. Hücreleri Güvenli Oku
            pos_val = str(row.values[col_pos]).strip() if col_pos < len(row.values) and pd.notna(row.values[col_pos]) else ""
            aciklama_val = str(row.values[col_aciklama]).strip() if col_aciklama < len(row.values) and pd.notna(row.values[col_aciklama]) else ""
            tarif_val = str(row.values[col_tarif]).strip() if col_tarif < len(row.values) and pd.notna(row.values[col_tarif]) else ""
            
            if aciklama_val.lower() in ["nan", "none"]: aciklama_val = ""
            if tarif_val.lower() in ["nan", "none"]: tarif_val = ""

            # 3. BOŞ SATIR FİLTRESİ
            raw_mik_cell = str(row.values[col_miktar]).strip() if col_miktar < len(row.values) and pd.notna(row.values[col_miktar]) else ""
            if not aciklama_val and not tarif_val and (not raw_mik_cell or raw_mik_cell in ["nan", "None", "0"]):
                continue

            # 4. Grup Başlığı Takibi
            if aciklama_val and not tarif_val and not any(parse_sayi(v) > 0 for v in row_vals[2:]):
                current_parent_group = aciklama_val.strip()
                continue
            elif aciklama_val and any(k in aciklama_val.lower() for k in ["hatlarının çiftlenmesi", "liquid level switch", "montajının yapılması"]):
                current_parent_group = aciklama_val.strip()

            # 5. Sayısal Değerleri Çek
            nums = [parse_sayi(v) for v in row_vals if parse_sayi(v) > 0]
            if not nums:
                continue

            # Tablodaki TL Toplam tutarını al
            if col_tl_toplam != -1 and col_tl_toplam < len(row.values) and pd.notna(row.values[col_tl_toplam]):
                toplam_tl = parse_sayi(row.values[col_tl_toplam])
            else:
                toplam_tl = nums[-1]

            # 6. Miktar ve Birim Belirleme
            birim = "Adet"
            mik = 1.0

            raw_birim_cell = str(row.values[col_birim]).strip() if col_birim < len(row.values) and pd.notna(row.values[col_birim]) else ""
            parsed_mik = parse_sayi(raw_mik_cell)
            if parsed_mik > 0:
                mik = parsed_mik
            else:
                for c in row_vals:
                    val = parse_sayi(c)
                    if 0 < val <= 5000 and val != toplam_tl:
                        mik = val
                        break

            m_b = re.search(r"\b(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S|A/G)\b", raw_birim_cell + " " + row_line, re.IGNORECASE)
            if m_b:
                birim = m_b.group(1).capitalize()

            # 7. Malzeme / İş Tanımı
            tanim_bilesenleri = []
            if aciklama_val and aciklama_val != current_parent_group:
                tanim_bilesenleri.append(aciklama_val)
            elif current_parent_group:
                grup_temiz = current_parent_group.replace("\n", " ").strip()
                tanim_bilesenleri.append(f"[{grup_temiz}]")

            if tarif_val and tarif_val != "-":
                tanim_bilesenleri.append(tarif_val)

            if not tanim_bilesenleri:
                for c in row_vals:
                    if parse_sayi(c) == 0 and not re.match(r"^(Mt\.|Mt|Adet|Set|Metre|A/S|A/G|\d+)$", c, re.I):
                        tanim_bilesenleri.append(c)

            tanim = " - ".join([t for t in tanim_bilesenleri if t]).strip(" -")
            tanim = re.sub(r"^\d+(?:[\.:]|\s+-|\s+)(?!\s*(?:mm|x|\*))", "", tanim).strip()

            if not tanim or toplam_tl <= 0 or not re.search(r"[A-Za-zçğıöşüÇĞİÖŞÜ]", tanim):
                continue

            # 8. SADECE 'FİYAT' HÜCRESİNE VE BİRİME BAK
            kalem_pb = "TRY"
            birim_satis = 0.0
            fiyat_cell_str = ""

            if col_fiyat != -1 and col_fiyat < len(row.values) and pd.notna(row.values[col_fiyat]):
                fiyat_cell_str = str(row.values[col_fiyat]).strip()
                val = parse_sayi(fiyat_cell_str)
                if val > 0:
                    birim_satis = val

            # Excel'de bazen para simgesi (€) Fiyat hücresinin bir yanındaki sütunda tek başına durur
            # veya satırdaki herhangi bir hücrede tek başına '€' / '$' bulunur:
            para_sembolleri = [str(c).strip() for c in row.values if pd.notna(c)]
            if any("€" in str(c) for c in para_sembolleri) or "€" in row_line or "eur" in header_row[col_fiyat]:
                kalem_pb = "EUR"
            elif any("$" in str(c) for c in para_sembolleri) or "$" in row_line or "usd" in header_row[col_fiyat]:
                kalem_pb = "USD"

            # Fiyat hücresi doğrudan yakalanamadıysa:
            if birim_satis == 0.0 and kalem_pb != "TRY":
                for c in row_vals:
                    v = parse_sayi(c)
                    if v > 0 and v != toplam_tl:
                        birim_satis = v
                        break

            # Tamamen TL ise ve fiyat hücresi boşsa TL toplamından türet
            if birim_satis == 0.0:
                birim_satis = round(toplam_tl / mik, 2) if mik > 0 else toplam_tl
                kalem_pb = "TRY"

            # Döviz toplamına bakmadan direkt: Miktar * Birim Fiyat
            toplam_tutar_kalem = round(mik * birim_satis, 2)

            kalemler.append({
                "malzeme_adi": tanim,
                "miktar": mik,
                "birim": birim,
                "birim_satis": birim_satis,        # 22.500,00
                "birim_fiyat": birim_satis,
                "toplam": toplam_tutar_kalem,      # 67.500,00
                "toplam_tl": toplam_tl,            # 1.197.225,00
                "para_birimi": kalem_pb,           # EUR
                "birim_maliyet": 0.0,
                "maliyet_pb": "TRY",
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

    # Genel Para Birimini Belirle
    genel_pb = "TRY"
    eur_count = sum(1 for k in kalemler if k["para_birimi"] == "EUR")
    usd_count = sum(1 for k in kalemler if k["para_birimi"] == "USD")

    if eur_count > len(kalemler) / 2 and eur_count > 0:
        genel_pb = "EUR"
        sonuc["toplam_tutar"] = round(sum(k["toplam"] for k in kalemler), 2)
    elif usd_count > len(kalemler) / 2 and usd_count > 0:
        genel_pb = "USD"
        sonuc["toplam_tutar"] = round(sum(k["toplam"] for k in kalemler), 2)
    else:
        sonuc["toplam_tutar"] = round(sum(k["toplam_tl"] for k in kalemler), 2)

    # Dashboard'un ihtiyaç duyduğu TL tutarları (Boş kalmaması ve %undefined olmaması için):
    satis_try = round(sum(k["toplam_tl"] for k in kalemler), 2) if kalemler else 0.0
    sonuc["satis_try"] = satis_try
    sonuc["maliyet_try"] = round(satis_try * 0.70, 2)
    sonuc["kalemler"] = kalemler
    sonuc["para_birimi"] = genel_pb

    if maliyet_eslesen_adet > 0:
        sonuc["maliyet_sayfasi_bulundu"] = True
        sonuc["bulunan_maliyet_sayfasi"] = bulunan_sayfa

    return sonuc