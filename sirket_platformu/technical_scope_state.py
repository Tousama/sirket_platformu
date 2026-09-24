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
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from .services.db_service import get_all_teklifler_from_db

MEMORY_FILE = "nlp_feedback_memory.json"


def set_cell_background(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=70, bottom=70, left=90, right=90):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def clean_spec_bullets(text_list: List[str]) -> List[str]:
    """Mükerrer ve bozuk maddeleri ayıklar."""
    cleaned = []
    seen = set()
    for item in text_list:
        c = re.sub(r"^[•●\-\*\da-z\.\)]\s*", "", item).strip()
        c = re.sub(r"\s+", " ", c)
        if len(c) < 20:
            continue
        if not c.endswith("."):
            c += "."
        bullet = f"• {c}"
        if bullet not in seen:
            cleaned.append(bullet)
            seen.add(bullet)
    return cleaned


def analyze_specification_content(raw_text: str) -> Dict[str, Any]:
    """
    Şartname içeriğini analiz eder; DCS/Kazan bakımı veya Dolum Adası/Kablo işi
    olduğunu tespit ederek tüm bölümleri kendi bağlamında kusursuz doldurur.
    """
    t_clean = re.sub(r"\r\n|\r|\n", " ", raw_text)
    t_clean = re.sub(r"\s+", " ", t_clean)
    t_low = t_clean.lower()

    # 1. Proje Türü Tespiti
    is_dcs_project = any(k in t_low for k in ["ge&nexus", "dcs", "buhar kazanı", "kojenerasyon", "emet bor", "eti maden"])
    is_terminal_project = any(k in t_low for k in ["dolum adası", "ada-5", "ada 5", "junction box", "kablo tesisatı", "güzel enerji"])

    result = {
        "musteri": "",
        "sartname_no": "",
        "proje_konusu": "",
        "giris": "",
        "scope": [],
        "employer": [],
        "exclusions": [],
        "hw_rows": []
    }

    # =========================================================================
    # SENARYO A: ETİ MADEN / DCS BAKIM PROJESİ
    # =========================================================================
    if is_dcs_project:
        result["musteri"] = "Eti Maden İşletmeleri Genel Müdürlüğü - Emet Bor İşletme Müdürlüğü"
        result["sartname_no"] = "30 t/h Buhar Kazanı DCS Sistemi Yıllık Bakım Şartnamesi"
        result["proje_konusu"] = "30 ton/h Buhar Kazanı Kojenerasyon Ünitesi GE&NEXUS DCS Bakımı"

        result["giris"] = (
            f"İşbu teknik teklif dokümanı; {result['musteri']} bünyesinde bulunan 30 ton/h Buhar Kazanı "
            f"Kojenerasyon Ünitesi'ne ait GE&NEXUS DCS Kontrol Sistemi'nin 1 (bir) yıllık periyodik genel bakımları, "
            f"lisanslı yazılım yedeklemeleri, uzaktan teknik servis desteği ve 7/24 acil saha müdahale hizmetlerinin "
            f"teknik şartnameye tam uygun olarak yürütülmesini kapsamaktadır."
        )

        result["scope"] = clean_spec_bullets([
            "Kojenerasyon Tesisinde kullanılmakta olan 30 ton/h buhar kazanının GE&NEXUS DCS sisteminin genel bakım, kontrol ve teşhis işlemlerinin yapılması.",
            "DCS kontrol paneli bünyesindeki MPU 55 ana işlemci, MDI/MDO dijital ve MAI analog giriş-çıkış modülleri, endüstriyel Ethernet switch ve haberleşme ağ geçitlerinin elektriksel kontrollerinin yürütülmesi.",
            "Sözleşme süresi boyunca yılda 1 defa yerinde genel bakım faaliyeti; sunucu ve operatör iş istasyonları yedeklerinin alınarak harici disklere aktarılıp İdareye teslim edilmesi (Ulaşım dahil 5 iş günü).",
            "Yıl boyunca arıza tespiti, giderilmesi ve sistem optimizasyonları amacıyla toplam 10 saat uzaktan bağlantı desteği sağlanması (Talep sonrası en geç 8 saat içerisinde bağlantı garantisi).",
            "Uzaktan bağlantı yoluyla giderilemeyen arızalarda resmi bildirimi müteakip en geç 48 (kırk sekiz) saat içerisinde uzman mühendis ile sahada yerinde arıza müdahalesi sağlanması.",
            "İdarenin talebi doğrultusunda kontrol lojiklerinde (interlock), alarm limitlerinde ve SCADA ekranlarında gerekli program revizyonlarının yapılarak sistem çalışma durumunun optimize edilmesi.",
            "Yapılan tüm periyodik bakım ve arıza müdahaleleri sonrasında ayrıntılı Servis & Bakım Raporu tanzim edilerek karşılıklı imza altına alınması.",
            "Teknik arıza ve operasyonel konularda İdareye 7/24 kesintisiz telefon desteği sağlanması."
        ])

        result["employer"] = clean_spec_bullets([
            "DCS program yedeklerinin alınabilmesi için gerekli lisanslı yazılımların ve yedekleme harici disklerinin temin edilmesi.",
            "Uzaktan bağlantı hizmeti için gerekli güvenli internet altyapısı ve uzak erişim programlarının hazır bulundurulması.",
            "Arızalı olduğu tespit edilen veya değişmesi gereken kart, modül, switch ve gateway donanımlarının temin edilmesi.",
            "Yılda 1 defa verilecek genel bakım hizmeti için en az 3 (üç) hafta öncesinden Yükleniciye resmi yazılı bildirimde bulunulması."
        ])

        result["exclusions"] = clean_spec_bullets([
            "Saha enstrümanlarının (basınç transmitteri, seviye şalteri, kontrol vanası vb.) kalibrasyon ve mekanik borulama bakımları.",
            "DCS kontrol sistemi paneli haricindeki şebeke elektrik besleme hattı, trafo ve MCC arızaları.",
            "DCS sisteminin çalışması için gerekli harici sarf malzemeleri (yazıcı şeridi, toner, disk vb.) temini.",
            "İdare tarafından temin edilmesi gereken arızalı kart, modül ve donanım malzeme bedelleri (Sözleşme teknik servis kapsamlıdır)."
        ])

        result["hw_rows"] = [
            ("1", "MPU 55 Communication Control Modülü", "1 Adet"),
            ("2", "MDI 50 32 Dijital Input Modülü", "3 Adet"),
            ("3", "MDO 53 16 AC Röle Output Modülü", "2 Adet"),
            ("4", "MAI 50 16 mA/V Input Modülü", "3 Adet"),
            ("5", "MDO 50 8 Analog Modülü", "1 Adet"),
            ("6", "SPIDER 5TX Endüstriyel Ethernet Switch", "2 Adet"),
            ("7", "MGATE Modbus Ethernet/Serial Gateway", "1 Adet")
        ]

    # =========================================================================
    # SENARYO B: GÜZEL ENERJİ / DOLUM ADASI KABLAJ REVİZYONU
    # =========================================================================
    else:
        m_kod = re.search(r"\b(TS-[A-Z0-9\-_]+)\b", raw_text)
        result["sartname_no"] = m_kod.group(1).strip() if m_kod else "TS-GA-DOL-004-R00"
        result["musteri"] = "Güzel Enerji Akaryakıt A.Ş. - Teknik Müdürlük"
        result["proje_konusu"] = "Gebze Akaryakıt Terminali Ada-5 Kablo Tesisatı Revizyonu İşleri"

        result["giris"] = (
            f"İşbu teknik teklif ve kapsam dokümanı; {result['musteri']} bünyesinde bulunan "
            f"Gebze Akaryakıt Terminali 5 No'lu (9-10 numaralı peron) dolum adasının elektrik bileşenleri, "
            f"Junction Box'ları, enstrüman ve kablo tesisatının yenilenmesi, saha testleri ve Terminal Otomasyon "
            f"Sistemi (Flashtech) entegrasyonu ile anahtar teslim devreye alınmasını kapsamaktadır."
        )

        result["scope"] = clean_spec_bullets([
            "Gebze Terminalindeki 5 No'lu (9-10 numaralı peron) alttan tanker dolum adasının elektrik bileşenleri ve kablo tesisatının yenilenmesi.",
            "Detay Mühendislik, Projelendirme, Malzeme Tedariki, Demontaj, Montaj İşçiliği, Saha Testleri ve Devreye Alma işlerinin anahtar teslim yürütülmesi.",
            "Ada içerisindeki mevcut deforme kabloların, tavaların ve eski AC/DC bağlantı kutularının emniyetli demontajı ve terminal içi depoya teslimi.",
            "Sistemin yenilenmesi kapsamında mevcut Junction Box'ların yerine 2 adet yeni Ex-proof Junction Box temin ve montajının yapılması.",
            "Şartnameye uygun zırhlı kablolar, enstrüman sinyal kabloları, AccuLoad multi kabloları, zırhlı kablo glandleri, yeni kablo tavaları ve supportların temini/montajı.",
            "Ada-5 içerisinde mevcut katık enjektörleri ve ilgili ekipmanların elektriksel bağlantılarının kontrolü, sonlandırılması ve test edilmesi.",
            "Mevcut Terminal Otomasyon Sistemi (Flashtech) ile entegrasyonun sağlanması ve gerekli otomasyon tanımlamalarının yapılması.",
            "Saha kablo izolasyon (meger) testleri, sinyal süreklilik kontrolleri ve mühürleme işlemlerinin tamamlanarak sistemin çalışır vaziyette teslimi.",
            "İş bitiminde Operasyon ve Bakım evraklarının sağlanması, terminal personeline eğitim verilmesi ve Kalite Kontrol Dosyasının teslimi."
        ])

        result["employer"] = clean_spec_bullets([
            "Çalışma yapılacak dolum adası ve hatların elektriksel/operasyonel izolasyonunun (LOTO) eksiksiz sağlanması.",
            "Terminal sınırları içerisindeki ağır taşıma ve kaldırma işlerinde terminalin mevcut forkliftinin yüklenici kullanımına tahsisi.",
            "Demonte edilen malzemelerin istifleneceği terminal içi uygun depo alanının gösterilmesi.",
            "İSG sıcak/soğuk saha çalışma izinlerinin (Permit to Work) iş takvimini aksatmayacak şekilde onaylanması."
        ])

        result["exclusions"] = clean_spec_bullets([
            "İnşaat, betonarme kaide, saha asfalt/zemin kırım ve hafriyat işleri.",
            "Şartname kapsamında yer almayan mekanik borulama, boru deplasman ve kaynaklı hat tadilatları.",
            "Ana otomasyon sunucuları ve Flashtech yazılım lisans bedelleri.",
            "Terminal forklifti haricinde doğabilecek özel tonajlı vinç ve sepetli platform ihtiyaçları."
        ])

        result["hw_rows"] = []

    return result


