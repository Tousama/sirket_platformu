import reflex as rx
from typing import Dict, Any
from .quote_state import QuoteState

# Görseldeki 19 Modüllük Orijinal Liste
MODULES_LIST = [
    ("bar-chart-3", "Dashboard (Analiz)"),
    ("file-plus-2", "Yeni Teklif Hazırla & Çıktı Al"),
    ("file-text", "Teknik Teklif & Kapsam Dosyası Üreteci"),
    ("zap", "Saha İşçilik & Montaj Motoru (A/S)"),
    ("git-compare", "Revizyon & Fark Takibi"),
    ("crosshair", "Rakip Fiyat Tahmini & İstihbarat"),
    ("trending-up", "Dinamik Fiyatlama & Kazanma Tahmini"),
    ("percent", "Marj & İskonto Simülatörü"),
    ("database", "Fiyat Hafızası & Katalog"),
    ("file-up", "Teklif Yükle (PDF / Excel)"),
    ("receipt", "Maliyet Yükle (PDF / Excel)"),
    ("scales", "Akıllı Tedarikçi Karşılaştırma & Sepet O..."),
    ("line-chart", "Satınalma Kapsama Raporu"),
    ("package-check", "Satınalma & RFQ İhracı"),
    ("banknote", "Nakit Akışı (Cash-Flow) & Tedarik Çizel..."),
    ("shield-alert", "Teknik Şartname & Datasheet Doğrulayıcı"),
    ("mail", "Gelen Teklif Mailleri (IMAP)"),
    ("sliders-horizontal", "Teklif Düzenle / Sil"),
    ("users", "Mühendis Yönetimi"),
]

MODULE_ROUTES = {
    "Dashboard (Analiz)": "/",
    "Yeni Teklif Hazırla & Çıktı Al": "/teklif-hazirla",
    "Teknik Teklif & Kapsam Dosyası Üreteci": "/teknik-kapsam",
    "Saha İşçilik & Montaj Motoru (A/S)": "/iscilik-motoru",
    "Revizyon & Fark Takibi": "/revizyon-takibi",
    "Rakip Fiyat Tahmini & İstihbarat": "/rakip-istihbarat",
    "Dinamik Fiyatlama & Kazanma Tahmini": "/dinamik-fiyatlama",
    "Marj & İskonto Simülatörü": "/marj-simulatoru",
    "Fiyat Hafızası & Katalog": "/fiyat-hafizasi",
    "Teklif Yükle (PDF / Excel)": "/teklif-yukle",
    "Maliyet Yükle (PDF / Excel)": "/maliyet-yukle",  # <-- Eklendi
}


def sidebar_item(icon_name: str, label: str) -> rx.Component:
    is_active = (QuoteState.active_module == label)
    target_route = MODULE_ROUTES.get(label, "")

    item_content = rx.hstack(
        rx.box(
            rx.box(
                width="7px",
                height="7px",
                border_radius="full",
                background=rx.cond(is_active, "#ff3344", "transparent"),
            ),
            width="12px",
            height="12px",
            border_radius="full",
            border=rx.cond(is_active, "1.5px solid #ff3344", "1.5px solid #4a5568"),
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.icon(icon_name, size=15, color=rx.cond(is_active, "#60a5fa", "#94a3b8")),
        rx.text(
            label,
            font_size="12.5px",
            color=rx.cond(is_active, "#ffffff", "#94a3b8"),
            font_weight=rx.cond(is_active, "600", "400"),
            overflow="hidden",
            white_space="nowrap",
            text_overflow="ellipsis",
        ),
        spacing="3",
        align_items="center",
        width="100%",
        padding_y="6px",
        padding_x="10px",
        border_radius="6px",
        background=rx.cond(is_active, "rgba(59, 130, 246, 0.12)", "transparent"),
        border=rx.cond(is_active, "1px solid rgba(59, 130, 246, 0.35)", "1px solid transparent"),
        cursor="pointer",
        # Tıklandığında ilgili sayfaya git:
        on_click=lambda: rx.redirect(target_route) if target_route else QuoteState.set_active_module(label),
        _hover={"background": "rgba(255, 255, 255, 0.04)"},
    )
    
    # Rota henüz yoksa tıklanabilir pasif eleman olarak kalsın:
    return item_content


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text("Tüm Modüller (19)", font_size="13px", font_weight="600", color="#f8fafc"),
                rx.spacer(),
                rx.icon("chevron-down", size=15, color="#64748b"),
                width="100%",
                padding="10px 14px",
                background="#111827",
                border="1px solid #1f2937",
                border_radius="8px",
                margin_bottom="12px",
            ),
            rx.vstack(
                *[sidebar_item(icon, name) for icon, name in MODULES_LIST],
                spacing="1",
                width="100%",
            ),
            width="100%",
            align_items="start",
        ),
        width="280px",
        min_width="280px",
        height="100vh",
        background="#070b14",
        border_right="1px solid #1e293b",
        padding="16px 12px",
        overflow_y="auto",
    )

def kpi_card(title: str, value: str, subtext: str, badge_color: str, icon_name: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(title, font_size="11.5px", color="#94a3b8", font_weight="500"),
                rx.text(value, font_size="21px", font_weight="bold", color="#ffffff"),
                rx.text(subtext, font_size="11px", color=badge_color),
                align_items="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon_name, size=20, color=badge_color),
                padding="10px",
                border_radius="10px",
                background="rgba(255, 255, 255, 0.03)",
                border="1px solid rgba(255, 255, 255, 0.07)",
            ),
            width="100%",
            align_items="center",
        ),
        background="#0f172a",
        border="1px solid #1e293b",
        border_radius="12px",
        padding="14px",
        flex="1",
    )

def item_row(item: Dict[str, Any], index: int) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.select(
                ["Malzeme", "İşçilik", "Enstrümantasyon", "Pano / İmalat", "Mühendislik"],
                value=item["tip"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "tip", val),
                size="1",
                variant="surface",
            ),
            width="140px",
        ),
        rx.table.cell(
            rx.input(
                value=item["aciklama"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "aciklama", val),
                placeholder="Kalem açıklaması, teknik marka/model detayları...",
                size="2",
                variant="surface",
            )
        ),
        rx.table.cell(
            rx.input(
                value=item["miktar"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "miktar", val),
                width="75px",
                size="2",
            )
        ),
        rx.table.cell(
            rx.select(
                ["Adet", "Metre", "Set", "Saat", "Gün", "Kg"],
                value=item["birim"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "birim", val),
                size="1",
                width="80px",
            )
        ),
        rx.table.cell(
            rx.input(
                value=item["birim_maliyet"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "birim_maliyet", val),
                width="95px",
                size="2",
            )
        ),
        rx.table.cell(
            rx.input(
                value=item["kar_marji"].to(str),
                on_change=lambda val: QuoteState.update_item(index, "kar_marji", val),
                width="70px",
                size="2",
            )
        ),
        rx.table.cell(
            rx.text(item["birim_satis"].to(str) + " " + QuoteState.para_birimi, font_weight="500", color="#cbd5e1", font_size="13px")
        ),
        rx.table.cell(
            rx.text(item["toplam_tutar"].to(str) + " " + QuoteState.para_birimi, font_weight="bold", color="#38bdf8", font_size="13px")
        ),
        rx.table.cell(
            rx.icon_button(
                rx.icon("trash-2", size=15),
                color_scheme="red",
                variant="ghost",
                on_click=lambda: QuoteState.remove_item(index),
                size="1",
            ),
            text_align="center",
        ),
    )

