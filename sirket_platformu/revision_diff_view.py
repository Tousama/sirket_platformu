import reflex as rx
from typing import Dict, Any
from .revision_diff_state import RevisionDiffState
from .quote_builder import sidebar


def summary_card(title: str, main_val: str, sub_val: str, sub_color: str) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(title, font_size="11px", color="#94a3b8", font_weight="600"),
            rx.text(main_val, font_size="22px", font_weight="bold", color="#ffffff"),
            rx.text(sub_val, font_size="12.5px", color=sub_color, font_weight="500"),
            align_items="center",
            justify="center",
            spacing="1",
        ),
        background="#070b14",
        border="1px solid #1e293b",
        border_radius="12px",
        padding="16px",
        flex="1",
    )


def diff_row(item: Dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.badge(
                item["durum"].to(str),
                color_scheme=item["badge_color"].to(str),
                variant="surface",
                radius="full",
                size="1",
            )
        ),
        rx.table.cell(rx.text(item["malzeme"].to(str), font_size="12px", font_weight="500", color="#cbd5e1")),
        rx.table.cell(rx.text(item["eski_miktar"].to(str), font_size="12px", color="#94a3b8"), text_align="center"),
        rx.table.cell(
            rx.input(
                value=item["yeni_miktar"].to(str),
                on_change=lambda val: RevisionDiffState.update_item_qty(item["malzeme"], val),
                size="1",
                width="60px",
                text_align="center",
                background="#030712",
                border="1px solid #334155",
                color="#ffffff",
                font_weight="bold",
            ),
            text_align="center",
        ),
        rx.table.cell(rx.text(item["eski_birim_satis"].to(str) + " ₺", font_size="11.5px", color="#94a3b8"), text_align="right"),
        rx.table.cell(
            rx.input(
                value=item["yeni_birim_satis"].to(str),
                on_change=lambda val: RevisionDiffState.update_item_unit_price(item["malzeme"], val),
                debounce_timeout=400,
                size="1",
                width="110px",
                text_align="right",
                background="#030712",
                border="1px solid #0284c7",
                color="#38bdf8",
                font_weight="600",
            ),
            text_align="right",
        ),
        rx.table.cell(rx.text(item["yeni_toplam_satis"].to(str) + " ₺", font_size="12px", font_weight="600", color="#ffffff"), text_align="right"),
        rx.table.cell(
            rx.text(
                item["fark"].to(str) + " ₺",
                font_size="12px",
                font_weight="bold",
                color=rx.cond(item["is_negative"], "#f87171", "#4ade80"),
            ),
            text_align="right",
        ),
        align="center",
    )


def empty_revision_view() -> rx.Component:
    """Revizyon kaydı bulunamadığında gösterilecek boş durum kutusu"""
    return rx.card(
        rx.vstack(
            rx.icon("git-commit", size=38, color="#475569"),
            rx.text("Henüz Kayıtlı Bir Teklif Revizyonu Bulunmuyor", font_size="14px", font_weight="bold", color="#94a3b8"),
            rx.text(
                "Sistemde aynı teklif koduna ait birden fazla versiyon (örn: PT202600153 ve PT202600153-Rev1) yüklendiğinde malzeme, miktar ve fiyat farkları burada otomatik analiz edilir.",
                font_size="12px",
                color="#64748b",
                text_align="center",
                max_width="480px",
            ),
            rx.button(
                rx.icon("upload", size=15),
                "Yeni Teklif / Revizyon Yükle",
                color_scheme="blue",
                size="2",
                radius="large",
                on_click=rx.redirect("/teklif-yukle"),
            ),
            spacing="3",
            align_items="center",
            justify="center",
            padding="48px 24px",
            width="100%",
        ),
        background="#0a0f1d",
        border="1px solid #1e293b",
        border_radius="12px",
        width="100%",
    )


