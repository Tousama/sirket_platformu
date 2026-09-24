import reflex as rx
from .quote_edit_state import QuoteEditState
from .quote_builder import sidebar


def audit_log_status_badge(durum: str) -> rx.Component:
    return rx.text(
        durum,
        font_size="12px",
        font_weight="700",
        color="#38bdf8",
    )


def tab_genel_bilgiler_ve_bom() -> rx.Component:
    """1. Sekme: Ana Bilgiler, Butonlar ve Kalem Kalem Maliyet Tablosu"""
    return rx.vstack(
        # Ana Güncelleme Kartı (Müşteri, Durum, Satış, Maliyet, Konu)
        rx.box(
            rx.vstack(
                rx.text(
                    QuoteEditState.current_code + " BİLGİLERİNİ GÜNCELLE",
                    font_size="12.5px",
                    font_weight="800",
                    color="#38bdf8",
                    letter_spacing="0.02em",
                    padding_bottom="4px",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("Müşteri / Tesis:", font_size="11.5px", color="#94a3b8"),
                        rx.input(
                            value=QuoteEditState.edit_musteri,
                            on_change=QuoteEditState.set_edit_musteri,
                            size="2",
                            width="100%",
                            background="#040813",
                            border="1px solid #1e293b",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Teklif Durumu:", font_size="11.5px", color="#94a3b8"),
                        rx.select(
                            QuoteEditState.status_options,
                            value=QuoteEditState.edit_durum,
                            on_change=QuoteEditState.set_edit_durum,
                            size="2",
                            width="100%",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("Satış Tutarı (TL):", font_size="11.5px", color="#94a3b8"),
                        rx.input(
                            value=QuoteEditState.edit_satis,
                            on_change=QuoteEditState.set_edit_satis,
                            size="2",
                            width="100%",
                            background="#040813",
                            border="1px solid #1e293b",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Toplam Maliyet (TL) [Kalemlerden Otomatik]:", font_size="11.5px", color="#94a3b8"),
                        rx.input(
                            value=QuoteEditState.edit_maliyet,
                            on_change=QuoteEditState.set_edit_maliyet,
                            size="2",
                            width="100%",
                            background="#040813",
                            border="1px solid #1e293b",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Teklif Konusu:", font_size="11.5px", color="#94a3b8"),
                    rx.input(
                        value=QuoteEditState.edit_konu,
                        on_change=QuoteEditState.set_edit_konu,
                        size="2",
                        width="100%",
                        background="#040813",
                        border="1px solid #1e293b",
                    ),
                    align_items="start",
                    spacing="1",
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Teklifi Kalıcı Olarak Sil",
                        background="#831843",
                        _hover={"background": "#9d174d"},
                        color="#fbcfe8",
                        size="2",
                        font_weight="600",
                        border_radius="6px",
                        cursor="pointer",
                        on_click=QuoteEditState.delete_quote,
                    ),
                    rx.spacer(),
                    rx.button(
                        "Değişiklikleri Kaydet & Logla",
                        background="#0284c7",
                        _hover={"background": "#0369a1"},
                        color="#ffffff",
                        size="2",
                        font_weight="700",
                        border_radius="6px",
                        cursor="pointer",
                        on_click=QuoteEditState.save_changes,
                    ),
                    width="100%",
                    padding_top="10px",
                    align_items="center",
                ),
                spacing="3",
                width="100%",
            ),
            background="#080e1a",
            border="1px solid #1a2538",
            border_radius="10px",
            padding="20px 24px",
            width="100%",
        ),

        # BOM Kalemleri & Kalem Kalem Maliyet Tablosu
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("layers", size=16, color="#38bdf8"),
                    rx.text(
                        QuoteEditState.current_code + " BOM KALEMLERİ & BİRİM MALİYET GİRİŞİ",
                        font_size="12.5px",
                        font_weight="700",
                        color="#ffffff",
                    ),
                    rx.spacer(),
                    rx.text("Maliyet kutusuna yazıp çıktığınızda toplam otomatik güncellenir", font_size="11.5px", color="#64748b"),
                    spacing="2",
                    align_items="center",
                    width="100%",
                    padding_bottom="6px",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("MALZEME / HİZMET ADI", font_size="11px", color="#64748b"),
                            rx.table.column_header_cell("MİKTAR", font_size="11px", color="#64748b"),
                            # 1. Sırada: Birim Maliyet (Mavi)
                            rx.table.column_header_cell("BİRİM MALİYET (TL)", font_size="11px", color="#38bdf8"),
                            # 2. Sırada: Birim Satış (Yeşil)
                            rx.table.column_header_cell("BİRİM SATIŞ (TL)", font_size="11px", color="#4ade80"),
                            rx.table.column_header_cell("TOPLAM MALİYET", font_size="11px", color="#64748b"),
                            rx.table.column_header_cell("TOPLAM SATIŞ", font_size="11px", color="#64748b"),
                            rx.table.column_header_cell("KÂR MARJI", font_size="11px", color="#64748b"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            QuoteEditState.items,
                            lambda item: rx.table.row(
                                rx.table.cell(rx.text(item["malzeme_adi"].to(str), font_size="12px", color="#e2e8f0", font_weight="500")),
                                rx.table.cell(rx.text(item["miktar"].to(str) + " " + item["birim"].to(str), font_size="12px", color="#94a3b8")),
                                # 1. Sırada: Birim Maliyet Giriş Kutusu (Mavi)
                                rx.table.cell(
                                    rx.input(
                                        value=item["birim_maliyet_val"].to(str),
                                        on_blur=lambda val: QuoteEditState.update_item_cost(item["id"].to(int), val),
                                        placeholder="0.00",
                                        size="1",
                                        width="110px",
                                        background="#040813",
                                        border="1px solid #334155",
                                        color="#38bdf8",
                                        font_weight="bold",
                                    )
                                ),
                                # 2. Sırada: Birim Satış Giriş Kutusu (Yeşil)
                                rx.table.cell(
                                    rx.input(
                                        value=item["birim_satis_val"].to(str),
                                        on_blur=lambda val: QuoteEditState.update_item_sale(item["id"].to(int), val),
                                        placeholder="0.00",
                                        size="1",
                                        width="110px",
                                        background="#040813",
                                        border="1px solid #166534",
                                        color="#4ade80",
                                        font_weight="bold",
                                    )
                                ),
                                rx.table.cell(rx.text(item["toplam_maliyet_str"].to(str), font_size="12px", color="#f87171", font_weight="600")),
                                rx.table.cell(rx.text(item["toplam_satis_str"].to(str), font_size="12px", color="#4ade80", font_weight="bold")),
                                rx.table.cell(rx.text(item["kar_marji_str"].to(str), font_size="12px", color="#38bdf8", font_weight="bold")),
                                align="center",
                            )
                        )
                    ),
                    width="100%",
                ),
                width="100%",
                spacing="2",
            ),
            background="#080e1a",
            border="1px solid #1a2538",
            border_radius="10px",
            padding="20px 24px",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def tab_audit_log_tarihce() -> rx.Component:
    """2. Sekme: Durum ve Fiyat Tarihçesi Tablosu"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("history", size=16, color="#38bdf8"),
                rx.text(
                    QuoteEditState.current_code + " Durum & Fiyat Tarihçesi (Audit Log)",
                    font_size="13px",
                    font_weight="700",
                    color="#ffffff",
                ),
                rx.spacer(),
                rx.badge(QuoteEditState.audit_logs_count.to(str) + " Kayıt", color_scheme="gray", variant="surface", radius="full", size="1"),
                spacing="2",
                align_items="center",
                width="100%",
                padding_bottom="6px",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("İŞLEM TARİHİ", font_size="11px", color="#64748b"),
                        rx.table.column_header_cell("OLAY / DURUM", font_size="11px", color="#64748b"),
                        rx.table.column_header_cell("GÜNCEL TUTAR", font_size="11px", color="#64748b"),
                        rx.table.column_header_cell("AÇIKLAMA", font_size="11px", color="#64748b"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        QuoteEditState.audit_logs,
                        lambda log: rx.table.row(
                            rx.table.cell(rx.text(log["islem_tarihi"].to(str), font_size="12px", color="#94a3b8")),
                            rx.table.cell(audit_log_status_badge(log["olay_durum"].to(str))),
                            rx.table.cell(rx.text(log["tutar_formatli"].to(str), font_size="12px", font_weight="bold", color="#ffffff")),
                            rx.table.cell(rx.text(log["aciklama"].to(str), font_size="12px", color="#cbd5e1")),
                            align="center",
                        )
                    )
                ),
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        background="#080e1a",
        border="1px solid #1a2538",
        border_radius="10px",
        padding="20px 24px",
        width="100%",
    )


def quote_edit_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # 1. Üst Navigasyon Barı
            rx.hstack(
                rx.hstack(
                    rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                    rx.icon("settings", size=16, color="#cbd5e1"),
                    rx.heading(
                        "Teklif Düzenle / Sil",
                        size="4",
                        color="#ffffff",
                        font_weight="700",
                    ),
                    rx.text("/", color="#475569"),
                    rx.text("PetroTek Engineering", color="#94a3b8", font_size="13px"),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.segmented_control.root(
                        rx.segmented_control.item("TRY (₺)", value="TRY (₺)"),
                        rx.segmented_control.item("USD ($)", value="USD ($)"),
                        rx.segmented_control.item("EUR (€)", value="EUR (€)"),
                        value=QuoteEditState.currency,
                        on_change=QuoteEditState.set_currency,
                        radius="full",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("plus", size=15),
                        "Yeni Teklif",
                        color_scheme="blue",
                        size="2",
                        radius="full",
                        on_click=rx.redirect("/teklif-hazirla"),
                    ),
                    rx.icon_button(
                        rx.icon("bell", size=16),
                        variant="ghost",
                        color_scheme="gray",
                        size="2",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                width="100%",
                padding_bottom="16px",
                border_bottom="1px solid #151e33",
            ),

            # 2. Modül Başlığı ve Açıklama
            rx.vstack(
                rx.hstack(
                    rx.icon("settings", size=18, color="#ffffff"),
                    rx.heading("Teklif Yönetimi, BOM & Durum Tarihçesi", size="4", color="#ffffff", font_weight="700"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Teklif bilgilerini güncelleyin, BOM kalemlerini doğrudan düzenleyin veya silme işlemi gerçekleştirin.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                spacing="1",
                align_items="start",
                padding_top="6px",
            ),

            # 3. Ortak Teklif Seçim Kartı (Her iki sekmede de geçerli olan ana seçim)
            rx.box(
                rx.vstack(
                    rx.text("İşlem Yapılacak Teklifi Seçin:", font_size="12px", color="#cbd5e1", font_weight="500"),
                    rx.select(
                        QuoteEditState.quote_options,
                        value=QuoteEditState.selected_quote_label,
                        on_change=QuoteEditState.set_selected_quote_label,
                        width="100%",
                        size="2",
                    ),
                    width="100%",
                    spacing="2",
                ),
                background="#080e1a",
                border="1px solid #1a2538",
                border_radius="10px",
                padding="16px 20px",
                width="100%",
            ),

            # 4. Sekmeli Yapı (Tabs)
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        rx.hstack(rx.icon("file-text", size=14), rx.text("Teklif Bilgileri & BOM Kalemleri"), spacing="2", align_items="center"),
                        value="genel_bom",
                    ),
                    rx.tabs.trigger(
                        rx.hstack(rx.icon("clock", size=14), rx.text("Durum & Fiyat Tarihçesi (Audit Log)"), spacing="2", align_items="center"),
                        value="tarihce",
                    ),
                    color_scheme="blue",
                    size="2",
                ),
                rx.tabs.content(
                    tab_genel_bilgiler_ve_bom(),
                    value="genel_bom",
                    padding_top="16px",
                ),
                rx.tabs.content(
                    tab_audit_log_tarihce(),
                    value="tarihce",
                    padding_top="16px",
                ),
                default_value="genel_bom",
                width="100%",
            ),

            spacing="4",
            width="100%",
        ),
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#030712",
    )


def quote_edit_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        quote_edit_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=QuoteEditState.on_load,
    )