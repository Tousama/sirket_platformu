import reflex as rx
from typing import Dict, Any
from .quote_upload_state import QuoteUploadState
from .quote_builder import sidebar

UPLOAD_ID = "quote_file_upload"

def kalem_tablo_satiri(item: Dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item["id"].to(str), font_size="12px", color="#64748b", text_align="center")),
        rx.table.cell(rx.text(item["malzeme_adi"].to(str), font_size="12.5px", font_weight="500", color="#ffffff")),
        rx.table.cell(
            rx.hstack(
                rx.text(item["miktar"].to(str), font_size="12px", font_weight="bold", color="#ffffff"),
                rx.text(item["birim"].to(str), font_size="11.5px", color="#94a3b8"),
                spacing="1",
                justify="center",
            ),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(item["birim_satis_str"].to(str) + " " + item["para_birimi"].to(str), font_size="12px", color="#cbd5e1", font_family="monospace"),
            text_align="right",
        ),
        rx.table.cell(
            rx.text(item["toplam_satis_str"].to(str) + " " + item["para_birimi"].to(str), font_size="12px", font_weight="bold", color="#38bdf8", font_family="monospace"),
            text_align="right",
        ),
        # Kullanıcının düzenleyebileceği birim maliyet kutusu
        rx.table.cell(
            rx.input(
                value=item["birim_maliyet_str"].to(str),
                on_change=lambda val: QuoteUploadState.update_item_maliyet(item["id"], val),
                size="1",
                width="110px",
                text_align="right",
                background="#030712",
                border="1px solid #334155",
                color="#4ade80",
                font_weight="600",
            ),
            text_align="right",
        ),
        align="center",
        _hover={"background": "rgba(255, 255, 255, 0.02)"},
    )