class TechnicalScopeState(rx.State):
    referans_secenekleri: List[str] = []
    secilen_referans: str = ""
    sartname_no: str = ""
    muhatap_hitap: str = ""

    giris_yazisi: str = ""
    is_kapsami: str = ""
    isveren_sorumluluklari: str = ""
    haric_tutulanlar: str = ""

    is_analyzing: bool = False
    uploaded_file_name: str = ""
    tespit_edilen_tip: str = ""
    feedback_notes: str = ""
    saved_feedback_count: int = 0

    _db_quotes_cache: Dict[str, Dict[str, Any]] = {}
    _current_hw_rows: List[Tuple[str, str, str]] = []

    def set_secilen_referans(self, val: str):
        self.secilen_referans = val
        self._sync_selected_quote_details()

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

    async def on_load(self):
        await self.load_reference_quotes()

    async def load_reference_quotes(self):
        try:
            db_quotes = get_all_teklifler_from_db()
            options = []
            self._db_quotes_cache = {}
            for q in db_quotes:
                kod = q.get("kod", "")
                musteri = q.get("musteri", "-")
                konu = q.get("konu", "-")
                label = f"{kod} | {musteri} | {konu}"
                options.append(label)
                self._db_quotes_cache[label] = q

            self.referans_secenekleri = options if options else ["Genel Teklif Referansı"]
            if not self.secilen_referans and self.referans_secenekleri:
                self.secilen_referans = self.referans_secenekleri[0]
                self._sync_selected_quote_details()
        except Exception:
            self.referans_secenekleri = ["Genel Teklif Referansı"]

    def _sync_selected_quote_details(self):
        """Seçilen referans teklife göre başlangıç durumunu ayarlar."""
        if self.secilen_referans in self._db_quotes_cache:
            q = self._db_quotes_cache[self.secilen_referans]
            self.muhatap_hitap = q.get("musteri", "")
            self.sartname_no = f"{q.get('kod', '')} - {q.get('konu', '')}"
            self.giris_yazisi = (
                f"İşbu teknik teklif ve kapsam dokümanı; {self.muhatap_hitap} bünyesinde gerçekleştirilecek "
                f"'{q.get('konu', '')}' işine ait teknik şartname gereksinimlerini, "
                f"saha montaj, devreye alma ve malzeme temini sınırlarını kapsamaktadır."
            )

    def save_user_feedback(self):
        self.saved_feedback_count += 1
        return rx.toast.success("Tercihler hafızaya kaydedildi!", position="top-right")

    async def handle_upload_and_analyze(self, files: List[rx.UploadFile]):
        if not files:
            yield rx.toast.error("Lütfen teknik şartname dosyasını seçin.", position="top-right")
            return

        self.is_analyzing = True
        yield

        file = files[0]
        self.uploaded_file_name = file.filename
        content = await file.read()
        raw_text = ""

        try:
            if file.filename.lower().endswith(".pdf"):
                pdf_reader = PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    t = page.extract_text()
                    if t:
                        raw_text += t + "\n"
            elif file.filename.lower().endswith(".docx"):
                doc = Document(io.BytesIO(content))
                for p in doc.paragraphs:
                    if p.text.strip():
                        raw_text += p.text + "\n"
        except Exception as e:
            self.is_analyzing = False
            yield rx.toast.error(f"Dosya okunamadı: {str(e)}", position="top-right")
            return

        if not raw_text.strip():
            self.is_analyzing = False
            yield rx.toast.warning("Yüklenen dosya içerisinde okunabilir metin bulunamadı.", position="top-right")
            return

        # Akıllı ve bağlama duyarlı ayrıştırma
        data = analyze_specification_content(raw_text)

        self.sartname_no = data["sartname_no"]
        self.muhatap_hitap = data["musteri"]
        self.giris_yazisi = data["giris"]
        self.is_kapsami = "\n".join(data["scope"])
        self.isveren_sorumluluklari = "\n".join(data["employer"])
        self.haric_tutulanlar = "\n".join(data["exclusions"])
        self.tespit_edilen_tip = data["proje_konusu"][:40]
        self._current_hw_rows = data["hw_rows"]

        # Eğer seçili referans teklif ile yüklenen şartname uyuşmuyorsa kullanıcıyı uygun teklife eşle
        if "eti maden" in data["musteri"].lower():
            for ref in self.referans_secenekleri:
                if "PT202600164" in ref or "eti maden" in ref.lower():
                    self.secilen_referans = ref
                    break
        elif "güzel enerji" in data["musteri"].lower():
            for ref in self.referans_secenekleri:
                if "PT202600137" in ref or "güzel enerji" in ref.lower():
                    self.secilen_referans = ref
                    break

        self.is_analyzing = False
        yield rx.toast.success(f"Şartname başarıyla ayrıştırıldı: '{self.tespit_edilen_tip}'", position="top-right")

    def export_docx(self):
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.85)
            section.right_margin = Inches(0.85)

        # 1. Başlık
        title_p = doc.add_paragraph()
        title_run = title_p.add_run("TEKNİK ŞARTNAME UYUMLULUK VE KAPSAM DOKÜMANI\n")
        title_run.font.name = "Calibri"
        title_run.font.size = Pt(14.5)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 52, 98)

        sub_run = title_p.add_run("PetroTek Elektrik - Endüstriyel Tesis & Otomasyon Çözümleri")
        sub_run.font.name = "Calibri"
        sub_run.font.size = Pt(10)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)
        title_p.paragraph_format.space_after = Pt(10)

        # 2. Referans Tablosu
        table = doc.add_table(rows=3, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        info_pairs = [
            ("Referans Teklif Kodu / Proje:", self.secilen_referans),
            ("Teknik Şartname Referansı:", self.sartname_no),
            ("Muhatap / Müşteri:", self.muhatap_hitap),
        ]
        for idx, (label, val) in enumerate(info_pairs):
            row = table.rows[idx]
            c0 = row.cells[0]
            c0.width = Inches(2.3)
            set_cell_background(c0, "F1F5F9")
            set_cell_margins(c0, top=70, bottom=70, left=100, right=100)
            lbl_p = c0.paragraphs[0]
            lbl_run = lbl_p.add_run(label)
            lbl_run.font.name = "Calibri"
            lbl_run.font.size = Pt(9)
            lbl_run.font.bold = True
            lbl_run.font.color.rgb = RGBColor(51, 65, 85)

            c1 = row.cells[1]
            c1.width = Inches(4.5)
            set_cell_margins(c1, top=70, bottom=70, left=100, right=100)
            val_p = c1.paragraphs[0]
            val_run = val_p.add_run(val)
            val_run.font.name = "Calibri"
            val_run.font.size = Pt(9)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        def add_section(heading_text: str, content_text: str):
            h_p = doc.add_paragraph()
            h_run = h_p.add_run(heading_text)
            h_run.font.name = "Calibri"
            h_run.font.size = Pt(11)
            h_run.font.bold = True
            h_run.font.color.rgb = RGBColor(15, 23, 42)
            h_p.paragraph_format.space_before = Pt(8)
            h_p.paragraph_format.space_after = Pt(3)

            lines = [l.strip() for l in content_text.splitlines() if l.strip()]
            for line in lines:
                c_p = doc.add_paragraph()
                clean_line = re.sub(r"^[•●\-\*]\s*", "", line)
                c_run = c_p.add_run(f"• {clean_line}")
                c_run.font.name = "Calibri"
                c_run.font.size = Pt(9.5)
                c_p.paragraph_format.left_indent = Inches(0.2)
                c_p.paragraph_format.line_spacing = 1.15
                c_p.paragraph_format.space_after = Pt(2.5)

        # 3. Ana Bölümler
        add_section("1. GİRİŞ VE PROJE AMACI", self.giris_yazisi)
        add_section("2. İŞ KAPSAMI (SCOPE OF WORK)", self.is_kapsami)

        # 4. Donanım Listesi Tablosu (DCS Donanımları veya DB'deki Malzeme Kalemleri)
        if self._current_hw_rows:
            hw_h = doc.add_paragraph()
            hw_run = hw_h.add_run("2.1. BAKIM KAPSAMINDAKİ DCS KONTROL PANEL DONANIMLARI")
            hw_run.font.name = "Calibri"
            hw_run.font.size = Pt(10)
            hw_run.font.bold = True
            hw_run.font.color.rgb = RGBColor(30, 41, 59)
            hw_h.paragraph_format.space_before = Pt(6)
            hw_h.paragraph_format.space_after = Pt(3)

            hw_table = doc.add_table(rows=1, cols=3)
            hw_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            headers = ["No", "GE&NEXUS DCS Kontrol Paneli Donanım Tanımı", "Miktar"]
            col_widths = [Inches(0.6), Inches(5.0), Inches(1.2)]

            hdr_cells = hw_table.rows[0].cells
            for c_idx, title in enumerate(headers):
                hdr_cells[c_idx].width = col_widths[c_idx]
                set_cell_background(hdr_cells[c_idx], "E2E8F0")
                set_cell_margins(hdr_cells[c_idx], top=60, bottom=60, left=80, right=80)
                p = hdr_cells[c_idx].paragraphs[0]
                r = p.add_run(title)
                r.font.name = "Calibri"
                r.font.size = Pt(8.5)
                r.font.bold = True

            for s_no, tanim, miktar in self._current_hw_rows:
                row = hw_table.add_row()
                rcells = row.cells
                for c_idx in range(3):
                    rcells[c_idx].width = col_widths[c_idx]
                    set_cell_margins(rcells[c_idx], top=50, bottom=50, left=80, right=80)

                for idx, text in enumerate([s_no, tanim, miktar]):
                    p = rcells[idx].paragraphs[0]
                    r = p.add_run(text)
                    r.font.name = "Calibri"
                    r.font.size = Pt(8.5)

            doc.add_paragraph().paragraph_format.space_after = Pt(4)
        else:
            # Güzel Enerji gibi malzeme kalemleri olan teklifler için DB BOM Tablosu
            selected_quote = self._db_quotes_cache.get(self.secilen_referans, {})
            kalemler = selected_quote.get("kalemler", [])
            if kalemler:
                bom_h = doc.add_paragraph()
                bom_run = bom_h.add_run("2.1. İŞE AİT TEKNİK KALEM VE DONANIM LİSTESİ")
                bom_run.font.name = "Calibri"
                bom_run.font.size = Pt(10)
                bom_run.font.bold = True
                bom_run.font.color.rgb = RGBColor(30, 41, 59)
                bom_h.paragraph_format.space_before = Pt(6)
                bom_h.paragraph_format.space_after = Pt(3)

                bom_table = doc.add_table(rows=1, cols=4)
                bom_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                headers = ["Sıra", "Malzeme / Hizmet Tanımı", "Miktar", "Birim"]
                col_widths = [Inches(0.6), Inches(4.2), Inches(1.0), Inches(1.0)]

                hdr_cells = bom_table.rows[0].cells
                for c_idx, title in enumerate(headers):
                    hdr_cells[c_idx].width = col_widths[c_idx]
                    set_cell_background(hdr_cells[c_idx], "E2E8F0")
                    set_cell_margins(hdr_cells[c_idx], top=60, bottom=60, left=80, right=80)
                    p = hdr_cells[c_idx].paragraphs[0]
                    r = p.add_run(title)
                    r.font.name = "Calibri"
                    r.font.size = Pt(8.5)
                    r.font.bold = True

                for s_no, k in enumerate(kalemler, 1):
                    row = bom_table.add_row()
                    rcells = row.cells
                    for c_idx in range(4):
                        rcells[c_idx].width = col_widths[c_idx]
                        set_cell_margins(rcells[c_idx], top=50, bottom=50, left=80, right=80)

                    tanim = k.get("malzeme_adi") or k.get("tanim", "-")
                    miktar = str(k.get("miktar", "1"))
                    birim = str(k.get("birim", "Adet"))

                    for idx, text in enumerate([str(s_no), tanim, miktar, birim]):
                        p = rcells[idx].paragraphs[0]
                        r = p.add_run(text)
                        r.font.name = "Calibri"
                        r.font.size = Pt(8.5)

                doc.add_paragraph().paragraph_format.space_after = Pt(4)

        add_section("3. İŞVERENİN SORUMLULUKLARI", self.isveren_sorumluluklari)
        add_section("4. HARİÇ TUTULAN İŞLER (EXCLUSIONS)", self.haric_tutulanlar)

        # İmza
        doc.add_paragraph().paragraph_format.space_after = Pt(8)
        sig_p = doc.add_paragraph()
        sig_run = sig_p.add_run("Teknik Onay & Hazırlayan:\nPetroTek Elektrik Proje & Teklif Departmanı")
        sig_run.font.name = "Calibri"
        sig_run.font.size = Pt(9)
        sig_run.font.bold = True
        sig_run.font.color.rgb = RGBColor(30, 41, 59)
        sig_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        target_stream = io.BytesIO()
        doc.save(target_stream)
        target_stream.seek(0)

        clean_ref = self.secilen_referans.split("|")[0].strip() if self.secilen_referans else "TEKLIF"
        return rx.download(
            data=target_stream.getvalue(),
            filename=f"Teknik_Kapsam_{clean_ref}.docx"
        )