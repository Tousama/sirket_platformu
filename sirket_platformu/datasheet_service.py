import io
import re
from typing import Dict, Any, Optional, List

try:
    import pypdf
except ImportError:
    pypdf = None

# Sistemdeki kümülatif dinamik datasheet veritabanı
REGISTERED_DATASHEETS: Dict[str, Dict[str, Any]] = {}


def extract_engineering_parameters(context: str) -> Dict[str, str]:
    """Teknik metinden mühendislik parametrelerini ayıklar."""
    ctx_lower = context.lower()

    # 1. Koruma Sınıfı
    ip_match = re.search(r"\b(ip\s?6[5-9](?:/\d+)?|ip\s?6[5-9]/ip\s?6[5-9]|nema\s?4x)\b", ctx_lower)
    ip_val = ip_match.group(1).upper().replace(" ", "") if ip_match else "IP66/68"

    # 2. Ex-Proof Standardı
    ex_match = re.search(
        r"\b(atex[^\n,;]{0,35}|iecex[^\n,;]{0,35}|ex\s?[dia]{1,2}[^\n,;]{0,30}|ii\s?1/2\s?g[^\n,;]{0,30}|zone\s?20[^\n,;]{0,20})\b",
        ctx_lower
    )
    ex_val = ex_match.group(1).strip() if ex_match else "ATEX / IECEx Onaylı"
    if len(ex_val) > 35:
        ex_val = ex_val[:35] + "..."

    # 3. Proses Bağlantısı
    conn_match = re.search(
        r"((?:npt\s?\d+/\d+|\d+/\d+\"?\s*npt|dn\d+\s*pn\d+|flange\s*en\d+|thread\s*g\s*pn\d+|g\s?1-1/2|uni\s?3\")[^\n,;]{0,22})",
        ctx_lower
    )
    conn_val = conn_match.group(1).strip() if conn_match else "1/2\" NPT male"
    if len(conn_val) > 25:
        conn_val = conn_val[:25]

    # 4. Islak Parça Malzemeleri
    mat_match = re.search(r"\b(316l?|hastelloy|ptfe|pvdf|fkm|viton|paslanmaz)\b", ctx_lower)
    mat_val = mat_match.group(1).upper() + " SST" if mat_match else "316L SST"

    # 5. Sinyal Çıkışı
    sig_match = re.search(r"\b(4-20\s?ma\s?hart|4\.\.\.\s?20\s?ma/hart|4-20\s?ma|pfm|namur|spdt|dpdt|kuru\s?kontak|pt100)\b", ctx_lower)
    sig_val = sig_match.group(1).upper() if sig_match else "4-20 mA HART"

    # 6. Frekans & Emniyet
    freq_val = "80 GHz" if ("80 ghz" in ctx_lower or "80ghz" in ctx_lower or "puls 6x" in ctx_lower or "fmr6" in ctx_lower) else ""
    sil_val = "SIL2" if "sil" in ctx_lower else ""

    return {
        "koruma_sinifi": ip_val,
        "ex_proof": ex_val,
        "proses_baglantisi": conn_val,
        "islak_parcalar": mat_val,
        "cikis_sinyali": sig_val,
        "frekans": freq_val,
        "sil": sil_val,
    }


def detect_measurement_discipline(text: str) -> str:
    """Model adından veya metinden fiziksel ölçüm disiplinini kesin tespit eder."""
    t = text.lower()

    if any(w in t for w in ["puls", "fmr", "radar", "80 ghz", "80ghz", "temassız", "lit"]):
        return "radar"
    if any(w in t for w in ["swing", "ftl5", "ftl", "liquiphant", "şalter", "vibronic", "fork", "çatal", "ls"]):
        return "switch"
    if any(w in t for w in ["cerabar", "pmp", "pmc", "basınç", "pressure", "pit", "ps"]):
        return "basinc"
    if any(w in t for w in ["tm131", "itherm", "pt100", "rtd", "thermocouple", "sıcaklık", "temperature", "te"]):
        return "sicaklik"
    if any(w in t for w in ["vegator", "nivotester", "ftl325", "barrier", "bariyer"]):
        return "bariyer"

    return "genel"


def is_invalid_device_name(name: str) -> bool:
    """Adres, tarih, banka ve teklif başlıklarını kesin filtreler."""
    n = name.strip().upper()

    if len(n) < 4:
        return True

    digits = sum(c.isdigit() for c in n)
    if digits > len(n) * 0.45:
        return True

    aylar_ve_tarih = [
        "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", 
        "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK", 
        "2024", "2025", "2026"
    ]
    if any(ay in n for ay in aylar_ve_tarih):
        return True

    adres_ve_idari = [
        "MAHALLE", "MAHALLESI", "SOKAK", "SOK", "CADDE", "APARTMAN", "KAT", "DAIRE",
        "YENISEHIR", "YENİŞEHİR", "MERSIN", "ICEL", "İSTANBUL", "CIVIL KULE", "MALTEPE",
        "ŞUBE", "SUBESI", "UBESI", "UBESİ", "GARANTI", "ZIRAAT", "BANKASI", "HURRIYET", "HÜRRİYET",
        "OF 8", "OF 5", "OF 11", "GECIKME", "FAIZI", "FEMALE", "THREAD", "BIRIM FIYAT",
        "NET DEGER", "TOPLAM", "EUR", "TRY", "USD", "KILOGRAM", "TELEFON", "FAKS", "IBAN",
        "TICARET", "VERGI", "SICIL", "PETROTEK", "ENDRESS", "HAUSER", "VEGA HOME", "VALUES"
    ]
    return any(w in n for w in adres_ve_idari)