def quote_upload_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("📄", font_size="16px"),
                    rx.heading("Teklif Yükle (PDF / Excel)", size="4", color="#ffffff"),
                    rx.text("/", color="#475569"),
                    rx.text("PetroTek Engineering", color="#94a3b8", font_size="13px"),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=15),
                    "Yeni Teklif",
                    color_scheme="blue",
                    size="2",
                    radius="full",
                    on_click=rx.redirect("/teklif-hazirla"),
                ),
                width="100%",
                padding_bottom="12px",
                border_bottom="1px solid #1e293b",
            ),

            # Modül Başlığı ve Dışarıdaki Simülasyon Butonu
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.text("📄", font_size="16px"),
                        rx.text("Çoklu Para Birimli PDF / Excel'den Teklif Yükle", font_size="15px", font_weight="700", color="#ffffff"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "PDF veya Excel dosyasını seçin; antet, müşteri adı ve dövizli BOM tablosu akıllı parser ile taranıp kalem kalem listelenir.",
                        font_size="12.5px",
                        color="#94a3b8",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("sparkles", size=15),
                    "Örnek Dosya Simüle Et",
                    variant="surface",
                    color_scheme="cyan",
                    size="2",
                    border_radius="8px",
                    on_click=QuoteUploadState.simule_et,
                    _hover={"background": "rgba(6, 182, 212, 0.15)"},
                ),
                width="100%",
                align_items="center",
                padding_y="4px",
            ),

            # Yükleme Alanı (Dropzone + Buton)
            rx.card(
                rx.upload(
                    rx.vstack(
                        rx.icon("file-up", size=42, color="#38bdf8"),
                        rx.text("Teklif PDF veya Excel Dosyasını Buraya Bırakın", font_size="14px", font_weight="bold", color="#ffffff"),
                        rx.text(".pdf, .xlsx, .xls formatları desteklenir", font_size="12px", color="#94a3b8"),
                        rx.button(
                            rx.icon("folder-open", size=15),
                            "Dosya Seç",
                            color_scheme="gray",
                            variant="surface",
                            size="2",
                            border_radius="8px",
                            margin_top="6px",
                        ),
                        align_items="center",
                        justify="center",
                        spacing="2",
                        padding_y="22px",
                    ),
                    id=UPLOAD_ID,
                    border="1.5px dashed #334155",
                    border_radius="10px",
                    width="100%",
                    background="rgba(15, 23, 42, 0.4)",
                    accept={"application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"], "application/vnd.ms-excel": [".xls"]},
                    max_files=1,
                    on_drop=QuoteUploadState.handle_upload(rx.upload_files(upload_id=UPLOAD_ID)),
                    cursor="pointer",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="16px",
                width="100%",
            ),

            # Okunan Dosya Özeti & Kalem Tablosu
            rx.cond(
                QuoteUploadState.has_file,
                rx.vstack(
                    # Antet Özeti Kartı
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.hstack(
                                    rx.icon("check-circle-2", size=18, color="#22c55e"),
                                    rx.text("Dosya Okundu: " + QuoteUploadState.dosya_adi, font_size="13px", font_weight="bold", color="#4ade80"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                rx.spacer(),
                                rx.hstack(
                                    rx.text("Maliyet: " + QuoteUploadState.maliyet_str, font_size="12.5px", color="#94a3b8"),
                                    rx.text(" | ", color="#334155"),
                                    rx.text("Satış: " + QuoteUploadState.toplam_str, font_size="13.5px", font_weight="bold", color="#ffffff"),
                                    rx.badge(QuoteUploadState.kar_marji_str + " Marj", color_scheme="green", variant="surface", size="1"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                width="100%",
                                align_items="center",
                                padding_bottom="10px",
                                border_bottom="1px solid #1e293b",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("Müşteri:", font_size="11.5px", color="#94a3b8"),
                                    rx.text(QuoteUploadState.musteri, font_size="13px", font_weight="bold", color="#ffffff"),
                                    align_items="start", spacing="0", flex="1.2",
                                ),
                                rx.vstack(
                                    rx.text("Konu:", font_size="11.5px", color="#94a3b8"),
                                    rx.text(QuoteUploadState.konu, font_size="13px", color="#cbd5e1"),
                                    align_items="start", spacing="0", flex="1.8",
                                ),
                                rx.vstack(
                                    rx.text("Sorumlu:", font_size="11.5px", color="#94a3b8"),
                                    rx.text(QuoteUploadState.sorumlu, font_size="13px", color="#cbd5e1"),
                                    align_items="start", spacing="0", flex="1",
                                ),
                                rx.button(
                                    "Teklifi Portala Kaydet",
                                    color_scheme="blue",
                                    size="3",
                                    padding_x="22px",
                                    border_radius="8px",
                                    on_click=QuoteUploadState.portala_kaydet,
                                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(2, 132, 199, 0.4)"},
                                ),
                                width="100%",
                                align_items="center",
                                padding_top="4px",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="16px 20px",
                        width="100%",
                    ),

                    # Taranan Kalemler Tablosu
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text("TARANAN TEKLİF KALEMLERİ (BOM LİSTESİ)", font_size="12px", font_weight="bold", color="#38bdf8"),
                                rx.spacer(),
                                rx.text("Birim maliyetleri tablodan düzenleyebilirsiniz.", font_size="11px", color="#64748b"),
                                width="100%",
                                align_items="center",
                            ),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("#", text_align="center", width="40px"),
                                        rx.table.column_header_cell("MALZEME / HİZMET TANIMI"),
                                        rx.table.column_header_cell("MİKTAR", text_align="center", width="100px"),
                                        rx.table.column_header_cell("BİRİM SATIŞ", text_align="right"),
                                        rx.table.column_header_cell("TOPLAM SATIŞ", text_align="right"),
                                        rx.table.column_header_cell("BİRİM MALİYET (₺)", text_align="right", width="130px"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(QuoteUploadState.kalemler, kalem_tablo_satiri)
                                ),
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="18px",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#060913",
    )

def quote_upload_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        quote_upload_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )