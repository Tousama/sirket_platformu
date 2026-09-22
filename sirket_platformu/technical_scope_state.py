import io
import os
import json
import re
import reflex as rx
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

MEMORY_FILE = "nlp_feedback_memory.json"

class TechnicalScopeState(rx.State):
    referans_secenekleri: List[str] = [
        "PT202609201555 Deneme | Shell | Enstruman Temini",
        "PT202609191725-Rev1 | OMC | LP Enstrumantasyon (Rev1)",
        "PT202609191650 | OMC | Radar & Pressure Gauge Temini",
        "PT2026088103 | Doğukan KILIÇ | AVES GÜNEY Motorin Pompası Scully",
        "PT2026088039 | GİZEM AKYILDIZ | DERİNCE SHELL TERMİNALİ UPS BAĞLANTISI",
    ]
    secilen_referans: str = "PT202609201555 Deneme | Shell | Enstruman Temini"
    sartname_no: str = "TÜPRAŞ / SHELL Tesisleri ATEX & Enstrümantasyon Teknik Şartnamesi"
    muhatap_hitap: str = "Sayın Yetkili (Satınalma & Proje Direktörlüğü)"

    giris_yazisi: str = ""
    is_kapsami: str = ""
    isveren_sorumluluklari: str = ""
    haric_tutulanlar: str = ""

    # Geri Bildirim ve Durum Değişkenleri
    is_analyzing: bool = False
    uploaded_file_name: str = ""
    tespit_edilen_tip: str = ""
    feedback_notes: str = ""
    saved_feedback_count: int = 0

    # Setters
    def set_secilen_referans(self, val: str):
        self.secilen_referans = val

    def set_sartname_no(self, val: str):
        self.sartname_no = val

    def set_muhatap_hitap(self, val: str):
        self.muhatap_hitap = val

    def set_giris_yazisi(self, val: str):
        self.giris_yazisi = val

    def set_is_kapsami(self, val: str):
        self.is_kapsami = val

    def set_isveren_sorumluluklari(self, val: str):
        self.isveren_sorumluluklari = val

    def set_haric_tutulanlar(self, val: str):
        self.haric_tutulanlar = val

    def set_feedback_notes(self, val: str):
        self.feedback_notes = val

    # =========================================================================
    # GERİ BİLDİRİM & ÖĞRENME MOTORU
    # =========================================================================
    def _load_memory(self) -> List[Dict[str, Any]]:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_memory_entry(self, entry: Dict[str, Any]):
        memory = self._load_memory()
        memory.append(entry)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    def save_user_feedback(self):
        """Mühendisin ekranda düzelttiği nihai hali NLP hafızasına kaydeder."""
        entry = {
            "sartname_no": self.sartname_no,
            "uploaded_file": self.uploaded_file_name,
            "tespit_tipi": self.tespit_edilen_tip,
            "approved_scope": self.is_kapsami,
            "approved_employer": self.isveren_sorumluluklari,
            "approved_exclusions": self.haric_tutulanlar,
            "feedback_notes": self.feedback_notes,
        }
        self._save_memory_entry(entry)
        self.feedback_notes = ""
        memory = self._load_memory()
        self.saved_feedback_count = len(memory)
        return rx.toast.success(
            "Geri bildirim başarıyla kaydedildi! NLP modeli gelecekteki analizlerde bu tercihi önceliklendirecek.",
            position="top-right"
        )

    # =========================================================================
    # GELİŞTİRİLMİŞ NLP VE TEMİZLEME MOTORU
    # =========================================================================
    def _nlp_clean_atex(self, text: str) -> str:
        """ATEX terimlerini yinelenmeyen ve düzgün formatlı hale getirir."""
        tokens = set()
        t_low = text.lower()
        if "zone 0" in t_low: tokens.add("Zone 0")
        if "zone 1" in t_low: tokens.add("Zone 1")
        if "zone 2" in t_low: tokens.add("Zone 2")
        if "ex d" in t_low or "ex-d" in t_low: tokens.add("Ex d")
        if "ex ia" in t_low or "ex-ia" in t_low: tokens.add("Ex ia")
        if "ex e" in t_low: tokens.add("Ex e")
        if "iic t6" in t_low: tokens.add("IIC T6")
        elif "iic t4" in t_low: tokens.add("IIC T4")
        if "iecex" in t_low: tokens.add("IECEx")
        if "atex" in t_low and not any("zone" in x.lower() for x in tokens):
            tokens.add("ATEX")

        # Sıralı ve tekrarsız birleştir
        order = ["ATEX", "IECEx", "Zone 0", "Zone 1", "Zone 2", "Ex d", "Ex ia", "Ex e", "IIC T4", "IIC T6"]
        sorted_tokens = [t for t in order if t in tokens]
        if not sorted_tokens and tokens:
            sorted_tokens = list(tokens)
        return " / ".join(sorted_tokens) if sorted_tokens else "Endüstriyel Standart"

    def _nlp_parse_specification(self, text: str) -> Dict[str, Any]:
        t_low = text.lower()

        # Hafızada benzer şartname varsa incele (Memory Lookup)
        memory = self._load_memory()
        for item in reversed(memory):
            if item.get("sartname_no") and item["sartname_no"].lower() in t_low:
                return {
                    "kapsam_tipi": item.get("tespit_tipi", "Öğrenilmiş Şablon"),
                    "giris": self.giris_yazisi,
                    "is_kapsami": item.get("approved_scope", ""),
                    "isveren": item.get("approved_employer", ""),
                    "haric": item.get("approved_exclusions", ""),
                }

        # Kapsam Skorlaması
        montaj_keywords = [r"\bmontaj\b", r"\bkablaj\b", r"\bkablo\s*çekim", r"\btava\s*montaj", r"\bsonlandırma\b", r"\bişçilik\b", r"\bsüpervizör\b"]
        temin_keywords = [r"\bmalzeme\s*temin", r"\benstrüman\s*temin", r"\bcihaz\s*temin", r"\bsatın\s*alma\b", r"\btedarik\b", r"\bprocurement\b", r"\bsupply\s*only\b"]

        montaj_skoru = sum(len(re.findall(k, t_low)) for k in montaj_keywords)
        temin_skoru = sum(len(re.findall(k, t_low)) for k in temin_keywords)
        is_supply_only = (montaj_skoru <= 2) or ("sadece temin" in t_low)

        # Yinelenmeyen temiz ATEX ifadesi
        atex_str = self._nlp_clean_atex(text)

        enstruman_maddeleri = []
        if atex_str != "Endüstriyel Standart":
            enstruman_maddeleri.append(f"Şartnamede talep edilen {atex_str} koruma sınıfına haiz enstrüman temini.")
        else:
            enstruman_maddeleri.append("Teknik şartname föylerine tam uyumlu endüstriyel proses enstrümanları temini.")

        # Sinyal Protokolleri (Tekrarsız)
        sinyaller = []
        if "4-20" in t_low: sinyaller.append("4-20mA")
        if "hart" in t_low: sinyaller.append("HART")
        if "modbus" in t_low: sinyaller.append("Modbus")
        if "profibus" in t_low: sinyaller.append("Profibus")
        if sinyaller:
            enstruman_maddeleri.append(f"Proses otomasyonuna entegre edilecek {' / '.join(sinyaller)} haberleşme protokolü desteği.")

        # Kalite & Test Dokümanları
        sertifikalar = []
        if "3.1" in t_low or "10204" in t_low:
            sertifikalar.append("EN 10204 3.1 Malzeme İzlenebilirlik Sertifikaları")
        if "sil" in t_low:
            sertifikalar.append("Fonksiyonel Emniyet (SIL) Sertifikaları")
        if "kalibrasyon" in t_low or "test" in t_low:
            sertifikalar.append("Fabrika Kalibrasyon ve Test Raporları")

        if sertifikalar:
            enstruman_maddeleri.append("Cihazlarla birlikte teslim edilecek: " + ", ".join(sertifikalar) + ".")
        else:
            enstruman_maddeleri.append("Orijinal üretici test/kalibrasyon sertifikaları ve kullanım kılavuzlarının teslimi.")

        enstruman_maddeleri.append("Tüm ekipmanların şantiye / tesis sahasına nakliye sigortalı (CIP/DAP) teslimi.")

        is_kapsami_list = [f"• {m}" for m in enstruman_maddeleri]
        isveren_list = []
        haric_list = []

        if is_supply_only:
            kapsam_tipi = "Saf Enstrüman / Malzeme Temini (Supply Only)"
            giris = (
                "İşbu teknik teklif ve kapsam dokümanı, incelenen şartnamedeki malzeme gereksinimlerine "
                "tam uyumlu olarak hazırlanmış olup, teklif sınırlarımız yalnızca fabrika çıkışlı enstrüman temini "
                "ve kalite sertifikasyonunu kapsamaktadır. Sahada montaj ve kablaj işleri kapsam dışıdır."
            )
            isveren_list.append("• Malzemelerin şantiye sahasında teslim alınması, uygun kapalı depolama koşullarının sağlanması.")
            isveren_list.append("• Malzeme kabul ve muayene tutanaklarının şartname takvimine uygun olarak imzalanması.")

            haric_list.append("• Sahada mekanik ve elektriksel montaj, braket kaynağı, flanşlama ve kablaj işleri.")
            haric_list.append("• Saha loop testleri, enerji verme ve devreye alma (commissioning) hizmetleri.")
            haric_list.append("• Şartnamede açıkça belirtilmeyen montaj sarf malzemeleri ve ilave kablo tavaları.")
            haric_list.append("• Her türlü inşaat, kaide, kırım ve hafriyat işleri.")
        else:
            kapsam_tipi = "Malzeme Temini + Saha Montaj & İşçilik"
            giris = (
                "İşbu teknik teklif dokümanı, şartnamede tanımlanan saha enstrümantasyon, kablaj "
                "ve montaj işçiliklerini kapsamakta olup, devreye alma sınırlarını detaylandırmaktadır."
            )
            is_kapsami_list.append("• Sahada paslanmaz kablo tavası montajı, kablo çekimi ve Ex-proof rakor sonlandırmaları.")
            is_kapsami_list.append("• 4-20mA HART sinyal süreklilik testleri, loop kontrolleri ve devreye alma faaliyetleri.")

            isveren_list.append("• Saha çalışma izinleri ve İSG sıcak çalışma formlarının onaylanması.")
            isveren_list.append("• Montaj öncesi proses hatlarının gazdan arındırılması, yıkanması ve körlenmesi.")
            isveren_list.append("• Sahada ihtiyaç duyulacak geçici şantiye enerjisi ve aydınlatmanın temini.")

            haric_list.append("• İnşaat, beton kaide ve hafriyat işleri.")
            haric_list.append("• Şartnamede açıkça belirtilmeyen mekanik borulama ve hat deplasmanları.")

        return {
            "kapsam_tipi": kapsam_tipi,
            "giris": giris,
            "is_kapsami": "\n".join(is_kapsami_list),
            "isveren": "\n".join(isveren_list),
            "haric": "\n".join(haric_list),
        }

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    async def handle_upload_and_analyze(self, files: List[rx.UploadFile]):
        if not files:
            yield rx.toast.error("Lütfen bir teknik şartname dosyası seçin.", position="top-right")
            return

        self.is_analyzing = True
        yield

        file = files[0]
        self.uploaded_file_name = file.filename
        content = await file.read()

        raw_text = ""
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                t = page.extract_text()
                if t:
                    raw_text += t + "\n"
        except Exception:
            self.is_analyzing = False
            yield rx.toast.error("PDF okunamadı, lütfen geçerli bir PDF yükleyin.", position="top-right")
            return

        if not raw_text.strip():
            self.is_analyzing = False
            yield rx.toast.warning("PDF içerisinde okunabilir metin bulunamadı.", position="top-right")
            return

        parsed = self._nlp_parse_specification(raw_text)

        self.tespit_edilen_tip = parsed["kapsam_tipi"]
        self.giris_yazisi = parsed["giris"]
        self.is_kapsami = parsed["is_kapsami"]
        self.isveren_sorumluluklari = parsed["isveren"]
        self.haric_tutulanlar = parsed["haric"]

        self.is_analyzing = False
        yield rx.toast.success(f"Şartname '{self.tespit_edilen_tip}' olarak çözümlendi (Tekrarlar temizlendi)!", position="top-right")

    def export_docx(self):
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.9)
            section.right_margin = Inches(0.9)

        title_p = doc.add_paragraph()
        title_run = title_p.add_run("TEKNİK ŞARTNAME UYUMLULUK VE KAPSAM DOKÜMANI")
        title_run.font.name = "Calibri"
        title_run.font.size = Pt(15)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 52, 98)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub_p = doc.add_paragraph()
        sub_run = sub_p.add_run("PetroTek Engineering - Endüstriyel Tesis & Otomasyon Çözümleri")
        sub_run.font.name = "Calibri"
        sub_run.font.size = Pt(9.5)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        table = doc.add_table(rows=3, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        info_pairs = [
            ("Referans Teklif Kodu / Proje:", self.secilen_referans),
            ("Teknik Şartname Referansı:", self.sartname_no),
            ("Muhatap / Hitap:", self.muhatap_hitap),
        ]
        for idx, (label, val) in enumerate(info_pairs):
            row = table.rows[idx]
            lbl_cell = row.cells[0].paragraphs[0].add_run(label)
            lbl_cell.font.name = "Calibri"
            lbl_cell.font.size = Pt(9)
            lbl_cell.font.bold = True

            val_cell = row.cells[1].paragraphs[0].add_run(val)
            val_cell.font.name = "Calibri"
            val_cell.font.size = Pt(9)

        doc.add_paragraph()

        def add_section(heading_text: str, content_text: str):
            h_p = doc.add_paragraph()
            h_run = h_p.add_run(heading_text)
            h_run.font.name = "Calibri"
            h_run.font.size = Pt(11.5)
            h_run.font.bold = True
            h_run.font.color.rgb = RGBColor(30, 41, 59)

            c_p = doc.add_paragraph()
            c_run = c_p.add_run(content_text)
            c_run.font.name = "Calibri"
            c_run.font.size = Pt(9.5)
            c_p.paragraph_format.line_spacing = 1.2
            c_p.paragraph_format.space_after = Pt(8)

        add_section("1. GİRİŞ VE PROJE AMACI", self.giris_yazisi)
        add_section("2. İŞ KAPSAMI (SCOPE OF WORK)", self.is_kapsami)
        add_section("3. İŞVERENİN SORUMLULUKLARI", self.isveren_sorumluluklari)
        add_section("4. HARİÇ TUTULAN İŞLER (EXCLUSIONS)", self.haric_tutulanlar)

        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_run = sig_p.add_run("Teknik Onay & Hazırlayan:\nPetroTek Engineering Proje & Teklif Departmanı")
        sig_run.font.name = "Calibri"
        sig_run.font.size = Pt(9)
        sig_run.font.bold = True
        sig_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        target_stream = io.BytesIO()
        doc.save(target_stream)
        target_stream.seek(0)

        clean_ref = self.secilen_referans.split("|")[0].strip()
        return rx.download(
            data=target_stream.getvalue(),
            filename=f"Teknik_Kapsam_{clean_ref}.docx"
        )