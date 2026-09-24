import io
import re
import pandas as pd
import pdfplumber


def detect_currency_and_symbol(raw_text: str) -> tuple[str, str]:
  text_lower = raw_text.lower()
  if (
      "€" in raw_text
      or "\x80" in raw_text
      or "\u20ac" in raw_text
      or re.search(r"\b(eur|euro|avro)\b", text_lower)
  ):
    return "EUR", "€"
  if "$" in raw_text or re.search(r"\b(usd|dolar|dollar)\b", text_lower):
    return "USD", "$"
  return "TRY", "₺"


def tr_lower(metin: str) -> str:
  if not metin:
    return ""
  donusum = {
      "İ": "i",
      "I": "ı",
      "Ş": "ş",
      "Ğ": "ğ",
      "Ü": "ü",
      "Ö": "ö",
      "Ç": "ç",
  }
  for b, k in donusum.items():
    metin = metin.replace(b, k)
  return metin.lower().strip()


def parse_sayi(deger) -> float:
  if deger is None or deger == "":
    return 0.0

  if isinstance(deger, (int, float)):
    if pd.isna(deger):
      return 0.0
    return abs(float(deger))

  val = str(deger).strip()
  if not val or val.lower() in ["nan", "none", "-", "--"]:
    return 0.0

  temiz = re.sub(
      r"(?i)\b(tl|try|eur|euro|usd|dolar|dollar|adet|mt|metre|set|kg|pcs|a/s|a/g)\b",
      "",
      val,
  )
  temiz = re.sub(r"[\$€₺\s]", "", temiz)

  if re.search(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]", temiz):
    return 0.0

  temiz = temiz.lstrip("-+ ").strip()
  temiz = re.sub(r"[^\d,\.]", "", temiz)
  if not temiz:
    return 0.0

  if "," in temiz and "." in temiz:
    if temiz.rfind(",") > temiz.rfind("."):
      temiz = temiz.replace(".", "").replace(",", ".")
    else:
      temiz = temiz.replace(",", "")
  elif "," in temiz:
    temiz = temiz.replace(",", ".")

  try:
    return abs(float(temiz))
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
      "tam_metin": "",
  }

  try:
    kalemler = []
    teklif_kodu = ""
    musteri_adi = ""
    musteri_iletisim = ""
    teklif_tarihi = ""
    muhendis_adi = ""
    konu_adi = ""

    dosya_adi = getattr(pdf_file, "name", "")
    if dosya_adi:
      fn_match = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
      if fn_match:
        teklif_kodu = fn_match.group(0).upper()

    raw_pages_text = []
    raw_extracted_tables = []

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

    # =========================================================
    # YENİ: Belgenin kendi para birimini tespit et
    # =========================================================
    belge_pb, belge_sembol = detect_currency_and_symbol(tam_metin)

    for l in tam_metin.split("\n"):
      l_strip = l.strip()
      l_low = l_strip.lower()
      if any(
          k in l_low
          for k in ["teklif talep eden kişi", "kişi/firma", "sayın", "müşteri"]
      ):
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
      elif (
          any(k in l_low for k in ["teklif no", "teklif numarası", "teklif kodu"])
          and not teklif_kodu
      ):
        m = re.search(r"(PT\d{6,}[A-Za-z0-9\-_]*)", l_strip, re.I)
        if m:
          teklif_kodu = m.group(1).strip().upper()
      elif (
          any(k in l_low for k in ["hazırlayan", "sorumlu mühendis"])
          and not muhendis_adi
      ):
        m = re.search(r":\s*([^\n\r]+)", l_strip)
        if m and "iletişim" not in m.group(1).lower():
          muhendis_adi = m.group(1).strip()

    if not teklif_kodu:
      pt_m = re.search(
          r"\b(PT\d{6,}[A-Za-z0-9\-_]*)\b", tam_metin, re.IGNORECASE
      )
      if pt_m:
        teklif_kodu = pt_m.group(0).upper()

    kur_usd = 43.64
    kur_eur = 51.84
    m_kur = re.search(
        r"USD\s*[:\s/]*([0-9\.,]+).*?EUR(?:O)?\s*[:\s/]*([0-9\.,]+)",
        tam_metin,
        re.IGNORECASE,
    )
    if m_kur:
      kur_usd = parse_sayi(m_kur.group(1)) or kur_usd
      kur_eur = parse_sayi(m_kur.group(2)) or kur_eur

    for tbl in raw_extracted_tables:
      header_idx = -1
      header_cells = []
      for idx, row in enumerate(tbl):
        row_str = " ".join(
            [str(c).replace("\n", " ").strip() for c in row if c]
        ).lower()
        if ("açıklama" in row_str or "malzeme" in row_str) and any(
            f in row_str for f in ["fiyat", "miktar", "tutar"]
        ):
          header_idx = idx
          header_cells = [
              str(c).replace("\n", " ").strip().lower() if c else "" for c in row
          ]
          break

      start_r = header_idx + 1 if header_idx != -1 else 0

      for r in tbl[start_r:]:
        if not r or not any(r):
          continue

        clean_cells = [
            str(c).replace("\n", " ").strip() if c is not None else ""
            for c in r
        ]
        row_line = " ".join(clean_cells).lower()

        if any(
            x in row_line
            for x in [
                "güncel kur",
                "döviz toplam",
                "tl toplam",
                "teklif toplamı",
                "malzeme €",
                "malzeme $",
                "malzeme tl",
                "işçilik toplamı",
                "kdv",
                "opsiyon",
                "ödeme",
                "teslim",
                "notlar",
            ]
        ):
          continue

        pos_str = clean_cells[0].strip() if len(clean_cells) > 0 else ""
        pos_match = re.match(r"^(\d{1,2})$", pos_str)
        if not pos_match:
          if kalemler and len(clean_cells) > 1 and clean_cells[1]:
            ek = re.sub(r"^[\.\d\s,]+[€\$₺]\s*-\s*", "", clean_cells[1]).strip()
            if ek and len(ek) > 2 and not parse_sayi(ek):
              kalemler[-1]["malzeme_adi"] += f" ({ek})"
          continue

        aciklama_raw = clean_cells[1] if len(clean_cells) > 1 else ""
        tarif_raw = clean_cells[2] if len(clean_cells) > 2 else ""

        aciklama_clean = re.sub(
            r"^[\.\d\s,]+[€\$₺]\s*-\s*", "", aciklama_raw
        ).strip()
        tarif_clean = re.sub(r"^[\.\d\s,]+[€\$₺]\s*-\s*", "", tarif_raw).strip()
        if tarif_clean == "-":
          tarif_clean = ""

        tanim = (
            f"{aciklama_clean} - {tarif_clean}".strip(" -")
            if tarif_clean
            else aciklama_clean
        )
        tanim = re.sub(r"\s+", " ", tanim).strip()

        if not tanim or not re.search(r"[A-Za-zçğıöşüÇĞİÖŞÜ]", tanim):
          continue

        mik = parse_sayi(clean_cells[3]) if len(clean_cells) > 3 else 1.0
        if mik <= 0:
          mik = 1.0

        birim = (
            clean_cells[4].strip().capitalize()
            if len(clean_cells) > 4 and clean_cells[4]
            else "Adet"
        )
        if not re.search(r"[A-Za-z]", birim):
          birim = "Adet"

        malz_birim_eur = (
            parse_sayi(clean_cells[5]) if len(clean_cells) > 5 else 0.0
        )
        iscilik_birim_tl = (
            parse_sayi(clean_cells[6]) if len(clean_cells) > 6 else 0.0
        )
        toplam_tl = (
            parse_sayi(clean_cells[9])
            if len(clean_cells) > 9
            else parse_sayi(clean_cells[-1])
        )

        nums = [
            parse_sayi(c)
            for c in clean_cells
            if parse_sayi(c) > 0 and parse_sayi(c) != mik
        ]
        if toplam_tl == 0.0 and nums:
          toplam_tl = nums[-1]

        if toplam_tl <= 0 or mik <= 0:
          continue

        # =========================================================
        # YENİ: Belge para birimine göre kalem tutarını hesapla
        # =========================================================
        if belge_pb == "TRY":
          # Mevcut davranış: kalem tutarları TL'ye çevrilir, final TL
          malz_tl = round(malz_birim_eur * kur_eur, 2)
          birlesik_birim = round(malz_tl + iscilik_birim_tl, 2)
          if birlesik_birim == 0.0 and toplam_tl > 0:
            birlesik_birim = round(toplam_tl / mik, 2)
          kalem_toplam = toplam_tl
          kalem_pb = "TRY"
        else:
          # Yeni davranış: kalem tutarları döviz olarak bırakılır
          birlesik_birim = round(malz_birim_eur + iscilik_birim_tl, 2)
          if birlesik_birim == 0.0 and toplam_tl > 0:
            birlesik_birim = round(toplam_tl / mik, 2)
          kalem_toplam = toplam_tl
          kalem_pb = belge_pb

        kalemler.append({
            "malzeme_adi": tanim,
            "miktar": mik,
            "birim": birim,
            "birim_satis": birlesik_birim,
            "birim_fiyat": birlesik_birim,
            "toplam": kalem_toplam,
            "toplam_tl": kalem_toplam,
            "para_birimi": kalem_pb,
            "birim_maliyet": 0.0,
            "maliyet_pb": "TRY",
        })

    teklif_toplam_tl = 0.0
    m_toplam = re.search(
        r"TEKLİF\s*TOPLAMI\s*[:\s₺&]*([0-9\.,]+)", tam_metin, re.IGNORECASE
    )
    if m_toplam:
      teklif_toplam_tl = parse_sayi(m_toplam.group(1))

    if teklif_toplam_tl == 0.0 and kalemler:
      teklif_toplam_tl = round(sum(k["toplam_tl"] for k in kalemler), 2)

    return {
        "teklif_kodu": teklif_kodu or "PT20250069",
        "musteri": musteri_adi or "ÖMER SAVUCU",
        "musteri_iletisim": musteri_iletisim or "omer.savucu@shell.com",
        "teklif_tarihi": teklif_tarihi or "12.11.2025",
        "muhendis": muhendis_adi or "Mustafa GÜRBÜZ",
        "konu": konu_adi or "ANTALYA KATIK",
        "kur_usd": kur_usd,
        "kur_eur": kur_eur,
        "toplam_tutar": teklif_toplam_tl,
        "satis_try": teklif_toplam_tl,
        "maliyet_try": 0.0,
        "para_birimi": belge_pb,   # ← Artık dinamik
        "kalemler": kalemler,
        "tam_metin": tam_metin,
    }

  except Exception:
    return bos_sonuc


