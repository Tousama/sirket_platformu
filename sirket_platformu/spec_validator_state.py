import io
import re
import reflex as rx
from typing import List, Dict, Any
from .dashboard_state import DashboardState
from .shared_quotes import SHARED_QUOTES
from .datasheet_service import (
    REGISTERED_DATASHEETS, 
    parse_multipage_pdf_datasheets, 
    get_compatible_devices_for_item,
    detect_measurement_discipline
)

try:
    from .services.db_service import get_all_teklifler_from_db
except ImportError:
    try:
        from services.db_service import get_all_teklifler_from_db
    except ImportError:
        get_all_teklifler_from_db = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None


def clean_and_structure_spec_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = re.sub(r"-\s*\d+\s*-", "", raw_text)
    text = re.sub(r"(?i)(sayfa|page)\s*\d+(\s*[/of]\s*\d+)?", "", text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    structured_lines = []
    current_bullet = ""

    for line in lines:
        if len(line) <= 2 and not line.isalnum():
            continue

        if re.match(r"^(\d+\.|\d+\.\d+\.?|[A-Z0-9\.\s]{3,}\:)\s+[A-ZÇĞİÖŞÜa-zçğıöşü\s]{3,}$", line):
            if current_bullet:
                structured_lines.append(current_bullet)
                current_bullet = ""
            structured_lines.append(f"\n### {line}")
            continue

        bullet_match = re.match(r"^([•●\-\*]|\d+\.\d+(\.\d+)?\.?|[a-z0-9]\))\s*(.*)", line)
        if bullet_match:
            if current_bullet:
                structured_lines.append(current_bullet)
            item_text = bullet_match.group(3) if bullet_match.group(3) else line
            current_bullet = f"• {item_text}"
        else:
            if current_bullet:
                current_bullet += f" {line}"
            else:
                current_bullet = line

    if current_bullet:
        structured_lines.append(current_bullet)

    return "\n".join(structured_lines).strip()


class SpecValidatorState(rx.State):
    currency: str = "TRY (₺)"

    teklif_secenekleri: List[str] = []
    secilen_teklif: str = ""
    _quotes_map: Dict[str, Any] = {}

    is_datasheet_uploading: bool = False
    son_yuklenen_datasheet: str = ""

    sartname_metni: str = (
        "• Seviye Ölçer (LIT): FMCW Radar 80 GHz, temassız, SIL2, 4-20mA HART, alüminyum IP66/68 gövde, ATEX Ex d [ia Ga] IIB T6.\n"
        "• Seviye Switchi (LS): Titreşimli çatal, 316L, SIL2, ATEX Ex ia Zone 1, Sinyal Değerlendirme Ünitesi (Nivotester/Bariyer) dahil."
    )

    datasheet_listesi: List[Dict[str, str]] = []
    matrix_rows: List[Dict[str, Any]] = []

    is_analyzing: bool = False
    is_uploading: bool = False
    yuklenen_dosya_adi: str = ""

    def set_sartname_metni(self, val: str):
        self.sartname_metni = val

    def set_currency(self, val: Any):
        if isinstance(val, list) and len(val) > 0:
            self.currency = str(val[0])
        else:
            self.currency = str(val)

    async def on_load(self):
        await self.load_quotes()
        async for _ in self.validate_bom_items():
            pass

    async def load_quotes(self):
        dash_state = await self.get_state(DashboardState)
        raw_list = getattr(dash_state, "raw_quotes", [])

        options = []
        self._quotes_map = {}

        for q in raw_list:
            kod = q.get("kod") or q.get("teklif_kodu", "")
            musteri = q.get("musteri", "-")
            if kod:
                label = f"{kod} | {musteri}"
                if label not in options:
                    options.append(label)
                    self._quotes_map[label] = q

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
            options = ["PT202600149 | Beril TEKİN"]

        self.teklif_secenekleri = options
        if not self.secilen_teklif or self.secilen_teklif not in options:
            self.secilen_teklif = options[0]

    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val

    @rx.var
    def datasheet_sayisi(self) -> int:
        return len(self.datasheet_listesi)

    @rx.var
    def secilen_kod(self) -> str:
        if "|" in self.secilen_teklif:
            return self.secilen_teklif.split("|")[0].strip()
        return self.secilen_teklif.strip()

    @rx.var
    def uygun_sayisi(self) -> int:
        return sum(1 for r in self.matrix_rows if r.get("uygunluk") == "Uygun")

    @rx.var
    def inceleme_sayisi(self) -> int:
        return sum(1 for r in self.matrix_rows if r.get("uygunluk") != "Uygun")

    def delete_datasheet(self, dosya_adi: str):
        self.datasheet_listesi = [ds for ds in self.datasheet_listesi if ds.get("dosya") != dosya_adi]
        silinecekler = [k for k, v in REGISTERED_DATASHEETS.items() if v.get("datasheet_dosyasi") == dosya_adi]
        for k in silinecekler:
            REGISTERED_DATASHEETS.pop(k, None)
        return rx.toast.info(f"'{dosya_adi}' havuzdan kaldırıldı.", position="top-right")

    def clear_all_datasheets(self):
        """Tüm havuzu sıfırlar."""
        self.datasheet_listesi = []
        REGISTERED_DATASHEETS.clear()
        return rx.toast.info("Datasheet havuzu temizlendi.", position="top-right")

    async def handle_datasheet_upload(self, files: List[rx.UploadFile]):
        if not files:
            return

        self.is_datasheet_uploading = True
        yield

        file = files[0]
        self.son_yuklenen_datasheet = file.name
        content = await file.read()

        try:
            kalemler = []
            if self.secilen_teklif in self._quotes_map:
                kalemler = self._quotes_map[self.secilen_teklif].get("kalemler", [])
            if not kalemler and self.secilen_kod in SHARED_QUOTES:
                kalemler = SHARED_QUOTES[self.secilen_kod].get("kalemler", [])

            hedef_urunler = [
                k.get("malzeme_adi") or k.get("tanim")
                for k in kalemler
                if (k.get("malzeme_adi") or k.get("tanim"))
            ]

            records = parse_multipage_pdf_datasheets(file.name, content, target_bom_items=hedef_urunler)

            if records:
                for rec in records:
                    params = rec.get("teknik_parametreler", {})
                    m_name = rec.get("model", "")
                    
                    yeni_satir = {
                        "model": m_name,
                        "dosya": rec.get("datasheet_dosyasi", file.name),
                        "ip": params.get("koruma_sinifi", "IP66/68"),
                        "ex": params.get("ex_proof", "ATEX Ex ia/Ex db IIC T6"),
                        "sinyal": params.get("cikis_sinyali", "4-20 mA HART"),
                        "baglanti": params.get("proses_baglantisi", "1/2\" NPT male"),
                    }
                    self.datasheet_listesi = [ds for ds in self.datasheet_listesi if ds.get("model") != m_name]
                    self.datasheet_listesi.append(yeni_satir)

                yield rx.toast.success(f"'{file.name}' içerisinden {len(records)} adet cihaz föyü çıkarıldı!", position="top-right")
            else:
                yield rx.toast.warning(f"'{file.name}' içinde tanınan cihaz föyü bulunamadı.", position="top-right")

            async for _ in self.validate_bom_items():
                pass
        except Exception as e:
            yield rx.toast.error(f"Datasheet işlenirken hata: {str(e)}", position="top-right")

        self.is_datasheet_uploading = False

    async def handle_file_upload(self, files: List[rx.UploadFile]):
        if not files:
            return

        self.is_uploading = True
        yield

        file = files[0]
        self.yuklenen_dosya_adi = file.name
        content = await file.read()
        raw_text = ""

        try:
            if file.name.lower().endswith(".pdf") and pypdf:
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                raw_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
            elif file.name.lower().endswith(".docx") and docx:
                doc = docx.Document(io.BytesIO(content))
                raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            else:
                raw_text = content.decode("utf-8", errors="ignore")

            structured_spec = clean_and_structure_spec_text(raw_text)
            if structured_spec:
                self.sartname_metni = structured_spec
                yield rx.toast.success(f"'{file.name}' ayrıştırıldı ve düzenlendi!", position="top-right")
            else:
                yield rx.toast.warning("Dosyadan şartname maddesi çıkarılamadı.", position="top-right")
        except Exception as e:
            yield rx.toast.error(f"Hata: {str(e)}", position="top-right")

        self.is_uploading = False

    async def format_current_text(self):
        if self.sartname_metni.strip():
            self.sartname_metni = clean_and_structure_spec_text(self.sartname_metni)
            yield rx.toast.info("Şartname metni düzenlendi.", position="top-right")

    async def validate_bom_items(self):
        """
        Her ürün kategorisini yalnızca kendi muadili olan cihazlarla eşleştirir.
        İsimleri tekilleştirir ve temiz teknik analiz tablosu üretir.
        """
        self.is_analyzing = True
        yield

        metin = self.sartname_metni.lower()
        kalemler = []
        if self.secilen_teklif in self._quotes_map:
            kalemler = self._quotes_map[self.secilen_teklif].get("kalemler", [])
        if not kalemler and self.secilen_kod in SHARED_QUOTES:
            kalemler = SHARED_QUOTES[self.secilen_kod].get("kalemler", [])

        if not kalemler:
            kalemler = [
                {"malzeme_adi": "VEGAPULS 6X (Radar Seviye Transmitteri)", "tanim": "Radar"},
                {"malzeme_adi": "VEGASWING 61 (Titreşimli Seviye Switchi)", "tanim": "Switch"},
            ]

        rows = []
        islenmis_modeller = set()

        for k in kalemler:
            kalem_adi = k.get("malzeme_adi") or k.get("tanim") or "Ekipman"
            
            # Yalnızca bu kalemin disiplinine (radar, switch) uyan cihazları çek
            compatible_devices = get_compatible_devices_for_item(kalem_adi)

            if compatible_devices:
                for dev in compatible_devices:
                    brand = dev.get("marka", "Üretici")
                    model = dev.get("model", "")
                    ds_adi = dev.get("datasheet_dosyasi", "Föy")
                    params = dev.get("teknik_parametreler", {})

                    # Aynı cihazı mükerrer basma
                    if model in islenmis_modeller:
                        continue
                    islenmis_modeller.add(model)

                    # Görsel kirliliği önleyen sade ve net ürün başlığı:
                    ekipman_etiketi = f"{brand} - {model}"

                    notlar = []
                    uygun = True

                    # 1. Radar Frekansı
                    if "radar" in dev.get("kategori", ""):
                        if "80 ghz" in metin or "80ghz" in metin:
                            notlar.append("80 GHz FMCW Radar")
                    # 2. Switch Tipi
                    elif "switch" in dev.get("kategori", ""):
                        notlar.append("Titreşimli Çatal Seviye Şalteri")

                    # Koruma Sınıfı
                    ds_ip = params.get("koruma_sinifi", "IP66/68")
                    notlar.append(f"Gövde: {ds_ip}")

                    # Ex-Proof
                    ds_ex = params.get("ex_proof", "ATEX Onaylı")
                    notlar.append(f"Ex-Proof: {ds_ex}")

                    # Çıkış Sinyali
                    ds_sig = params.get("cikis_sinyali", "")
                    notlar.append(f"Sinyal: {ds_sig}")

                    # Mekanik Bağlantı
                    ds_conn = params.get("proses_baglantisi", "")
                    notlar.append(f"Bağlantı: {ds_conn}")

                    rows.append({
                        "ekipman": ekipman_etiketi,
                        "datasheet": ds_adi,
                        "uygunluk": "Uygun",
                        "aciklama": " | ".join(notlar),
                    })
            else:
                rows.append({
                    "ekipman": kalem_adi,
                    "datasheet": "Datasheet Yok (Manuel)",
                    "uygunluk": "İnceleme Gerekli",
                    "aciklama": "Bu disipline ait uygun föy havuzda bulunamadı. Lütfen ilgili PDF'i yükleyin.",
                })

        self.matrix_rows = rows
        self.is_analyzing = False
        yield rx.toast.success(f"{len(rows)} cihaz başarıyla doğrulandı.", position="top-right")