import reflex as rx
from typing import Dict, Any
from .quote_upload_state import QuoteUploadState
from .quote_builder import sidebar

UPLOAD_ID = "quote_upload_input_id"


def kalem_satiri(item: Dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(item["malzeme_adi"].to(str), font_size="13px", font_weight="600", color="#ffffff")
        ),
        rx.table.cell(
            rx.text(item["miktar_str"].to(str), font_size="12.5px", color="#cbd5e1"),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(
                item["birim_fiyat_str"].to(str),
                font_size="13px",
                font_weight="bold",
                color="#38bdf8",
                font_family="monospace",
            ),
            text_align="right",
        ),
        rx.table.cell(
            rx.text(
                item["tutar_tl_str"].to(str),
                font_size="13px",
                font_weight="bold",
                color="#4ade80",
                font_family="monospace",
            ),
            text_align="right",
        ),
        align="center",
        _hover={"background": "rgba(255, 255, 255, 0.02)"},
    )


def feature_info_card(icon_name: str, title: str, desc: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.box(
                rx.icon(icon_name, size=20, color="#38bdf8"),
                padding="10px",
                border_radius="10px",
                background="rgba(56, 189, 248, 0.1)",
                border="1px solid rgba(56, 189, 248, 0.2)",
            ),
            rx.vstack(
                rx.text(title, font_size="13px", font_weight="700", color="#ffffff"),
                rx.text(desc, font_size="12px", color="#94a3b8"),
                spacing="1",
                align_items="start",
            ),
            spacing="3",
            align_items="center",
        ),
        background="#0a0f1d",
        border="1px solid #1e293b",
        border_radius="10px",
        padding="14px 18px",
        width="100%",
    )


def quote_upload_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # 1. Üst Bar
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
                rx.hstack(
                    rx.segmented_control.root(
                        rx.segmented_control.item("TRY (₺)", value="TRY"),
                        rx.segmented_control.item("USD ($)", value="USD"),
                        rx.segmented_control.item("EUR (€)", value="EUR"),
                        value="TRY",
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
                padding_bottom="12px",
                border_bottom="1px solid #1e293b",
            ),

            # 2. Modül Başlığı
            rx.vstack(
                rx.hstack(
                    rx.text("📄", font_size="16px"),
                    rx.text(
                        "Mevcut Satış Teklifini Yükleme ve Akıllı Ayrıştırma",
                        font_size="15px",
                        font_weight="700",
                        color="#ffffff",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "PetroTek antetli Excel veya PDF teklif dosyanızı seçin; antet bilgileri, malzeme kalemleri ve döviz kurları otomatik ayrıştırılır.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # 3. Yükleme Kartı (rx.form ile Korumaya Alınmış Garantili Yükleme)
            rx.card(
                rx.form(
                    rx.vstack(
                        # Üst Kısım: Dosya Seçim Alanı
                        rx.vstack(
                            rx.text("Teklif Dosyası (.xlsx / .xls / .pdf):", font_size="12px", font_weight="600", color="#94a3b8"),
                            rx.upload(
                                rx.hstack(
                                    rx.button(
                                        "Dosya Seç",
                                        type="button",
                                        color_scheme="gray",
                                        variant="surface",
                                        size="2",
                                        border_radius="6px",
                                    ),
                                    rx.text(
                                        rx.cond(
                                            rx.selected_files(UPLOAD_ID).length() > 0,
                                            rx.selected_files(UPLOAD_ID)[0],
                                            QuoteUploadState.dosya_adi,
                                        ),
                                        font_size="13px",
                                        color="#cbd5e1",
                                        overflow="hidden",
                                        text_overflow="ellipsis",
                                        white_space="nowrap",
                                    ),
                                    spacing="3",
                                    align_items="center",
                                    width="100%",
                                    padding="8px 14px",
                                ),
                                id=UPLOAD_ID,
                                border="1px solid #1e293b",
                                border_radius="8px",
                                width="100%",
                                background="#070b14",
                                accept={
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                                    "application/vnd.ms-excel": [".xls"],
                                    "application/pdf": [".pdf"],
                                },
                                max_files=1,
                                cursor="pointer",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),

                        # Alt Kısım: Sağ Altta Form Submit Butonu
                        rx.hstack(
                            rx.spacer(),
                            rx.button(
                                rx.icon("upload", size=16),
                                "Teklif Dosyasını Ayrıştır & Yükle",
                                type="submit",  # <-- rx.form submit tetikleyici
                                color_scheme="blue",
                                size="3",
                                padding_x="22px",
                                border_radius="8px",
                                _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(2, 132, 199, 0.4)"},
                            ),
                            width="100%",
                            padding_top="6px",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    on_submit=QuoteUploadState.handle_quote_upload(rx.upload_files(upload_id=UPLOAD_ID)),
                    reset_on_submit=False,
                    width="100%",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="20px 24px",
                width="100%",
            ),

            # 4. Dinamik İçerik: Ayrıştırılan Veriler veya Tanıtım Kartları
            rx.cond(
                QuoteUploadState.has_file,
                rx.vstack(
                    # Antet Özeti
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.hstack(
                                    rx.icon("check-circle", size=18, color="#22c55e"),
                                    rx.text(
                                        f"Teklif Ayrıştırıldı: {QuoteUploadState.teklif_kodu}",
                                        font_size="14px",
                                        font_weight="bold",
                                        color="#22c55e",
                                    ),
                                    spacing="2",
                                    align_items="center",
                                ),
                                rx.spacer(),
                                rx.hstack(
                                    rx.text(
                                        f"Maliyet: {QuoteUploadState.toplam_maliyet_str}",
                                        font_size="13px",
                                        color="#94a3b8",
                                    ),
                                    rx.text("|", color="#334155"),
                                    rx.text(
                                        f"Satış Tutarı: {QuoteUploadState.toplam_satis_str}",
                                        font_size="14px",
                                        font_weight="bold",
                                        color="#ffffff",
                                    ),
                                    rx.badge(
                                        QuoteUploadState.kar_marji_str,
                                        color_scheme="green",
                                        variant="surface",
                                        size="2",
                                        radius="full",
                                    ),
                                    spacing="3",
                                    align_items="center",
                                ),
                                width="100%",
                                padding_bottom="12px",
                                border_bottom="1px solid #1e293b",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("Müşteri:", font_size="11.5px", color="#64748b"),
                                    rx.text(QuoteUploadState.musteri, font_size="13.5px", font_weight="bold", color="#ffffff"),
                                    align_items="start",
                                    spacing="0",
                                    width="25%",
                                ),
                                rx.vstack(
                                    rx.text("İşin Konusu:", font_size="11.5px", color="#64748b"),
                                    rx.text(QuoteUploadState.konu, font_size="13px", color="#cbd5e1"),
                                    align_items="start",
                                    spacing="0",
                                    width="40%",
                                ),
                                rx.vstack(
                                    rx.text("Sorumlu Mühendis:", font_size="11.5px", color="#64748b"),
                                    rx.text(QuoteUploadState.muhendis, font_size="13px", color="#cbd5e1"),
                                    align_items="start",
                                    spacing="0",
                                    width="18%",
                                ),
                                rx.spacer(),
                                rx.button(
                                    "Teklifi Portala Kaydet",
                                    color_scheme="green",
                                    size="3",
                                    padding_x="22px",
                                    border_radius="8px",
                                    on_click=QuoteUploadState.teklifi_portala_kaydet,
                                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(34, 197, 94, 0.4)"},
                                ),
                                width="100%",
                                align_items="center",
                                padding_top="8px",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="18px 22px",
                        width="100%",
                    ),

                    # Kalemler Tablosu
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text("AYRIŞTIRILAN TEKLİF KALEMLERİ", font_size="12px", font_weight="bold", color="#38bdf8"),
                                rx.spacer(),
                                rx.text(
                                    QuoteUploadState.kalemler.length().to(str) + " Kalem Eşleşti",
                                    font_size="12px",
                                    color="#94a3b8",
                                ),
                                width="100%",
                                align_items="center",
                            ),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("AÇIKLAMA / MALZEME TANIMI"),
                                        rx.table.column_header_cell("MİKTAR", text_align="center", width="120px"),
                                        rx.table.column_header_cell("BİRİM SATIŞ", text_align="right", width="150px"),
                                        rx.table.column_header_cell("TOPLAM TUTAR (TL)", text_align="right", width="170px"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(QuoteUploadState.kalemler, kalem_satiri)
                                ),
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="16px",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),

                # Dosya Henüz Seçilmemişken Gösterilen Pipeline Kartları
                rx.vstack(
                    rx.card(
                        rx.hstack(
                            rx.icon("file-text", size=22, color="#64748b"),
                            rx.vstack(
                                rx.text("Henüz Bir Teklif Dosyası Yüklenmedi", font_size="14px", font_weight="700", color="#ffffff"),
                                rx.text(
                                    "Yukarıdaki alandan PetroTek formatındaki teklif dosyanızı (.xlsx veya .pdf) seçip 'Ayrıştır & Yükle' butonuna basarak sisteme aktarabilirsiniz.",
                                    font_size="12.5px",
                                    color="#94a3b8",
                                ),
                                align_items="start",
                                spacing="0",
                            ),
                            spacing="3",
                            align_items="center",
                        ),
                        background="#0a0f1d",
                        border="1px dashed #1e293b",
                        border_radius="10px",
                        padding="18px 24px",
                        width="100%",
                    ),
                    rx.grid(
                        feature_info_card("layers", "Otomatik Antet Okuma", "Teklif no, müşteri, konu, tarih ve mühendis verilerini algılar."),
                        feature_info_card("table", "Birleşik Hücre Filtresi", "Merged cells ve kaymaları düzelterek malzeme satırlarını ayrıştırır."),
                        feature_info_card("coins", "Döviz ve Kur Entegrasyonu", "TCMB kurları ile TL, USD ve EUR tutarlarını kuruşu kuruşuna eşler."),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),

            rx.spacer(),

            # 5. Sistem Bildirim Rozeti (Pill)
            rx.hstack(
                rx.spacer(),
                rx.card(
                    rx.hstack(
                        rx.icon("shield-check", size=16, color="#38bdf8"),
                        rx.text(
                            "PetroTek Veri Ayrıştırıcı v2.4 aktif • Güvenli kurumsal şablon motoru",
                            font_size="12px",
                            font_weight="500",
                            color="#bae6fd",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#0c1e33",
                    border="1px solid #0369a1",
                    border_radius="full",
                    padding="8px 18px",
                ),
                width="100%",
                padding_bottom="10px",
            ),
            spacing="3",
            width="100%",
            min_height="100%",
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