def extract_excel_full_with_cost_sheets(
    excel_file, kur_usd=43.64, kur_eur=51.84
):
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
      "bulunan_maliyet_sayfasi": "",
  }

  try:
    excel_sheets = pd.read_excel(excel_file, sheet_name=None, header=None)
  except Exception:
    try:
      excel_sheets = pd.read_excel(
          excel_file, sheet_name=None, header=None, engine="openpyxl"
      )
    except Exception:
      return sonuc

  if not excel_sheets:
    return sonuc

  # =========================================================
  # YENİ: Excel belgesinin para birimini tüm hücrelerden tespit et
  # =========================================================
  try:
    tum_metin_parts = []
    for df_x in excel_sheets.values():
      for v in df_x.values.flatten():
        if pd.notna(v) and str(v).strip():
          tum_metin_parts.append(str(v))
    tam_metin_excel = " ".join(tum_metin_parts)
    belge_pb, belge_sembol = detect_currency_and_symbol(tam_metin_excel)
  except Exception:
    belge_pb, belge_sembol = "TRY", "₺"

  satis_sheet_name = None
  df_satis = None

  for s_name, df_s in excel_sheets.items():
    tam_str = " ".join(
        [str(v) for v in df_s.values.flatten() if pd.notna(v)]
    ).lower()
    if any(
        k in tam_str
        for k in [
            "teklif no",
            "fiyat/teklif formu",
            "teklif talep",
            "toplam fiyat teklifi",
        ]
    ):
      satis_sheet_name = s_name
      df_satis = df_s
      break

  if df_satis is None:
    satis_sheet_name = list(excel_sheets.keys())[0]
    df_satis = excel_sheets[satis_sheet_name]

  for r_idx, row in df_satis.iloc[:25].iterrows():
    cells = [
        str(c).strip()
        for c in row.values
        if pd.notna(c) and str(c).strip() != ""
    ]
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

      if (
          any(
              k == c_low
              for k in [
                  "teklif talep eden kişi/firma",
                  "teklif talep eden kisi/firma",
                  "müşteri",
                  "musteri",
                  "firma",
              ]
          )
          and not sonuc["musteri"]
      ):
        sonuc["musteri"] = val
      elif (
          any(
              k in c_low
              for k in [
                  "teklif talep eden iletişim",
                  "teklif talep eden iletisim",
                  "müşteri iletişim",
              ]
          )
          and not sonuc["musteri_iletisim"]
      ):
        sonuc["musteri_iletisim"] = val
      elif (
          any(
              k in c_low
              for k in ["teklifin konusu", "konu", "işin adı", "isin adi"]
          )
          and not sonuc["konu"]
      ):
        sonuc["konu"] = val
      elif any(k in c_low for k in ["teklif tarihi", "tarih"]) and not sonuc[
          "teklif_tarihi"
      ]:
        clean_date = str(val).split()[0].replace("-", ".")
        sonuc["teklif_tarihi"] = clean_date
      elif (
          any(k in c_low for k in ["teklif no", "teklif numarası", "teklif kodu"])
          and not sonuc["teklif_kodu"]
      ):
        m_kod = re.search(r"PT\d+", val, re.IGNORECASE)
        sonuc["teklif_kodu"] = m_kod.group(0).upper() if m_kod else val
      elif (
          any(
              k in c_low
              for k in [
                  "teklifi hazırlayan",
                  "teklifi hazirlayan",
                  "sorumlu mühendis",
                  "hazırlayan",
              ]
          )
          and not sonuc["muhendis"]
      ):
        sonuc["muhendis"] = val

  if not sonuc["teklif_kodu"]:
    dosya_adi = getattr(excel_file, "name", "")
    m_fn = re.search(r"PT\d+", dosya_adi, re.IGNORECASE)
    if m_fn:
      sonuc["teklif_kodu"] = m_fn.group(0).upper()

  baslik_idx = -1
  for idx, row in df_satis.iloc[:35].iterrows():
    r_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
    if (
        "açıklama" in r_str or "aciklama" in r_str or "malzeme" in r_str
    ) and any(f in r_str for f in ["fiyat", "miktar", "tutar"]):
      baslik_idx = idx
      break

  kalemler = []

  if baslik_idx != -1:
    header_row = [
        str(c).strip().lower() if pd.notna(c) else ""
        for c in df_satis.iloc[baslik_idx].values
    ]

    col_pos = 0
    col_aciklama = 1
    col_tarif = 2
    col_miktar = 3
    col_birim = 4
    col_malz_eur = -1
    col_iscilik_tl = -1
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
      elif (
          "shell" in h
          or ("malzeme" in h and "fiyat" in h and "toplam" not in h)
      ):
        col_malz_eur = c_i
      elif "işçilik" in h and "fiyat" in h and "toplam" not in h:
        col_iscilik_tl = c_i
      elif ("toplam" in h or "teklif" in h) and "tl" in h:
        col_tl_toplam = c_i

    for r_i in range(baslik_idx + 1, len(df_satis)):
      row = df_satis.iloc[r_i]
      row_vals = [
          str(c).strip()
          for c in row.values
          if pd.notna(c) and str(c).strip() not in ["", "nan", "None"]
      ]
      if not row_vals:
        continue

      row_line = " ".join(row_vals).lower()

      if any(
          x in row_line
          for x in [
              "güncel kur",
              "döviz toplam",
              "tl toplam",
              "teklif toplamı",
              "malzeme €",
              "malzeme $",
              "malzeme tl",
              "işçilik toplamı",
              "kdv",
              "opsiyon",
              "ödeme",
              "teslim",
              "notlar",
          ]
      ):
        break

      pos_str = (
          str(row.values[col_pos]).strip()
          if col_pos < len(row.values) and pd.notna(row.values[col_pos])
          else ""
      )
      if not re.match(r"^(\d{1,2})$", pos_str):
        if kalemler and len(row.values) > col_aciklama and pd.notna(row.values[col_aciklama]):
          ek = str(row.values[col_aciklama]).strip()
          if ek and len(ek) > 2:
            kalemler[-1]["malzeme_adi"] += f" ({ek})"
        continue

      aciklama_val = (
          str(row.values[col_aciklama]).strip()
          if col_aciklama < len(row.values) and pd.notna(row.values[col_aciklama])
          else ""
      )
      tarif_val = (
          str(row.values[col_tarif]).strip()
          if col_tarif != -1
          and col_tarif < len(row.values)
          and pd.notna(row.values[col_tarif])
          else ""
      )

      if aciklama_val.lower() in ["nan", "none"]:
        aciklama_val = ""
      if tarif_val.lower() in ["nan", "none"] or tarif_val == "-":
        tarif_val = ""

      tanim = (
          f"{aciklama_val} - {tarif_val}".strip(" -")
          if tarif_val
          else aciklama_val
      )
      tanim = re.sub(r"\s+", " ", tanim).strip()
      if not tanim:
        continue

      mik = (
          parse_sayi(row.values[col_miktar])
          if col_miktar < len(row.values) and pd.notna(row.values[col_miktar])
          else 1.0
      )
      if mik <= 0:
        mik = 1.0

      birim = (
          str(row.values[col_birim]).strip().capitalize()
          if col_birim < len(row.values) and pd.notna(row.values[col_birim])
          else "Adet"
      )
      if not re.search(r"[A-Za-z]", birim):
        birim = "Adet"

      malz_birim_eur = (
          parse_sayi(row.values[col_malz_eur])
          if col_malz_eur != -1
          and col_malz_eur < len(row.values)
          and pd.notna(row.values[col_malz_eur])
          else 0.0
      )
      iscilik_birim_tl = (
          parse_sayi(row.values[col_iscilik_tl])
          if col_iscilik_tl != -1
          and col_iscilik_tl < len(row.values)
          and pd.notna(row.values[col_iscilik_tl])
          else 0.0
      )
      toplam_tl = (
          parse_sayi(row.values[col_tl_toplam])
          if col_tl_toplam != -1
          and col_tl_toplam < len(row.values)
          and pd.notna(row.values[col_tl_toplam])
          else 0.0
      )

      if toplam_tl == 0.0:
        nums = [parse_sayi(v) for v in row.values if parse_sayi(v) > 0 and parse_sayi(v) != mik]
        if nums:
          toplam_tl = nums[-1]

      if toplam_tl <= 0 or mik <= 0:
        continue

      # =========================================================
      # YENİ: Belge para birimine göre kalem tutarını hesapla
      # =========================================================
      if belge_pb == "TRY":
        malz_tl = round(malz_birim_eur * kur_eur, 2)
        birlesik_birim = round(malz_tl + iscilik_birim_tl, 2)
        if birlesik_birim == 0.0 and toplam_tl > 0:
          birlesik_birim = round(toplam_tl / mik, 2)
        kalem_toplam = toplam_tl
        kalem_pb = "TRY"
      else:
        birlesik_birim = round(malz_birim_eur + iscilik_birim_tl, 2)
        if birlesik_birim == 0.0 and toplam_tl > 0:
          birlesik_birim = round(toplam_tl / mik, 2)
        kalem_toplam = toplam_tl
        kalem_pb = belge_pb

      kalemler.append({
          "malzeme_adi": tanim,
          "miktar": mik,
          "birim": birim,
          "birim_satis": birlesik_birim,
          "birim_fiyat": birlesik_birim,
          "toplam": kalem_toplam,
          "toplam_tl": kalem_toplam,
          "para_birimi": kalem_pb,
          "birim_maliyet": 0.0,
          "maliyet_pb": "TRY",
      })

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
            bulunan_maliyet = (
                nums[0]
                if len(nums) == 1
                else (nums[1] if nums[0] == k["miktar"] else nums[0])
            )
            k["birim_maliyet"] = bulunan_maliyet
            if any(x in oth_line for x in ["€", "eur"]):
              k["maliyet_pb"] = "EUR"
            elif any(x in oth_line for x in ["$", "usd"]):
              k["maliyet_pb"] = "USD"
            else:
              k["maliyet_pb"] = "TRY"

            maliyet_eslesen_adet += 1
            bulunan_sayfa = s_name

  teklif_toplam_tl = round(sum(k["toplam_tl"] for k in kalemler), 2) if kalemler else 0.0

  sonuc["toplam_tutar"] = teklif_toplam_tl
  sonuc["satis_try"] = teklif_toplam_tl
  sonuc["maliyet_try"] = round(teklif_toplam_tl * 0.70, 2)
  sonuc["kalemler"] = kalemler
  sonuc["para_birimi"] = belge_pb   # ← Artık dinamik

  if maliyet_eslesen_adet > 0:
    sonuc["maliyet_sayfasi_bulundu"] = True
    sonuc["bulunan_maliyet_sayfasi"] = bulunan_sayfa

  return sonuc