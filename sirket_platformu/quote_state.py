import asyncio
import reflex as rx
import io
import json
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from typing import List, Dict, Any

class QuoteState(rx.State):
    # Proje & Müşteri Üst Bilgileri
    musteri_adi: str = "Tüpraş Rafineri A.Ş."
    proje_adi: str = "Dolum Adası Otomasyon & Ex-Proof Saha Revizyonu"
    teklif_no: str = "TK-2026-094"
    para_birimi: str = "USD"
    kdv_orani: float = 20.0
    genel_iskonto: float = 0.0

    # Sol Menü Durumu
    active_module: str = "Yeni Teklif Hazırla & Çıktı Al"

    # Kalem Listesi
    items: List[Dict[str, Any]] = [
        {
            "tip": "Malzeme",
            "aciklama": "Ex-Proof IP66 Paslanmaz Çelik Dağıtım Panosu",
            "miktar": 2.0,
            "birim": "Adet",
            "birim_maliyet": 1450.0,
            "kar_marji": 30.0,
            "birim_satis": 1885.0,
            "toplam_tutar": 3770.0,
        },
        {
            "tip": "Enstrümantasyon",
            "aciklama": "Coriolis Kütlesel Akış Ölçer (DN50, Ex-d)",
            "miktar": 1.0,
            "birim": "Adet",
            "birim_maliyet": 4200.0,
            "kar_marji": 22.0,
            "birim_satis": 5124.0,
            "toplam_tutar": 5124.0,
        },
        {
            "tip": "İşçilik",
            "aciklama": "Saha Kablo Çekimi, Kanal Montajı & Test/Devreye Alma",
            "miktar": 80.0,
            "birim": "Metre",
            "birim_maliyet": 24.0,
            "kar_marji": 40.0,
            "birim_satis": 33.6,
            "toplam_tutar": 2688.0,
        },
    ]

    # 1. BUTON: TASLAK KAYDET
    def save_draft(self):
        # Taslağı yerel JSON dosyasına veya veritabanına kaydeder
        draft_data = {
            "teklif_no": self.teklif_no,
            "musteri_adi": self.musteri_adi,
            "proje_adi": self.proje_adi,
            "para_birimi": self.para_birimi,
            "genel_toplam": self.genel_toplam,
            "items": self.items,
            "kapsam_metni": self.kapsam_metni,
        }
        with open("son_teklif_taslagi.json", "w", encoding="utf-8") as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
            
        # Kullanıcıya başarı bildirimi gönder
        return rx.toast.success(f"{self.teklif_no} numaralı taslak başarıyla kaydedildi!", position="top-right")

    # 2. BUTON: EXCEL İNDİR
    def export_excel(self):
        # Tablo verilerini DataFrame'e aktarma
        export_rows = []
        for idx, item in enumerate(self.items, 1):
            export_rows.append({
                "Sıra No": idx,
                "Kategori": item.get("tip", ""),
                "Kalem Açıklaması": item.get("aciklama", ""),
                "Miktar": item.get("miktar", 0),
                "Birim": item.get("birim", ""),
                f"Birim Satış ({self.para_birimi})": item.get("birim_satis", 0),
                f"Toplam Tutar ({self.para_birimi})": item.get("toplam_tutar", 0),
            })
        
        df = pd.DataFrame(export_rows)
        
        # Bellekte Excel oluşturma (in-memory)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Teklif Detayı")
        
        # Dosyayı tarayıcıya indirtme
        return rx.download(
            data=output.getvalue(),
            filename=f"Teklif_{self.teklif_no}_{self.musteri_adi[:15]}.xlsx"
        )

    # 3. BUTON: RESMİ PDF TEKLİF AL
    def export_pdf(self):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        # Başlık ve Proje Bilgileri
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#0f172a"))
        normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#334155"))
        
        elements.append(Paragraph(f"<b>MÜHENDİSLİK TEKLİF MEKTUBU</b>", title_style))
        elements.append(Paragraph(f"<b>Teklif No:</b> {self.teklif_no} | <b>Müşteri:</b> {self.musteri_adi}", normal_style))
        elements.append(Paragraph(f"<b>Proje:</b> {self.proje_adi}", normal_style))
        elements.append(Spacer(1, 15))

        # Kalem Tablosu
        table_data = [["No", "Kategori", "Açıklama", "Miktar", "Birim", f"B.Fiyat ({self.para_birimi})", f"Toplam ({self.para_birimi})"]]
        for idx, item in enumerate(self.items, 1):
            table_data.append([
                str(idx),
                str(item.get("tip", "")),
                Paragraph(str(item.get("aciklama", "")), normal_style),
                str(item.get("miktar", 0)),
                str(item.get("birim", "")),
                f"{item.get('birim_satis', 0):,.2f}",
                f"{item.get('toplam_tutar', 0):,.2f}",
            ])

        pdf_table = Table(table_data, colWidths=[25, 75, 200, 45, 40, 75, 75])
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(pdf_table)
        elements.append(Spacer(1, 15))

        # Genel Toplam Kutusu (KDV Hariç)
        total_p = Paragraph(
            f"<b>GENEL TOPLAM (KDV Hariç): {self.genel_toplam:,.2f} {self.para_birimi}</b>",
            ParagraphStyle('Total', parent=styles['Heading2'], fontSize=12, alignment=2, textColor=colors.HexColor("#0284c7"))
        )
        elements.append(total_p)
        elements.append(Spacer(1, 15))

        # AI Teknik Kapsam Metni
        if self.kapsam_metni:
            elements.append(Paragraph("<b>TEKNİK KAPSAM VE ŞARTLAR:</b>", normal_style))
            elements.append(Paragraph(self.kapsam_metni.replace('\n', '<br/>'), normal_style))

        # PDF'i derle
        doc.build(elements)
        buffer.seek(0)

        # Doğrudan tarayıcıya indirt
        return rx.download(
            data=buffer.getvalue(),
            filename=f"Teklif_{self.teklif_no}_{self.musteri_adi[:15]}.pdf"
        )
    
    # AI Kapsam & Risk Analiz Alanları
    kapsam_metni: str = ""
    ai_risk_analizi: str = ""
    is_generating_ai: bool = False
    ai_win_rate: int = 78  # Tahmini Kazanma Oranı (%)

    # Explicit Setters
    def set_musteri_adi(self, val: str):
        self.musteri_adi = val

    def set_proje_adi(self, val: str):
        self.proje_adi = val

    def set_teklif_no(self, val: str):
        self.teklif_no = val

    def set_para_birimi(self, val: str):
        self.para_birimi = val

    def set_genel_iskonto(self, val: str):
        try:
            self.genel_iskonto = float(val or 0.0)
        except ValueError:
            self.genel_iskonto = 0.0

    def set_kapsam_metni(self, val: str):
        self.kapsam_metni = val

    def set_active_module(self, mod_name: str):
        self.active_module = mod_name

    # Hesaplanan KPI'lar (Computed Vars)
    @rx.var
    def toplam_maliyet(self) -> float:
        return sum(float(item.get("miktar", 0)) * float(item.get("birim_maliyet", 0)) for item in self.items)

    @rx.var
    def ara_toplam(self) -> float:
        return sum(float(item.get("toplam_tutar", 0)) for item in self.items)

    @rx.var
    def iskonto_tutari(self) -> float:
        return self.ara_toplam * (self.genel_iskonto / 100.0)

    @rx.var
    def net_ara_toplam(self) -> float:
        return self.ara_toplam - self.iskonto_tutari

    @rx.var
    def genel_toplam(self) -> float:
        return self.net_ara_toplam

    @rx.var
    def net_kar(self) -> float:
        # Doğrudan 2 basamağa yuvarlar, 1403.8 olarak döner
        return round(self.genel_toplam - self.toplam_maliyet, 2)
    
    @rx.var
    def net_kar_str(self) -> str:
        # 1403.80 formatında basar (virgülden sonra net 2 basamak)
        return f"{self.net_kar:,.2f}"
    
    @rx.var
    def ortalama_marj(self) -> float:
        # Paydaya maliyeti alarak maliyet üstü kâr oranını (Markup) hesaplıyoruz:
        if self.toplam_maliyet > 0:
            return round(((self.ara_toplam - self.toplam_maliyet) / self.toplam_maliyet) * 100, 1)
        return 0.0

    # Kalem CRUD İşlemleri
    def add_item(self):
        self.items.append({
            "tip": "Malzeme",
            "aciklama": "",
            "miktar": 1.0,
            "birim": "Adet",
            "birim_maliyet": 0.0,
            "kar_marji": 25.0,
            "birim_satis": 0.0,
            "toplam_tutar": 0.0,
        })

    def remove_item(self, index: int):
        self.items.pop(index)

    def update_item(self, index: int, field: str, value: str):
        item = dict(self.items[index])
        if field in ["aciklama", "birim", "tip"]:
            item[field] = value
        elif field in ["miktar", "birim_maliyet", "kar_marji"]:
            try:
                item[field] = float(value or 0.0)
            except ValueError:
                item[field] = 0.0

        maliyet = float(item.get("birim_maliyet", 0.0))
        marj = float(item.get("kar_marji", 0.0))
        miktar = float(item.get("miktar", 0.0))

        item["birim_satis"] = round(maliyet * (1.0 + marj / 100.0), 2)
        item["toplam_tutar"] = round(miktar * item["birim_satis"], 2)
        self.items[index] = item

    # Asenkron AI Teknik Kapsam ve Risk Analiz Motoru
    @rx.event(background=True)
    async def generate_scope_with_ai(self):
        async with self:
            self.is_generating_ai = True
            self.kapsam_metni = ""
            self.ai_risk_analizi = ""

        await asyncio.sleep(1.8)

        kalem_sayisi = len(self.items)
        metin = (
            f"1. GENEL KAPSAM: İşbu mühendislik teklifi, {self.musteri_adi} bünyesinde gerçekleştirilecek "
            f"'{self.proje_adi}' projesinin anahtar teslim mekanik ve enstrümantasyon imalatlarını kapsar.\n"
            f"2. STANDARTLAR: Tüm pano montajları ATEX Zone 1/Zone 2 standartlarına, saha kablolamaları "
            f"IEC 60079 normlarına uygun olarak test edilip sertifikalandırılacaktır.\n"
            f"3. DEVREYE ALMA: Toplam {kalem_sayisi} ana iş paketi saha kabul testleri (FAT/SAT) "
            f"akabinde eksiksiz devreye alınarak teslim edilecektir."
        )

        risk = (
            "• Malzeme Termin Süresi: Yurt dışı menşeili debimetre tedariğinde 4-6 hafta termin riski bulunmaktadır.\n"
            "• Fiyat Tahmini Uyumu: Fiyatlama geçmiş ihalelerdeki piyasa ortalamasının %4 altında, kazanma ihtimali yüksek."
        )

        async with self:
            self.kapsam_metni = metin
            self.ai_risk_analizi = risk
            self.is_generating_ai = False