def main_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Header & Aksiyon Butonları
            rx.hstack(
                    rx.button(
                        rx.icon("save", size=15), 
                        "Taslak Kaydet", 
                        variant="soft", 
                        color_scheme="gray", 
                        size="2",
                        on_click=QuoteState.save_draft,  # <-- 1. Fonksiyon
                    ),
                    rx.button(
                        rx.icon("file-spreadsheet", size=15), 
                        "Excel İndir", 
                        variant="surface", 
                        color_scheme="cyan", 
                        size="2",
                        on_click=QuoteState.export_excel,  # <-- 2. Fonksiyon
                    ),
                    rx.button(
                        rx.icon("file-down", size=16), 
                        "Resmi PDF Teklif Al", 
                        color_scheme="blue", 
                        size="2",
                        on_click=QuoteState.export_pdf,  # <-- 3. Fonksiyon
                    ),
                    spacing="2",
                ),

            # 4'lü KPI Kartları
            rx.hstack(
                kpi_card(
                    "TOPLAM HAM MALİYET", 
                    QuoteState.toplam_maliyet.to(str) + " " + QuoteState.para_birimi, 
                    "Satınalma & taşeron toplamı", 
                    "#94a3b8", 
                    "boxes"
                ),
                kpi_card(
                    "NET KÂR PROJEKSİYONU", 
                    QuoteState.net_kar.to(str) + " " + QuoteState.para_birimi, 
                    "İskonto sonrası net kâr", 
                    "#4ade80", 
                    "wallet"
                ),
                kpi_card(
                    "AĞIRLIKLI KÂR (MARKUP)", 
                    "%" + QuoteState.ortalama_marj.to(str), 
                    "Maliyet üstü ortalama kâr oranı", 
                    "#38bdf8", 
                    "percent"
                ),
                kpi_card(
                    "KAZANMA TAHMİNİ (AI)", 
                    "%" + QuoteState.ai_win_rate.to(str), 
                    "Yüksek ihale kazanma skoru", 
                    "#a855f7", 
                    "sparkles"
                ),
                width="100%",
                spacing="3",
            ),

            # Müşteri ve İhale Parametreleri Kartı
            rx.card(
                rx.grid(
                    rx.vstack(
                        rx.text("Müşteri / Kurum Adı", font_size="11.5px", color="#94a3b8"),
                        rx.input(value=QuoteState.musteri_adi, on_change=QuoteState.set_musteri_adi, size="2", width="100%"),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Proje & İhale Başlığı", font_size="11.5px", color="#94a3b8"),
                        rx.input(value=QuoteState.proje_adi, on_change=QuoteState.set_proje_adi, size="2", width="100%"),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Teklif Kodu", font_size="11.5px", color="#94a3b8"),
                        rx.input(value=QuoteState.teklif_no, on_change=QuoteState.set_teklif_no, size="2", width="100%"),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Para Birimi", font_size="11.5px", color="#94a3b8"),
                        rx.select(["USD", "EUR", "TRY"], value=QuoteState.para_birimi, on_change=QuoteState.set_para_birimi, size="2", width="100%"),
                        align_items="start",
                        spacing="1",
                    ),
                    columns="4",
                    spacing="3",
                    width="100%",
                ),
                background="#0f172a",
                border="1px solid #1e293b",
                border_radius="12px",
                width="100%",
            ),

            # Kalem Listesi & Tablo
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text("Teklif Kalemleri & İmalat Dağılımı", font_size="14px", font_weight="600", color="#ffffff"),
                        rx.spacer(),
                        rx.button(
                            rx.icon("plus", size=15),
                            "Yeni Kalem Ekle",
                            variant="surface",
                            color_scheme="blue",
                            size="1",
                            on_click=QuoteState.add_item,
                        ),
                        width="100%",
                        padding_bottom="6px",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Kategori"),
                                rx.table.column_header_cell("Açıklama & Teknik Özellikler"),
                                rx.table.column_header_cell("Miktar"),
                                rx.table.column_header_cell("Birim"),
                                rx.table.column_header_cell("Birim Mal."),
                                rx.table.column_header_cell("Marj %"),
                                rx.table.column_header_cell("Birim Satış"),
                                rx.table.column_header_cell("Toplam Satış"),
                                rx.table.column_header_cell(""),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(QuoteState.items, lambda item, idx: item_row(item, idx))
                        ),
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                background="#0f172a",
                border="1px solid #1e293b",
                border_radius="12px",
                width="100%",
            ),

            # Alt Panel: AI Zekası & Finansal Kapanış
            rx.grid(
                # Sol Kısım: AI Teknik Kapsam & Risk Motoru
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("sparkles", size=17, color="#c084fc"),
                            rx.text("AI Mühendislik & Standart Analiz Asistanı", font_size="13.5px", font_weight="600", color="#ffffff"),
                            rx.spacer(),
                            rx.button(
                                "Teknik Kapsam & Riskleri Üret",
                                loading=QuoteState.is_generating_ai,
                                on_click=QuoteState.generate_scope_with_ai,
                                size="1",
                                color_scheme="purple",
                            ),
                            width="100%",
                            padding_bottom="4px",
                        ),
                        rx.text_area(
                            value=QuoteState.kapsam_metni,
                            on_change=QuoteState.set_kapsam_metni,
                            placeholder="ATEX, IEC standartlarına uygunluk maddeleri, iş kapsamı ve montaj gereksinimleri AI tarafından buraya otomatik doldurulur...",
                            height="130px",
                            width="100%",
                            background="#070b14",
                            border="1px solid #1e293b",
                            font_size="12px",
                        ),
                        rx.cond(
                            QuoteState.ai_risk_analizi != "",
                            rx.box(
                                rx.text("Tedarik & İhale Risk Analizi:", font_size="11.5px", font_weight="600", color="#fbbf24"),
                                rx.text(QuoteState.ai_risk_analizi, font_size="11.5px", color="#cbd5e1", white_space="pre-line"),
                                background="rgba(251, 191, 36, 0.08)",
                                border="1px solid rgba(251, 191, 36, 0.2)",
                                border_radius="8px",
                                padding="10px",
                                width="100%",
                            ),
                        ),
                        width="100%",
                        spacing="2",
                    ),
                    background="#0f172a",
                    border="1px solid #1e293b",
                    border_radius="12px",
                ),

                # Sağ Kısım: Finansal İskonto & Kapanış Tablosu
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Ara Toplam:", font_size="13px", color="#94a3b8"),
                            rx.spacer(),
                            rx.text(QuoteState.ara_toplam.to(str) + " " + QuoteState.para_birimi, font_weight="600", font_size="14px", color="#ffffff"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.text("Genel İskonto Oranı (%):", font_size="13px", color="#94a3b8"),
                            rx.spacer(),
                            rx.input(
                                value=QuoteState.genel_iskonto.to(str),
                                on_change=QuoteState.set_genel_iskonto,
                                width="80px",
                                size="1",
                            ),
                            width="100%",
                            align_items="center",
                        ),
                        rx.cond(
                            QuoteState.genel_iskonto > 0,
                            rx.hstack(
                                rx.text("İskonto Tutarı:", font_size="13px", color="#f87171"),
                                rx.spacer(),
                                rx.text("-" + QuoteState.iskonto_tutari.to(str) + " " + QuoteState.para_birimi, font_size="13px", color="#f87171"),
                                width="100%",
                            ),
                        ),
                        rx.divider(color_scheme="gray"),
                        rx.hstack(
                            rx.vstack(
                                rx.text("GENEL TEKLİF BEDELİ:", font_size="14px", font_weight="bold", color="#ffffff"),
                                rx.badge("Fiyatlara KDV Dahil Değildir", color_scheme="gray", variant="soft", size="1"),
                                align_items="start",
                                spacing="1",
                            ),
                            rx.spacer(),
                            rx.text(
                                QuoteState.genel_toplam.to(str) + " " + QuoteState.para_birimi,
                                font_size="20px",
                                font_weight="bold",
                                color="#38bdf8",
                            ),
                            width="100%",
                            align_items="center",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    background="#0f172a",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="18px",
                ),
                columns="2",
                spacing="3",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        padding="24px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#0b0f19",
    )

def quote_builder_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        main_content(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )