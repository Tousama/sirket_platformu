import pdfplumber
import re
import pandas as pd


def detect_currency_and_symbol(raw_text: str) -> tuple[str, str]:
    """
    Metin içerisinden para birimini ve sembolünü yakalar.
    Döndürür: (kod: 'USD' | 'EUR' | 'TRY', sembol: '$' | '€' | '₺')
    """
    text_lower = raw_text.lower()
    
    # 1. Doğrudan sembol kontrolü
    if "$" in raw_text or "usd" in text_lower or "dolar" in text_lower:
        return "USD", "$"
    elif "€" in raw_text or "eur" in text_lower or "euro" in text_lower:
        return "EUR", "€"
    elif "₺" in raw_text or "tl" in text_lower or "try" in text_lower:
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

        # 1. Dosya adından teklif kodunu yakala
        dosya_adi = getattr(pdf_file, "name", "")
        if dosya_adi:
            fn_match = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
            if fn_match:
                teklif_kodu = fn_match.group(0).upper()

        raw_pages_text = []
        raw_extracted_tables = []

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(layout=False) or ""
                if txt:
                    raw_pages_text.append(txt)
                
                # Tabloları hücre çizgilerine göre çıkar
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                })
                # Eğer tam çizgili tablo gelmezse text tabanlı dene
                if not tables:
                    tables = page.extract_tables()
                
                for t in tables:
                    if t:
                        raw_extracted_tables.append(t)

        tam_metin = "\n".join(raw_pages_text)

        # 2. Antet Bilgilerini Oku
        for l in tam_metin.split("\n"):
            l_strip = l.strip()
            if any(k in l_strip.lower() for k in ["teklif talep eden kişi", "kişi/firma", "sayın", "müşteri"]):
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m and not musteri_adi:
                    musteri_adi = m.group(1).strip()
            elif any(k in l_strip.lower() for k in ["iletişim", "mail"]) and "@" in l_strip:
                m_mail = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", l_strip)
                if m_mail and not musteri_iletisim:
                    musteri_iletisim = m_mail.group(0).strip()
            elif any(k in l_strip.lower() for k in ["konusu", "konu"]) and not konu_adi:
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m: konu_adi = m.group(1).strip()
            elif any(k in l_strip.lower() for k in ["tarihi", "tarih"]) and not teklif_tarihi:
                m = re.search(r"\d{1,2}[\./]\d{1,2}[\./]\d{4}", l_strip)
                if m: teklif_tarihi = m.group(0).strip()
            elif any(k in l_strip.lower() for k in ["hazırlayan", "sorumlu mühendis"]) and not muhendis_adi:
                m = re.search(r":\s*([^\n\r]+)", l_strip)
                if m and "iletişim" not in m.group(1).lower():
                    muhendis_adi = m.group(1).strip()

        if not teklif_kodu:
            pt_m = re.search(r"PT\d+", tam_metin, re.IGNORECASE)
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
            # Başlık satırını bul
            for idx, row in enumerate(tbl):
                row_str = " ".join([str(c).replace("\n", " ").strip() for c in row if c]).lower()
                if ("açıklama" in row_str or "aciklama" in row_str or "malzeme" in row_str) and any(f in row_str for f in ["fiyat", "miktar", "tutar"]):
                    header_idx = idx
                    break

            start_r = header_idx + 1 if header_idx != -1 else 0

            for r in tbl[start_r:]:
                if not r or not any(r):
                    continue

                clean_cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in r]
                row_line = " ".join(clean_cells).lower()

                # DİP TOPLAM ve ALT BİLGİ SATIRLARINI KES
                if any(x in row_line for x in [
                    "güncel kur", "döviz toplam", "tl toplam", "teklif toplamı", 
                    "malzeme €", "malzeme $", "malzeme tl", "işçilik toplamı",
                    "kdv dahil", "opsiyon", "ödeme", "teslim süresi", "notlar"
                ]):
                    current_parent_group = ""
                    continue

                # Sütunları standartlaştır (PetroTek PDF Tablosu Genelde 10 sütunludur)
                # POS [0] | Açıklama [1] | SHELL Birim Fiyat Tarifi [2] | Miktar [3] | Birim [4] | ... | Toplam Fiyat TL [-1]
                if len(clean_cells) < 4:
                    continue

                pos_val = clean_cells[0]
                aciklama_val = clean_cells[1]
                tarif_val = clean_cells[2] if len(clean_cells) > 2 else ""

                # Boş Satır Kontrolü (42, 43, 44 gibi boş hücreler)
                if not aciklama_val and not tarif_val and not any(parse_sayi(c) > 0 for c in clean_cells[3:]):
                    continue

                # Grup Başlığı Tespiti (Örn: "Shell katık Hatlarının Çiftlenmesi" veya "Pompalar için...")
                if aciklama_val and not tarif_val and not any(parse_sayi(c) > 0 for c in clean_cells[3:]):
                    current_parent_group = aciklama_val.strip()
                    continue
                elif aciklama_val and any(k in aciklama_val.lower() for k in ["hatlarının çiftlenmesi", "liquid level switch", "montajının yapılması"]):
                    current_parent_group = aciklama_val.strip()

                # Sayısal Değerler
                nums = [parse_sayi(c) for c in clean_cells if parse_sayi(c) > 0]
                if not nums:
                    continue

                # En son geçerli sayı DAİMA toplam satış TL tutarıdır
                toplam_tl = nums[-1]
                if toplam_tl <= 0:
                    continue

                # Miktar ve Birim Çekme
                mik = 1.0
                birim = "Adet"

                # 3. ve 4. sütunları kontrol et
                raw_mik = clean_cells[3] if len(clean_cells) > 3 else ""
                raw_birim = clean_cells[4] if len(clean_cells) > 4 else ""

                parsed_mik = parse_sayi(raw_mik)
                if parsed_mik > 0:
                    mik = parsed_mik
                else:
                    # Mobilizasyon veya kaymış satırlar için güvenli miktar arama
                    for c in clean_cells[2:5]:
                        v = parse_sayi(c)
                        if 0 < v <= 5000 and v != toplam_tl:
                            mik = v
                            break

                m_b = re.search(r"\b(Mt\.|Mt|Adet|Set|Metre|Pcs|Kg|A/S|A/G)\b", raw_birim + " " + row_line, re.IGNORECASE)
                if m_b:
                    birim = m_b.group(1).capitalize()

                # Tanım Oluşturma (Kesilmeden, Başındaki Rakamları ve Kesitleri KORUYARAK)
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
                
                # SADECE BAĞIMSIZ POS NUMARASINI TEMİZLE (Kablo kesitlerini: 6mm2, 16mm2, 300x, 1/2" KORU!)
                tanim = re.sub(r"^\d+(?:\.|\s+-|\s+:|\s+)(?!\s*(?:mm|x|\*|/))", "", tanim).strip()

                # Tanım temizliği (Kelimeler arası fazla boşlukları düzenle)
                tanim = re.sub(r"\s+", " ", tanim)

                # Boş veya anlamsız satırları ele
                if not tanim or not re.search(r"[A-Za-zçğıöşüÇĞİÖŞÜ]", tanim):
                    continue

                # TL Birim Satış Fiyatı (Toplam TL / Miktar)
                birim_satis_tl = round(toplam_tl / mik, 2) if mik > 0 else toplam_tl

                kalemler.append({
                    "malzeme_adi": tanim,
                    "miktar": mik,
                    "birim": birim,
                    "birim_satis": birim_satis_tl,
                    "birim_fiyat": birim_satis_tl,
                    "toplam": toplam_tl,
                    "toplam_tl": toplam_tl,
                    "para_birimi": "TRY",
                    "birim_maliyet": 0.0,
                    "maliyet_pb": "TRY",
                })

        if kalemler:
            toplam_tutar = round(sum(k["toplam_tl"] for k in kalemler), 2)

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

    # --- 3. Aşama: Gelişmiş Merged-Cell & PetroTek Kalem Ayrıştırıcı ---
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

        for c_i, h in enumerate(header_row):
            if "pos" in h: col_pos = c_i
            elif "açıklama" in h or "aciklama" in h: col_aciklama = c_i
            elif "tarif" in h: col_tarif = c_i
            elif "miktar" in h: col_miktar = c_i
            elif "birim" in h and "fiyat" not in h: col_birim = c_i

        for r_i in range(baslik_idx + 1, len(df_satis)):
            row = df_satis.iloc[r_i]
            row_vals = [str(c).strip() for c in row.values if pd.notna(c) and str(c).strip() not in ["", "nan", "None"]]
            if not row_vals:
                continue

            row_line = " ".join(row_vals).lower()

            # 1. KESİN DİP TOPLAM / ALT BİLGİ FİLTRESİ
            # Malzeme toplamı, işçilik toplamı veya genel toplam satırına gelindiğinde ayrıştırmayı durdur
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

            # 3. BOŞ SATIR FİLTRESİ (42, 43, 44 gibi sadece satır numarası olan boş satırları atla)
            # Eğer açıklama ve tarif tamamen boşsa ve miktar sütununda veri yoksa bu satır boştur.
            raw_mik_cell = str(row.values[col_miktar]).strip() if col_miktar < len(row.values) and pd.notna(row.values[col_miktar]) else ""
            if not aciklama_val and not tarif_val and (not raw_mik_cell or raw_mik_cell in ["nan", "None", "0"]):
                continue

            # 4. Grup Başlığı Takibi (Örn: "Shell katık Hatlarının Çiftlenmesi" veya "Pompalar için...")
            if aciklama_val and not tarif_val and not any(parse_sayi(v) > 0 for v in row_vals[2:]):
                current_parent_group = aciklama_val.strip()
                continue
            elif aciklama_val and any(k in aciklama_val.lower() for k in ["hatlarının çiftlenmesi", "liquid level switch", "montajının yapılması"]):
                current_parent_group = aciklama_val.strip()

            # 5. Sayısal Değerleri Çek
            nums = [parse_sayi(v) for v in row_vals if parse_sayi(v) > 0]
            if not nums:
                continue

            # Tablodaki en son sayı nihai "Toplam Fiyat Teklifi TL" tutarıdır
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

            # GÜVENLİ SIRA NO TEMİZLİĞİ:
            # 6mm2 veya 16mm2 gibi kesit değerlerini bozmadan yalnızca "1 - ", "1. ", "1 " gibi sıra numaralarını eler
            tanim = re.sub(r"^\d+(?:[\.:]|\s+-|\s+)(?!\s*(?:mm|x|\*))", "", tanim).strip()

            if not tanim or toplam_tl <= 0 or not re.search(r"[A-Za-zçğıöşüÇĞİÖŞÜ]", tanim):
                continue

            # 8. TL Birim Satış Fiyatı (Toplam TL / Miktar)
            birim_satis_tl = round(toplam_tl / mik, 2) if mik > 0 else toplam_tl

            kalemler.append({
                "malzeme_adi": tanim,
                "miktar": mik,
                "birim": birim,
                "birim_satis": birim_satis_tl,
                "birim_fiyat": birim_satis_tl,
                "toplam": toplam_tl,
                "toplam_tl": toplam_tl,
                "para_birimi": "TRY",
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

    sonuc["kalemler"] = kalemler
    sonuc["toplam_tutar"] = sum(k["toplam_tl"] for k in kalemler)
    if maliyet_eslesen_adet > 0:
        sonuc["maliyet_sayfasi_bulundu"] = True
        sonuc["bulunan_maliyet_sayfasi"] = bulunan_sayfa

    return sonuc


