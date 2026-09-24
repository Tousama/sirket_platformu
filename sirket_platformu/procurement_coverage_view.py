import reflex as rx
from .procurement_coverage_state import ProcurementCoverageState
from .quote_builder import sidebar

def kpi_card(title: str, value: rx.Var, subtext: str, value_color: str = "#38BDF8") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                title,
                font_size="0.75rem",
                font_weight="600",
                color="#94A3B8",
                letter_spacing="0.05em",
                text_transform="uppercase",
            ),
            rx.hstack(
                rx.text(
                    value,
                    font_size="1.75rem",
                    font_weight="700",
                    color=value_color,
                    font_family="monospace",
                ),
                rx.cond(
                    subtext != "",
                    rx.text(
                        subtext,
                        font_size="1.25rem",
                        font_weight="600",
                        color=value_color,
                    ),
                ),
                spacing="2",
                align_items="baseline",
            ),
            spacing="1",
            align_items="center",
            justify_content="center",
            height="100%",
        ),
        bg="#0B132B",
        border="1px solid #1E293B",
        border_radius="12px",
        padding="1.25rem 1.5rem",
        flex="1",
        min_width="220px",
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.2)",
    )

def quote_row(item: dict) -> rx.Component:
    return rx.table.row(
        # Kapsama Kolonu (Progress Bar + Yüzde)
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.box(
                        width=item["kapsama"].to_string() + "%",
                        height="100%",
                        bg=item["status_color"],
                        border_radius="9999px",
                    ),
                    width="70px",
                    height="7px",
                    bg="#1E293B",
                    border_radius="9999px",
                    overflow="hidden",
                ),
                rx.text(
                    "%" + item["kapsama"].to_string(),
                    font_size="0.875rem",
                    font_weight="600",
                    color=item["status_color"],
                    font_family="monospace",
                ),
                spacing="3",
                align_items="center",
            ),
            vertical_align="middle",
        ),
        # Teklif No
        rx.table.cell(
            rx.text(item["teklif_no"], font_weight="600", color="#F8FAFC", font_size="0.875rem"),
            vertical_align="middle",
        ),
        # Müşteri
        rx.table.cell(
            rx.text(item["musteri"], color="#94A3B8", font_size="0.875rem"),
            vertical_align="middle",
        ),
        # Toplam Kalem
        rx.table.cell(
            rx.text(item["toplam_kalem"].to_string(), color="#F8FAFC", font_size="0.875rem", text_align="center"),
            vertical_align="middle",
        ),
        # Fiyatı Olan
        rx.table.cell(
            rx.text(item["fiyati_olan"].to_string(), color="#10B981", font_weight="600", font_size="0.875rem", text_align="center"),
            vertical_align="middle",
        ),
        # Eksik Kalan (Hatanın çözüldüğü yer: item["eksik_kalan"].to(int) > 0 veya != 0)
        rx.table.cell(
            rx.text(
                item["eksik_kalan"].to_string(),
                color=rx.cond(item["eksik_kalan"].to(int) > 0, "#F43F5E", "#64748B"),
                font_weight="600",
                font_size="0.875rem",
                text_align="center",
            ),
            vertical_align="middle",
        ),
        # Teklif Tutarı
        rx.table.cell(
            rx.text(item["teklif_tutari"], font_weight="600", color="#F8FAFC", font_size="0.875rem", text_align="right", font_family="monospace"),
            vertical_align="middle",
        ),
        border_bottom="1px solid #1E293B",
        _hover={"bg": "#0D1B2A"},
    )

def procurement_coverage_main() -> rx.Component:
    return rx.box(
        # Üst Navigasyon Çubuğu (Header)
        rx.hstack(
            rx.hstack(
                rx.icon("menu", color="#94A3B8", size=20, cursor="pointer"),
                rx.text("📊", font_size="1.2rem"),
                rx.text("Satınalma Kapsama Raporu", font_weight="700", color="#FFFFFF", font_size="1rem"),
                rx.text("/", color="#475569", font_weight="500"),
                rx.text("PetroTek Engineering", color="#64748B", font_size="0.9rem"),
                spacing="3",
                align_items="center",
            ),
            rx.hstack(
                # Para Birimi Seçimi
                rx.hstack(
                    rx.button(
                        "TRY (₺)",
                        bg=rx.cond(ProcurementCoverageState.currency == "TRY (₺)", "#2563EB", "transparent"),
                        color="#FFFFFF",
                        font_size="0.75rem",
                        font_weight="600",
                        padding="4px 12px",
                        border_radius="6px",
                        height="auto",
                        on_click=lambda: ProcurementCoverageState.set_currency("TRY (₺)"),
                    ),
                    rx.button(
                        "USD ($)",
                        bg=rx.cond(ProcurementCoverageState.currency == "USD ($)", "#2563EB", "transparent"),
                        color="#94A3B8",
                        font_size="0.75rem",
                        font_weight="600",
                        padding="4px 12px",
                        border_radius="6px",
                        height="auto",
                        on_click=lambda: ProcurementCoverageState.set_currency("USD ($)"),
                    ),
                    rx.button(
                        "EUR (€)",
                        bg=rx.cond(ProcurementCoverageState.currency == "EUR (€)", "#2563EB", "transparent"),
                        color="#94A3B8",
                        font_size="0.75rem",
                        font_weight="600",
                        padding="4px 12px",
                        border_radius="6px",
                        height="auto",
                        on_click=lambda: ProcurementCoverageState.set_currency("EUR (€)"),
                    ),
                    bg="#0F172A",
                    border="1px solid #1E293B",
                    border_radius="8px",
                    padding="3px",
                ),
                rx.link(
                    rx.button(
                        rx.icon("plus", size=16),
                        "Yeni Teklif",
                        bg="#0284C7",
                        color="#FFFFFF",
                        font_size="0.8rem",
                        font_weight="600",
                        border_radius="8px",
                        padding="6px 14px",
                        height="auto",
                        _hover={"bg": "#0369A1"},
                    ),
                    href="/teklif-hazirla",
                ),
                rx.box(
                    rx.icon("bell", color="#94A3B8", size=18),
                    rx.box(width="6px", height="6px", bg="#EAB308", border_radius="full", position="absolute", top="2px", right="2px"),
                    position="relative",
                    cursor="pointer",
                    padding="4px",
                ),
                spacing="4",
                align_items="center",
            ),
            width="100%",
            justify_content="space-between",
            padding="1rem 2rem",
            border_bottom="1px solid #1E293B",
            bg="#050B14",
        ),
        
        # İçerik Alanı
        rx.vstack(
            rx.vstack(
                rx.hstack(
                    rx.text("📊", font_size="1.4rem"),
                    rx.heading("Satınalma Kapsama & Eksik Maliyet Analizi", size="6", color="#FFFFFF", font_weight="700"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Açık tekliflerin satınalma birim maliyeti tamamlanma oranlarını izleyin; fiyatı eksik kalan kalemleri satınalmaya liste olarak iletin.",
                    color="#94A3B8",
                    font_size="0.875rem",
                ),
                spacing="1",
                align_items="flex-start",
                width="100%",
                padding_bottom="1rem",
                border_bottom="1px solid #131E31",
            ),
            
            # KPI Kartları
            rx.hstack(
                kpi_card("Genel Kapsama Ortalaması", ProcurementCoverageState.genel_kapsama_ortalamasi, "", value_color="#38BDF8"),
                kpi_card("Maliyeti Tam (%100)", ProcurementCoverageState.tam_maliyetli_sayisi.to_string(), "Teklif", value_color="#10B981"),
                kpi_card("Kısmi Maliyetli (%1-%99)", ProcurementCoverageState.kismi_maliyetli_sayisi.to_string(), "Teklif", value_color="#FBBF24"),
                kpi_card("Eksik Kalan Kalemler", ProcurementCoverageState.eksik_kalem_sayisi.to_string(), "Malzeme", value_color="#FB7185"),
                spacing="4",
                width="100%",
                padding_y="1rem",
            ),

            # Tablo
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("KAPSAMA", color="#94A3B8", font_size="0.75rem", font_weight="700"),
                            rx.table.column_header_cell("TEKLİF NO", color="#94A3B8", font_size="0.75rem", font_weight="700"),
                            rx.table.column_header_cell("MÜŞTERİ", color="#94A3B8", font_size="0.75rem", font_weight="700"),
                            rx.table.column_header_cell("TOPLAM KALEM", color="#94A3B8", font_size="0.75rem", font_weight="700", text_align="center"),
                            rx.table.column_header_cell("FİYATI OLAN", color="#94A3B8", font_size="0.75rem", font_weight="700", text_align="center"),
                            rx.table.column_header_cell("EKSİK KALAN", color="#94A3B8", font_size="0.75rem", font_weight="700", text_align="center"),
                            rx.table.column_header_cell("TEKLİF TUTARI", color="#94A3B8", font_size="0.75rem", font_weight="700", text_align="right"),
                            border_bottom="1px solid #1E293B",
                        )
                    ),
                    rx.table.body(
                        rx.foreach(ProcurementCoverageState.quotes, quote_row)
                    ),
                    width="100%",
                    variant="surface",
                ),
                bg="#08101E",
                border="1px solid #1A2639",
                border_radius="10px",
                overflow="hidden",
                width="100%",
                margin_top="0.5rem",
            ),

            # Excel İndir Butonu
            rx.box(
                rx.button(
                    rx.icon("download", size=16),
                    "Eksik Fiyat Kalemleri Raporunu İndir (.xlsx)",
                    bg="#BE123C",
                    color="#FFFFFF",
                    font_size="0.875rem",
                    font_weight="600",
                    border_radius="8px",
                    padding="0.75rem 1.5rem",
                    height="auto",
                    _hover={"bg": "#9F1239"},
                    on_click=ProcurementCoverageState.export_excel_missing,
                ),
                width="100%",
                display="flex",
                justify_content="flex-end",
                padding_top="1rem",
            ),
            spacing="4",
            padding="2rem",
            width="100%",
            max_width="1400px",
            margin="0 auto",
        ),
        bg="#030712",
        min_height="100vh",
        width="100%",
    )
def procurement_coverage_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        procurement_coverage_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=ProcurementCoverageState.sync_from_dashboard,
    )