def revision_diff_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.icon("git-compare", size=18, color="#f59e0b"),
                    rx.heading("Revizyon & Fark Takibi", size="4", color="#ffffff"),
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
                    rx.icon("zap", size=18, color="#f59e0b"),
                    rx.text("Otomatik Revizyon & Versiyon Fark Takibi (Diff)", font_size="15px", font_weight="700", color="#ffffff"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "İki revizyon arasındaki malzeme, miktar, maliyet ve satış fiyatı farklarını anında karşılaştırın veya yeni revizyon kopyalayın.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # Koşullu Panel: Revizyon varsa tüm karşılaştırmayı aç, yoksa boş durum kutusu göster
            rx.cond(
                RevisionDiffState.has_revisions,
                rx.vstack(
                    # Karşılaştırma Seçim Alanı
                    rx.card(
                        rx.grid(
                            rx.vstack(
                                rx.text("Eski Versiyon (Baz Teklif):", font_size="11.5px", color="#94a3b8"),
                                rx.select(
                                    RevisionDiffState.eski_versiyon_secenekleri,
                                    value=RevisionDiffState.secilen_eski_versiyon,
                                    on_change=RevisionDiffState.set_secilen_eski_versiyon,
                                    width="100%",
                                    size="2",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Yeni Versiyon (Güncel Teklif):", font_size="11.5px", color="#94a3b8"),
                                rx.select(
                                    RevisionDiffState.yeni_versiyon_secenekleri,
                                    value=RevisionDiffState.secilen_yeni_versiyon,
                                    on_change=RevisionDiffState.set_secilen_yeni_versiyon,
                                    width="100%",
                                    size="2",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="1",
                            ),
                            columns="2",
                            spacing="3",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="16px",
                        width="100%",
                    ),

                    # 3 Finansal Özet Kartı
                    rx.hstack(
                        summary_card(
                            "TOPLAM MALİYET",
                            RevisionDiffState.toplam_maliyet_str,
                            RevisionDiffState.maliyet_fark_str,
                            "#22c55e",
                        ),
                        summary_card(
                            "TOPLAM SATIŞ",
                            RevisionDiffState.toplam_satis_str,
                            RevisionDiffState.satis_fark_str,
                            "#f87171",
                        ),
                        summary_card(
                            "KÂR MARJI DEĞİŞİMİ",
                            RevisionDiffState.kar_marji_str,
                            RevisionDiffState.marj_fark_str,
                            "#fbbf24",
                        ),
                        spacing="3",
                        width="100%",
                    ),

                    # Kalem Bazlı Değişiklik Raporu (Diff Tablosu)
                    rx.card(
                        rx.vstack(
                            rx.text("Kalem Bazlı Değişiklik Raporu", font_size="13px", font_weight="600", color="#ffffff"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("DURUM"),
                                        rx.table.column_header_cell("MALZEME / EKİPMAN"),
                                        rx.table.column_header_cell("ESKİ MİKTAR", text_align="center"),
                                        rx.table.column_header_cell("YENİ MİKTAR", text_align="center"),
                                        rx.table.column_header_cell("ESKİ BİRİM", text_align="right"),
                                        rx.table.column_header_cell("YENİ BİRİM (₺)", text_align="right"),
                                        rx.table.column_header_cell("YENİ TOPLAM (₺)", text_align="right"),
                                        rx.table.column_header_cell("FARK (TL)", text_align="right"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(RevisionDiffState.diff_items, diff_row)
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

                    # Alt Kısım: Yeni Revizyon Kopyası Türet Kartı
                    rx.card(
                        rx.vstack(
                            rx.text("YENİ REVİZYON KOPYASI TÜRET", font_size="12px", font_weight="bold", color="#38bdf8", letter_spacing="0.5px"),
                            rx.grid(
                                rx.vstack(
                                    rx.text("Yeni Revizyon Kodu:", font_size="11px", color="#94a3b8"),
                                    rx.input(
                                        value=RevisionDiffState.yeni_revizyon_kodu,
                                        on_change=RevisionDiffState.set_yeni_revizyon_kodu,
                                        width="100%",
                                        size="2",
                                        background="#070b14",
                                        border="1px solid #1e293b",
                                    ),
                                    align_items="start",
                                    width="100%",
                                    spacing="1",
                                ),
                                rx.vstack(
                                    rx.text("Revizyon Gerekçesi:", font_size="11px", color="#94a3b8"),
                                    rx.input(
                                        value=RevisionDiffState.revizyon_gerekcesi,
                                        on_change=RevisionDiffState.set_revizyon_gerekcesi,
                                        width="100%",
                                        size="2",
                                        background="#070b14",
                                        border="1px solid #1e293b",
                                    ),
                                    align_items="start",
                                    width="100%",
                                    spacing="1",
                                ),
                                columns="2",
                                spacing="3",
                                width="100%",
                            ),
                            rx.button(
                                rx.icon("copy", size=15),
                                "Yeni Revizyonu Başlat & Kopyala",
                                color_scheme="blue",
                                size="2",
                                border_radius="8px",
                                padding_x="18px",
                                on_click=RevisionDiffState.revizyon_kopyala_ve_baslat,
                                _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 10px rgba(59, 130, 246, 0.3)"},
                            ),
                            spacing="3",
                            width="100%",
                            align_items="start",
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
                empty_revision_view(),
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


def revision_diff_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        revision_diff_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=RevisionDiffState.on_load_recompute,
    )