import io
import re
import reflex as rx
from typing import List, Dict, Any
from .dashboard_state import DashboardState
from .shared_quotes import SHARED_QUOTES
from .services.spec_analyzer import SpecAnalyzerEngine
from .datasheet_service import (
    REGISTERED_DATASHEETS, 
    parse_multipage_pdf_datasheets, 
    get_compatible_devices_for_item,
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
    
    # Kullanıcının düzenlediği ve analiz edilen tek şartname metni
    spec_text: str = (
        "• Seviye Ölçer: 80 GHz Temassız Radar, IP66, ATEX Zone 1 IIB T4, 24VDC, 4-20mA HART.\n"
        "• Basınç Transmitteri: IP67, ATEX Zone 1, 24VDC, 4-20mA HART, 316L gövde.\n"
        "• Ortam sıcaklığı max 55°C."
    )
    
    is_analyzing: bool = False
    extracted_specs: Dict[str, Any] = {}
    validation_results: List[Dict[str, str]] = []
    
    teklif_secenekleri: List[str] = []
    secilen_teklif: str = ""
    _quotes_map: Dict[str, Any] = {}

    is_datasheet_uploading: bool = False
    son_yuklenen_datasheet: str = ""

    datasheet_listesi: List[Dict[str, str]] = []
    matrix_rows: List[Dict[str, Any]] = []

    # Şartnameyle mukayese edilecek cihaz havuzu
    cihaz_secenekleri: List[str] = [
        "PT-101 (Endress+Hauser Basınç Transmitteri)",
        "LT-201 (VEGAPULS 6X Radar Seviye Ölçer)",
        "LS-301 (VEGASWING 61 Titreşimli Switch)",
        "STD-01 (Standart Non-Ex IP54 Sensör)"
    ]
    secilen_cihaz_etiketi: str = "PT-101 (Endress+Hauser Basınç Transmitteri)"

    cihaz_veritabani: Dict[str, Dict[str, Any]] = {
        "PT-101 (Endress+Hauser Basınç Transmitteri)": {
            "name": "Endress+Hauser Cerabar PMP71B",
            "ip_rating": 67,
            "is_atex": True,
            "max_temp": 80,
            "voltage": "24VDC",
            "protocol": "4-20MA HART",
            "body_material": "AISI 316L SS"
        },
        "LT-201 (VEGAPULS 6X Radar Seviye Ölçer)": {
            "name": "VEGAPULS 6X Radar",
            "ip_rating": 68,
            "is_atex": True,
            "max_temp": 70,
            "voltage": "24VDC",
            "protocol": "4-20MA HART",
            "body_material": "Alüminyum"
        },
        "LS-301 (VEGASWING 61 Titreşimli Switch)": {
            "name": "VEGASWING 61 Seviye Şalteri",
            "ip_rating": 66,
            "is_atex": True,
            "max_temp": 60,
            "voltage": "24VDC",
            "protocol": "Röle Çıkış",
            "body_material": "AISI 316L SS"
        },
        "STD-01 (Standart Non-Ex IP54 Sensör)": {
            "name": "Standart Endüstriyel Sensör",
            "ip_rating": 54,
            "is_atex": False,
            "max_temp": 45,
            "voltage": "230VAC",
            "protocol": "Modbus RTU",
            "body_material": "Plastik"
        }
    }

    is_uploading: bool = False
    yuklenen_dosya_adi: str = ""

    @rx.var
    def selected_equipment(self) -> Dict[str, Any]:
        return self.cihaz_veritabani.get(
            self.secilen_cihaz_etiketi, 
            self.cihaz_veritabani["PT-101 (Endress+Hauser Basınç Transmitteri)"]
        )

    @rx.var
    def active_spec_text(self) -> str:
        return self.spec_text

    def set_secilen_cihaz(self, val: str):
        self.secilen_cihaz_etiketi = val
        self.run_spec_analysis()

    def set_spec_text(self, val: str):
        self.spec_text = val

    def set_currency(self, val: Any):
        if isinstance(val, list) and len(val) > 0:
            self.currency = str(val[0])
        else:
            self.currency = str(val)

    async def on_load(self):
        await self.load_quotes()
        self.run_spec_analysis()
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
                self.spec_text = structured_spec
                self.run_spec_analysis()
                async for _ in self.validate_bom_items():
                    pass
                yield rx.toast.success(f"'{file.name}' şartnamesi yüklendi ve analiz edildi!", position="top-right")
            else:
                yield rx.toast.warning("Dosyadan şartname maddesi çıkarılamadı.", position="top-right")
        except Exception as e:
            yield rx.toast.error(f"Hata: {str(e)}", position="top-right")

        self.is_uploading = False

    async def format_current_text(self):
        if self.spec_text.strip():
            self.spec_text = clean_and_structure_spec_text(self.spec_text)
            yield rx.toast.info("Şartname metni düzenlendi.", position="top-right")

    def run_spec_analysis(self):
        """Metin alanındaki şartname ile seçili cihazı karşılaştırır."""
        self.is_analyzing = True
        self.extracted_specs = SpecAnalyzerEngine.extract_spec_parameters(self.spec_text)
        self.validation_results = SpecAnalyzerEngine.validate_equipment(
            self.extracted_specs, 
            self.selected_equipment
        )
        self.is_analyzing = False

    async def validate_bom_items(self):
        """Girilen şartname metnindeki koşullarla BOM tablosundaki cihazları dinamik kıyaslar."""
        self.is_analyzing = True
        yield

        # Şartname metnindeki gerçek gereksinimleri çıkar
        spec_rules = SpecAnalyzerEngine.extract_spec_parameters(self.spec_text)
        metin = self.spec_text.lower()

        kalemler = []
        if self.secilen_teklif in self._quotes_map:
            kalemler = self._quotes_map[self.secilen_teklif].get("kalemler", [])
        if not kalemler and self.secilen_kod in SHARED_QUOTES:
            kalemler = SHARED_QUOTES[self.secilen_kod].get("kalemler", [])

        if not kalemler:
            kalemler = [
                {"malzeme_adi": "VEGAPULS 6X (Radar Seviye Transmitteri)", "tanim": "Radar"},
                {"malzeme_adi": "VEGASWING 61 (Titreşimli Seviye Switchi)", "tanim": "Switch"},
                {"malzeme_adi": "Rosemount 3051S Basınç Transmitteri", "tanim": "Transmitter"},
            ]

        rows = []
        islenmis_modeller = set()

        for k in kalemler:
            kalem_adi = k.get("malzeme_adi") or k.get("tanim") or "Ekipman"
            compatible_devices = get_compatible_devices_for_item(kalem_adi)

            if compatible_devices:
                for dev in compatible_devices:
                    brand = dev.get("marka", "Üretici")
                    model = dev.get("model", "")
                    ds_adi = dev.get("datasheet_dosyasi", "Föy")
                    params = dev.get("teknik_parametreler", {})

                    if model in islenmis_modeller:
                        continue
                    islenmis_modeller.add(model)

                    ekipman_etiketi = f"{brand} - {model}"
                    notlar = []
                    is_compatible = True

                    # 1. IP Koruma Kontrolü
                    ds_ip = params.get("koruma_sinifi", "IP66/68")
                    if spec_rules.get("ip_rating"):
                        req_ip = spec_rules["ip_rating"]
                        ip_match = re.search(r"(\d{2})", ds_ip)
                        dev_ip = int(ip_match.group(1)) if ip_match else 65
                        if dev_ip < req_ip:
                            notlar.append(f"KORUMA YETERSİZ (İstenen: IP{req_ip}, Cihaz: {ds_ip})")
                            is_compatible = False
                        else:
                            notlar.append(f"IP Uygun ({ds_ip})")
                    else:
                        notlar.append(f"Gövde: {ds_ip}")

                    # 2. ATEX Kontrolü
                    ds_ex = params.get("ex_proof", "ATEX Onaylı")
                    if spec_rules.get("is_atex_required"):
                        if "atex" in ds_ex.lower() or "ex" in ds_ex.lower():
                            notlar.append("ATEX Zone 1/2 Uyumlu")
                        else:
                            notlar.append("ATEX EKSİK (Non-Ex Cihaz)")
                            is_compatible = False
                    else:
                        notlar.append(f"Sertifika: {ds_ex}")

                    # 3. Sinyal Tipi
                    ds_sig = params.get("cikis_sinyali", "4-20 mA HART")
                    if spec_rules.get("protocol"):
                        req_proto = spec_rules["protocol"].upper()
                        if req_proto in ds_sig.upper():
                            notlar.append(f"Sinyal Uyumlu ({ds_sig})")
                        else:
                            notlar.append(f"Sinyal Uyuşmazlığı: Şartname {req_proto} istiyor")
                            is_compatible = False
                    else:
                        notlar.append(f"Sinyal: {ds_sig}")

                    rows.append({
                        "ekipman": ekipman_etiketi,
                        "datasheet": ds_adi,
                        "uygunluk": "Uygun" if is_compatible else "İnceleme Gerekli",
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
        yield rx.toast.success("Şartname gereksinimleri tüm cihazlara uygulandı.", position="top-right")