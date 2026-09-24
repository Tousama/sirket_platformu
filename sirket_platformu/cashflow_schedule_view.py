import reflex as rx
from .cashflow_schedule_state import CashflowScheduleState
from .quote_builder import sidebar


def kpi_card(title: str, val: str, val_color: str, sub_text: str = "", sub_color: str = "#94a3b8") -> rx.Component:
    """Görseldeki 4'lü üst özet kart tasarımı"""
    return rx.card(
        rx.vstack(
            rx.text(title, font_size="10.5px", color="#94a3b8", font_weight="700", letter_spacing="0.04em"),
            rx.text(val, font_size="21px", font_weight="800", color=val_color, letter_spacing="-0.02em"),
            rx.cond(
                sub_text != "",
                rx.text(sub_text, font_size="11.5px", color=sub_color, font_weight="500"),
                rx.box(height="16px")
            ),
            align_items="center",
            justify="center",
            spacing="1",
        ),
        background="#0a1020",
        border="1px solid #151e33",
        border_radius="14px",
        padding="20px 16px",
        flex="1",
    )


def custom_legend_item(color: str, label: str, is_dashed: bool = False) -> rx.Component:
    """Görseldeki özel grafik gösterge rozeti"""
    return rx.hstack(
        rx.box(
            width="12px",
            height="12px",
            border=f"2px {'dashed' if is_dashed else 'solid'} {color}",
            background="transparent",
            border_radius="2px",
        ),
        rx.text(label, font_size="12px", font_weight="600", color="#cbd5e1"),
        align_items="center",
        spacing="2",
    )


def cashflow_schedule_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                    rx.text("📊", font_size="16px"),
                    rx.heading("Nakit Akışı (Cash-Flow) & Tedarik Çizelgesi", size="4", color="#ffffff", font_weight="700"),
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
                        value=CashflowScheduleState.currency,
                        on_change=CashflowScheduleState.set_currency,
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

            # Modül Başlığı ve Proje Seçim Satırı
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.text("📊", font_size="18px"),
                        rx.text(
                            "Hakediş İlerleme (Cash-Flow) & Tedarik Çizelgesi",
                            font_size="16px",
                            font_weight="800",
                            color="#ffffff",
                            letter_spacing="-0.01em",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "Tedarikçi termin süreleri, avans ve kabul şartlarına göre projenin haftalık kasa akışını (S-Curve) ve finansman açığını simüle edin.",
                        font_size="12.5px",
                        color="#94a3b8",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                # Proje Seçici Açılır Menü
                rx.hstack(
                    rx.text("Aktif Proje / Teklif:", font_size="12.5px", color="#94a3b8", font_weight="600"),
                    rx.select(
                        CashflowScheduleState.proje_secenekleri,
                        value=CashflowScheduleState.secilen_proje,
                        on_change=CashflowScheduleState.set_secilen_proje,
                        size="2",
                        radius="medium",
                        color_scheme="blue",
                        width="260px",
                    ),
                    align_items="center",
                    spacing="2",
                    background="#0a1020",
                    padding="6px 12px",
                    border_radius="8px",
                    border="1px solid #151e33",
                ),
                width="100%",
                align_items="center",
                padding_y="6px",
            ),

            # 4 KPI Kartı
            rx.hstack(
                kpi_card("KRİTİK YOL (TERMİN)", CashflowScheduleState.kritik_yol_termin, "#ffffff"),
                kpi_card("TOPLAM PROJE SÜRESİ", CashflowScheduleState.toplam_proje_suresi, "#38bdf8"),
                kpi_card("TOPLAM SATIŞ TUTARI", CashflowScheduleState.toplam_satis_str, "#34d399"),
                kpi_card(
                    "EN DÜŞÜK KASA BAKİYESİ",
                    CashflowScheduleState.en_dusuk_kasa_str,
                    CashflowScheduleState.kasa_durum_renk,
                    CashflowScheduleState.kasa_durum_metni,
                    CashflowScheduleState.kasa_durum_renk
                ),
                spacing="3",
                width="100%",
            ),

            # S-Curve Grafik Kartı
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Kümülatif Hakediş vs Harcama (S-Curve)",
                            font_size="13.5px",
                            font_weight="700",
                            color="#ffffff",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            custom_legend_item("#10b981", "Kümülatif Tahsilat (₺)"),
                            custom_legend_item("#ef4444", "Kümülatif Harcama (₺)"),
                            custom_legend_item("#38bdf8", "Net Kasa Pozisyonu (₺)", is_dashed=True),
                            spacing="4",
                            align_items="center",
                        ),
                        width="100%",
                        padding_bottom="12px",
                    ),

                    # Recharts Line Chart
                    rx.box(
                        rx.recharts.line_chart(
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 3",
                                stroke="#1e293b",
                                vertical=True,
                                horizontal=True,
                            ),
                            rx.recharts.x_axis(
                                data_key="hafta",
                                stroke="#64748b",
                                font_size="11.5px",
                                tick_line=False,
                                axis_line=True,
                            ),
                            rx.recharts.y_axis(
                                stroke="#64748b",
                                font_size="11px",
                                tick_line=False,
                                axis_line=False,
                            ),
                            rx.recharts.tooltip(
                                content_style={
                                    "backgroundColor": "#070b14",
                                    "borderColor": "#1e293b",
                                    "borderRadius": "8px",
                                    "color": "#ffffff",
                                    "fontSize": "12px",
                                }
                            ),
                            rx.recharts.line(
                                data_key="kumulatif_tahsilat",
                                stroke="#10b981",
                                stroke_width=2.5,
                                type_="monotone",
                                dot={"stroke": "#10b981", "strokeWidth": 2, "r": 3.5, "fill": "#070b14"},
                                active_dot={"r": 5, "fill": "#10b981"},
                            ),
                            rx.recharts.line(
                                data_key="kumulatif_harcama",
                                stroke="#ef4444",
                                stroke_width=2.5,
                                type_="monotone",
                                dot={"stroke": "#ef4444", "strokeWidth": 2, "r": 3.5, "fill": "#070b14"},
                                active_dot={"r": 5, "fill": "#ef4444"},
                            ),
                            rx.recharts.line(
                                data_key="net_kasa",
                                stroke="#38bdf8",
                                stroke_width=2.5,
                                stroke_dasharray="4 4",
                                type_="monotone",
                                dot={"stroke": "#38bdf8", "strokeWidth": 2, "r": 3.5, "fill": "#070b14"},
                                active_dot={"r": 5, "fill": "#38bdf8"},
                            ),
                            data=CashflowScheduleState.curve_data,
                            width="100%",
                            height=360,
                        ),
                        width="100%",
                        padding_top="6px",
                    ),

                    spacing="2",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                border_radius="14px",
                padding="22px 24px",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#030712",
    )


def cashflow_schedule_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        cashflow_schedule_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=CashflowScheduleState.on_load,
    )