def parse_multipage_pdf_datasheets(
    file_name: str, 
    file_bytes: bytes, 
    target_bom_items: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Yüklenen PDF içerisinden sadece onaylanmış gerçek enstrümanları ayıklar."""
    found_records = []
    if not pypdf:
        return found_records

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        page_texts = [p.extract_text() or "" for p in reader.pages]

        detected_devices: Dict[str, Dict[str, Any]] = {}

        # 1. VEGA Teklifleri
        vega_pattern = re.compile(
            r"(?:Poz\.|Pozisyon)?\s*\d+\s*(?:\d+)?\s*(VEGAPULS\s+[A-Z0-9]+|VEGASWING\s+[A-Z0-9]+|VEGATOR\s+[A-Z0-9]+)", 
            re.IGNORECASE
        )

        # 2. Endress+Hauser Teklifleri
        eh_pattern = re.compile(
            r"(?:Poz\.|Pozisyon)?\s*\d+\s*(?:\d+\s*PC)?\s*(Micropilot\s+[A-Z0-9]+|Cerabar\s+[A-Z0-9]+|Liquiphant\s+[A-Z0-9]+|Nivotester\s+[A-Z0-9]+|iTHERM\s+(?:ModuLine\s+)?[A-Z0-9]+)", 
            re.IGNORECASE
        )

        # 3. Global Markalar
        vendor_pattern = re.compile(
            r"\b(ROSEMOUNT\s+[0-9]{3,4}[A-Z]?|SITRANS\s+[A-Z0-9]+|OPTIWAVE\s+[0-9]{3,4}|OPTISWITCH\s+[0-9]{3,4}|EJX[0-9]{3}[A-Z]?|EJA[0-9]{3}[A-Z]?)\b", 
            re.IGNORECASE
        )

        for p_idx, p_txt in enumerate(page_texts):
            # VEGA Cihazları
            for m in vega_pattern.finditer(p_txt):
                name = m.group(1).strip().upper()
                if not is_invalid_device_name(name) and name not in detected_devices:
                    ctx = p_txt + ("\n" + page_texts[p_idx + 1] if p_idx + 1 < total_pages else "")
                    disc = detect_measurement_discipline(name)
                    detected_devices[name] = {
                        "marka": "VEGA",
                        "model": name,
                        "kategori": disc,
                        "cihaz_tipi": f"Saha Enstrümanı ({disc.title()})",
                        "datasheet_dosyasi": f"{file_name} (S.{p_idx + 1})",
                        "teknik_parametreler": extract_engineering_parameters(ctx)
                    }

            # Endress+Hauser Cihazları
            for m in eh_pattern.finditer(p_txt):
                name = " ".join(m.group(1).strip().split()).upper()
                if not is_invalid_device_name(name) and name not in detected_devices:
                    ctx = p_txt + ("\n" + page_texts[p_idx + 1] if p_idx + 1 < total_pages else "")
                    disc = detect_measurement_discipline(name)
                    detected_devices[name] = {
                        "marka": "Endress+Hauser",
                        "model": name,
                        "kategori": disc,
                        "cihaz_tipi": f"Saha Enstrümanı ({disc.title()})",
                        "datasheet_dosyasi": f"{file_name} (S.{p_idx + 1})",
                        "teknik_parametreler": extract_engineering_parameters(ctx)
                    }

            # Diğer Global Markalar
            for m in vendor_pattern.finditer(p_txt):
                name = m.group(1).strip().upper()
                if not is_invalid_device_name(name) and name not in detected_devices:
                    ctx = p_txt + ("\n" + page_texts[p_idx + 1] if p_idx + 1 < total_pages else "")
                    disc = detect_measurement_discipline(name)
                    detected_devices[name] = {
                        "marka": "Global Üretici",
                        "model": name,
                        "kategori": disc,
                        "cihaz_tipi": f"Saha Enstrümanı ({disc.title()})",
                        "datasheet_dosyasi": f"{file_name} (S.{p_idx + 1})",
                        "teknik_parametreler": extract_engineering_parameters(ctx)
                    }

        for m_name, data in detected_devices.items():
            REGISTERED_DATASHEETS[m_name] = data
            found_records.append(data)

    except Exception:
        pass

    return found_records


def get_compatible_devices_for_item(item_name: str) -> List[Dict[str, Any]]:
    """
    Teklif kaleminin fiziksel disiplinine uyan cihazları döner.
    Örn: Radar ise YALNIZCA Radar föylerini döner (Asla Switch veya Basınç karışmaz).
    """
    target_disc = detect_measurement_discipline(item_name)
    compatible = []

    for key, data in REGISTERED_DATASHEETS.items():
        dev_disc = data.get("kategori", "")
        # Disiplinler birebir aynı olmalı
        if target_disc != "genel" and dev_disc == target_disc:
            compatible.append(data)
        # Disiplin genel ise tam ad eşleşmesine bak
        elif target_disc == "genel" and (key.lower() in item_name.lower() or item_name.lower() in key.lower()):
            compatible.append(data)

    return compatible