import reflex as rx
from typing import Dict, Any
from .cost_upload_state import CostUploadState
from .quote_builder import sidebar

UPLOAD_COST_ID = "cost_file_upload_input"

def eslesen_kalem_satiri(item: Dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(item["malzeme"].to(str), font_size="13px", font_weight="600", color="#ffffff")
        ),
        rx.table.cell(
            rx.text(
                item["gelen_fiyat_str"].to(str),
                font_size="13px",
                font_weight="bold",
                color="#22c55e",
                font_family="monospace",
            ),
            text_align="right",
        ),
        rx.table.cell(
            rx.text(item["pb"].to(str), font_size="12.5px", font_weight="bold", color="#facc15"),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(item["tedarikci"].to(str), font_size="13px", color="#cbd5e1")
        ),
        align="center",
        _hover={"background": "rgba(255, 255, 255, 0.02)"},
    )

def cost_upload_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("📥", font_size="16px"),
                    rx.heading("Maliyet Yükle (PDF / Excel)", size="4", color="#ffffff"),
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

            # Modül Başlığı
            rx.vstack(
                rx.hstack(
                    rx.text("📥", font_size="16px"),
                    rx.text(
                        "Tedarikçi Maliyet Dosyası Yükleme & Kısmi Maliyet Eşleme",
                        font_size="15px",
                        font_weight="700",
                        color="#ffffff",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Tedarikçiden gelen doldurulmuş RFQ Excel veya PDF'ini yükleyin; malzeme isimlerini eşleyip birim maliyetleri otomatik günceller.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # Seçim ve Dosya Yükleme Kartı
            rx.card(
                rx.vstack(
                    rx.grid(
                        # Sol: Maliyetin İşleneceği Teklif
                        rx.vstack(
                            rx.text("Maliyetin İşleneceği Teklif:", font_size="12px", color="#94a3b8"),
                            rx.select(
                                CostUploadState.teklif_secenekleri,
                                value=CostUploadState.secilen_teklif,
                                on_change=CostUploadState.set_secilen_teklif,
                                width="100%",
                                size="2",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),

                        # Sağ: Tedarikçi Dosyası (.xlsx / .pdf)
                        rx.vstack(
                            rx.text("Tedarikçi Dosyası (.xlsx / .pdf):", font_size="12px", color="#94a3b8"),
                            rx.upload(
                                rx.hstack(
                                    rx.button(
                                        "Dosya Seç",
                                        color_scheme="gray",
                                        variant="surface",
                                        size="2",
                                        border_radius="6px",
                                    ),
                                    rx.text(
                                        CostUploadState.dosya_adi,
                                        font_size="13px",
                                        color="#94a3b8",
                                        overflow="hidden",
                                        text_overflow="ellipsis",
                                        white_space="nowrap",
                                    ),
                                    spacing="3",
                                    align_items="center",
                                    width="100%",
                                    padding="6px 12px",
                                ),
                                id=UPLOAD_COST_ID,
                                border="1px solid #1e293b",
                                border_radius="8px",
                                width="100%",
                                background="#070b14",
                                accept={
                                    "application/pdf": [".pdf"],
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                                    "application/vnd.ms-excel": [".xls"],
                                },
                                max_files=1,
                                on_drop=CostUploadState.handle_cost_upload(rx.upload_files(upload_id=UPLOAD_COST_ID)),
                                cursor="pointer",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),

                    # Eşleşen Kalemler Alanı (Dosya yokken boş durum kutusu, dosya varken önizleme tablosu)
                    rx.cond(
                        CostUploadState.has_matches,
                        rx.vstack(
                            rx.card(
                                rx.vstack(
                                    rx.hstack(
                                        rx.text(
                                            "Eşleşen Kalem Maliyetleri Önizleme",
                                            font_size="13px",
                                            font_weight="bold",
                                            color="#ffffff",
                                        ),
                                        rx.spacer(),
                                        rx.text(
                                            CostUploadState.eslesen_sayisi_str,
                                            font_size="13px",
                                            font_weight="bold",
                                            color="#22c55e",
                                        ),
                                        width="100%",
                                        align_items="center",
                                        padding_bottom="8px",
                                    ),
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell("TEKLİFTEKİ MALZEME"),
                                                rx.table.column_header_cell("GELEN FİYAT", text_align="right"),
                                                rx.table.column_header_cell("PB", text_align="center"),
                                                rx.table.column_header_cell("TEDARİKÇİ FİRMA"),
                                            )
                                        ),
                                        rx.table.body(
                                            rx.foreach(CostUploadState.eslesen_kalemler, eslesen_kalem_satiri)
                                        ),
                                        width="100%",
                                    ),
                                    spacing="2",
                                    width="100%",
                                ),
                                background="#070b14",
                                border="1px solid #1e293b",
                                border_radius="10px",
                                padding="16px",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.spacer(),
                                rx.button(
                                    "Maliyetleri Teklife İşle & Kaydet",
                                    color_scheme="green",
                                    size="3",
                                    padding_x="22px",
                                    border_radius="8px",
                                    on_click=CostUploadState.maliyetleri_isle_ve_kaydet,
                                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(34, 197, 94, 0.4)"},
                                ),
                                width="100%",
                                padding_top="6px",
                            ),
                            width="100%",
                            spacing="3",
                        ),
                        rx.card(
                            rx.hstack(
                                rx.icon("file-search", size=18, color="#64748b"),
                                rx.text(
                                    "Tedarikçi dosyası henüz yüklenmedi. Excel veya PDF seçildiğinde eşleşen birim maliyetler burada listelenecektir.",
                                    font_size="12.5px",
                                    color="#94a3b8",
                                ),
                                spacing="2",
                                align_items="center",
                                justify="center",
                                padding_y="16px",
                            ),
                            background="#070b14",
                            border="1px dashed #1e293b",
                            border_radius="10px",
                            width="100%",
                        ),
                    ),
                    spacing="4",
                    width="100%",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="20px",
                width="100%",
            ),

            rx.spacer(),

            # Sağ Alttaki Bildirim Hapı (Notification Pill)
            rx.hstack(
                rx.spacer(),
                rx.card(
                    rx.hstack(
                        rx.icon("info", size=16, color="#f97316"),
                        rx.text(
                            CostUploadState.sistem_bildirim_metni,
                            font_size="12px",
                            font_weight="500",
                            color="#fed7aa",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#1f1006",
                    border="1px solid #7c2d12",
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

def cost_upload_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        cost_upload_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )