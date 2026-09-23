import reflex as rx
from .supplier_compare_state import SupplierCompareState
from .quote_builder import sidebar


def render_matris_satiri(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(
                item["malzeme_adi"],
                font_weight="500",
                color="slate.100",
                font_size="0.875rem",
            ),
            max_width="450px",
        ),
        rx.table.cell(
            rx.badge(item["miktar_str"], variant="surface", color_scheme="gray"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.badge(item["en_iyi_tedarikci"], variant="soft", color_scheme="blue"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(
                item["en_dusuk_birim_str"],
                font_weight="600",
                color="blue.300",
                font_size="0.875rem",
            ),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(
                item["satir_toplam_str"],
                font_weight="bold",
                color="green.9",
                font_size="0.875rem",
            ),
            white_space="nowrap",
        ),
    )


def supplier_compare_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Başlık ve Aksiyon Alanı
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.icon("layers", size=24, color="var(--blue-9)"),
                        rx.heading("Akıllı Tedarikçi Karşılaştırma", size="6", color="slate.100"),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        "Teklif kalemlerine ait tedarikçi birim fiyatlarını analiz edin ve en uygun sepeti oluşturun.",
                        color="slate.400",
                        font_size="0.875rem",
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.hstack(
                    # Teklif Seçim Dropdown Menüsü (Veritabanındaki güncel teklifleri listeler)
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Teklif Seçiniz...",
                            width="260px",
                            variant="surface",
                        ),
                        rx.select.content(
                            rx.select.group(
                                rx.foreach(
                                    SupplierCompareState.teklif_kodlari,
                                    lambda kod: rx.select.item(kod, value=kod),
                                ),
                            ),
                        ),
                        value=SupplierCompareState.secilen_teklif_kodu,
                        on_change=SupplierCompareState.set_teklif,
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        "Yenile",
                        variant="soft",
                        color_scheme="gray",
                        on_click=SupplierCompareState.teklifleri_guncelle,
                    )
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                padding_bottom="1.5rem",
                border_bottom="1px solid rgba(255, 255, 255, 0.08)",
            ),

            # Kalem ve Karşılaştırma Tablosu
            rx.cond(
                SupplierCompareState.karsilastirma_matrisi.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.badge(
                            f"{SupplierCompareState.karsilastirma_matrisi.length()} Kalem Listelendi",
                            color_scheme="blue",
                            variant="surface",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("check-check", size=16),
                            "En İyi Sepeti Teklife Uygula",
                            color_scheme="green",
                            on_click=SupplierCompareState.en_iyi_sepeti_teklife_uygula,
                        ),
                        width="100%",
                        align="center",
                        padding_y="0.5rem",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("AÇIKLAMA / MALZEME TANIMI"),
                                rx.table.column_header_cell("MİKTAR"),
                                rx.table.column_header_cell("EN UYGUN TEDARİKÇİ"),
                                rx.table.column_header_cell("EN İYİ BİRİM FİYAT"),
                                rx.table.column_header_cell("TOPLAM TUTAR (TL)"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                SupplierCompareState.karsilastirma_matrisi,
                                render_matris_satiri,
                            ),
                        ),
                        variant="surface",
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=48, color="slate.600"),
                        rx.text("Lütfen yukarıdaki menüden bir teklif seçin.", color="slate.400"),
                        align="center",
                    spacing="2",
                    padding="4rem",
                ),
                width="100%",
                border="1px dashed rgba(255, 255, 255, 0.1)",
                border_radius="8px",
            ),
        ),
        width="100%",
        spacing="5",
        padding="20px 28px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#060913",
)

def supplier_compare_page() -> rx.Component:
    """Sol menüyü (sidebar) içeren ve sayfa açılışında teklifleri güncelleyen ana sayfa yapısı."""
    return rx.hstack(
        sidebar(),
        supplier_compare_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=SupplierCompareState.teklifleri_guncelle,
    )