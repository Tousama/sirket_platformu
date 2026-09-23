import reflex as rx
from typing import Dict, Any
from .price_catalog_state import PriceCatalogState
from .quote_builder import sidebar

def catalog_row(item: Dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(item["tanim"].to(str), font_size="13px", font_weight="600", color="#ffffff")
        ),
        rx.table.cell(
            rx.text(item["marka"].to(str), font_size="12.5px", font_weight="600", color="#38bdf8")
        ),
        rx.table.cell(
            rx.text(item["birim"].to(str), font_size="12px", color="#94a3b8"),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(item["pb"].to(str), font_size="12px", font_weight="600", color="#facc15"),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(item["maliyet_str"].to(str), font_size="12.5px", color="#cbd5e1", font_family="monospace"),
            text_align="right",
        ),
        rx.table.cell(
            rx.text(item["satis_str"].to(str), font_size="13px", font_weight="bold", color="#ffffff", font_family="monospace"),
            text_align="right",
        ),
        rx.table.cell(
            rx.text(item["marj_str"].to(str), font_size="12.5px", font_weight="bold", color="#4ade80"),
            text_align="center",
        ),
        rx.table.cell(
            rx.text(item["kaynak"].to(str), font_size="12px", color="#94a3b8")
        ),
        rx.table.cell(
            rx.badge(
                item["guncellik"].to(str),
                color_scheme="green",
                variant="surface",
                radius="full",
                size="1",
            ),
            text_align="center",
        ),
        align="center",
        _hover={"background": "rgba(255, 255, 255, 0.02)"},
    )

def price_catalog_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("📚", font_size="16px"),
                    rx.heading("Fiyat Hafızası & Katalog", size="4", color="#ffffff"),
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

            # Modül Başlığı ve Havuzu Senkronize Et Butonu
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.text("📚", font_size="16px"),
                        rx.text("Malzeme & Ekipman Fiyat Hafızası", font_size="15px", font_weight="700", color="#ffffff"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "Geçmiş tekliflerden toplanan birim maliyetler, satış fiyatları, kâr marjları ve tedarikçi katalog verileri.",
                        font_size="12.5px",
                        color="#94a3b8",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("refresh-cw", size=15),
                    "Havuzu Senkronize Et",
                    variant="surface",
                    color_scheme="gray",
                    size="2",
                    border_radius="8px",
                    on_click=PriceCatalogState.sync_pool,
                    _hover={"background": "rgba(255, 255, 255, 0.08)"},
                ),
                width="100%",
                align_items="center",
                padding_y="4px",
            ),

            # Arama ve Filtreleme Kartı
            rx.card(
                rx.hstack(
                    rx.input(
                        placeholder="Malzeme, Marka veya Teklif No Ara...",
                        value=PriceCatalogState.search_query,
                        on_change=PriceCatalogState.set_search_query,
                        size="2",
                        flex="3",
                        background="#070b14",
                        border="1px solid #1e293b",
                        color="#ffffff",
                    ),
                    rx.select(
                        PriceCatalogState.brand_options,
                        value=PriceCatalogState.selected_brand,
                        on_change=PriceCatalogState.set_selected_brand,
                        size="2",
                        flex="1.5",
                    ),
                    rx.select(
                        PriceCatalogState.currency_options,
                        value=PriceCatalogState.selected_currency,
                        on_change=PriceCatalogState.set_selected_currency,
                        size="2",
                        flex="1",
                    ),
                    rx.spacer(),
                    rx.text(
                        PriceCatalogState.total_count_str,
                        font_size="13px",
                        color="#94a3b8",
                        font_weight="600",
                        padding_x="8px",
                    ),
                    width="100%",
                    spacing="3",
                    align_items="center",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="14px 18px",
                width="100%",
            ),

            # Fiyat Kataloğu Tablosu
            rx.card(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("MALZEME / EKİPMAN TANIMI"),
                            rx.table.column_header_cell("MARKA / TEDARİKÇİ"),
                            rx.table.column_header_cell("BİRİM", text_align="center"),
                            rx.table.column_header_cell("PB", text_align="center"),
                            rx.table.column_header_cell("SON ALIŞ MALİYETİ", text_align="right"),
                            rx.table.column_header_cell("SON SATIŞ FİYATI", text_align="right"),
                            rx.table.column_header_cell("KÂR MARJI", text_align="center"),
                            rx.table.column_header_cell("KAYNAK TEKLİF & MÜŞTERİ"),
                            rx.table.column_header_cell("GÜNCELLİK", text_align="center"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(PriceCatalogState.filtered_items, catalog_row)
                    ),
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
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#060913",
    )

def price_catalog_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        price_catalog_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )