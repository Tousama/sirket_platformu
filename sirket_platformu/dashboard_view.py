import reflex as rx
from typing import Dict, Any
from .dashboard_state import DashboardState
from .quote_builder import sidebar

def kpi_box(
    title: str,
    count: str,
    amount: str,
    subtext: str,
    icon_name: str,
    kpi_key: str,
    is_alert: bool = False,
) -> rx.Component:
    is_active = (DashboardState.selected_kpi == kpi_key)
    
    border_color = rx.cond(
        is_active,
        rx.cond(is_alert, "#ef4444", "#38bdf8"),
        rx.cond(is_alert, "rgba(239, 68, 68, 0.4)", "#1e293b")
    )
    
    bg_color = rx.cond(
        is_active,
        rx.cond(is_alert, "rgba(239, 68, 68, 0.12)", "rgba(56, 189, 248, 0.08)"),
        "#0a0f1d"
    )

    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(
                    title, 
                    font_size="12px", 
                    color=rx.cond(is_alert, "#f87171", "#94a3b8"), 
                    font_weight="600"
                ),
                rx.hstack(
                    rx.text(count, font_size="22px", font_weight="bold", color="#ffffff"),
                    rx.text("Adet", font_size="12px", color="#64748b", margin_top="8px"),
                    spacing="2",
                    align_items="baseline",
                ),
                rx.text(
                    rx.cond(amount != "", amount + " " + DashboardState.currency_symbol, subtext),
                    font_size="13px",
                    font_weight=rx.cond(amount != "", "600", "400"),
                    color=rx.cond(is_alert, "#f87171", rx.cond(amount != "", "#38bdf8", "#64748b")),
                ),
                align_items="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon_name, size=20, color=rx.cond(is_alert, "#ef4444", "#38bdf8")),
                padding="10px",
                border_radius="10px",
                background="rgba(255, 255, 255, 0.02)",
            ),
            width="100%",
            align_items="start",
        ),
        background=bg_color,
        border=f"1.5px solid {border_color}",
        border_radius="12px",
        padding="16px",
        flex="1",
        cursor="pointer",
        on_click=DashboardState.select_kpi(kpi_key),
        _hover={"transform": "translateY(-2px)", "transition": "0.15s ease"},
    )

def status_badge(durum: str) -> rx.Component:
    return rx.match(
        durum,
        ("Müşteride", rx.badge("Müşteride", color_scheme="cyan", variant="solid", radius="full", size="1")),
        ("Hazırlanıyor", rx.badge("Hazırlanıyor", color_scheme="gray", variant="surface", radius="full", size="1")),
        ("Kazanıldı", rx.badge("Kazanıldı", color_scheme="green", variant="solid", radius="full", size="1")),
        ("Onaylandı", rx.badge("Onaylandı", color_scheme="green", variant="solid", radius="full", size="1")),
        ("Revizyonda", rx.badge("Revizyonda", color_scheme="amber", variant="solid", radius="full", size="1")),
        ("Reddedildi", rx.badge("Reddedildi", color_scheme="ruby", variant="solid", radius="full", size="1")),
        ("Reddedildi (Zaman Aşımı)", rx.badge("Reddedildi (Zaman Aşımı)", color_scheme="ruby", variant="solid", radius="full", size="1")),
        rx.badge(durum, variant="surface", radius="full", size="1"),
    )

def pie_chart_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text("Teklif Durum Dağılımı", font_size="13px", font_weight="600", color="#ffffff"),
                rx.spacer(),
                rx.text("Adet Bazında", font_size="11px", color="#64748b"),
                width="100%",
            ),
            # Donut Grafik
            rx.box(
                rx.recharts.pie_chart(
                    rx.recharts.pie(
                        data=DashboardState.status_pie_data,
                        data_key="value",
                        name_key="name",
                        cx="50%",
                        cy="50%",
                        inner_radius=50,
                        outer_radius=80,
                        padding_angle=4,
                        stroke="none",
                    ),
                    rx.recharts.graphing_tooltip(),
                    width="100%",
                    height=190,
                ),
                width="100%",
                display="flex",
                justify="center",
            ),
            # Tıklanabilir 4 Lejant Butonu
            rx.hstack(
                rx.hstack(
                    rx.box(
                        width="9px",
                        height="9px",
                        border_radius="2px",
                        background=rx.cond(DashboardState.hide_hazirlaniyor, "#475569", "#22d3ee"),
                    ),
                    rx.text(
                        "Hazırlanıyor",
                        font_size="11.5px",
                        color=rx.cond(DashboardState.hide_hazirlaniyor, "#64748b", "#cbd5e1"),
                        text_decoration=rx.cond(DashboardState.hide_hazirlaniyor, "line-through", "none"),
                        user_select="none",
                    ),
                    spacing="2",
                    align_items="center",
                    cursor="pointer",
                    padding="3px 7px",
                    border_radius="4px",
                    background="rgba(255, 255, 255, 0.03)",
                    on_click=DashboardState.toggle_hazirlaniyor,
                    _hover={"background": "rgba(255, 255, 255, 0.08)"},
                ),
                rx.hstack(
                    rx.box(
                        width="9px",
                        height="9px",
                        border_radius="2px",
                        background=rx.cond(DashboardState.hide_kazanildi, "#475569", "#10b981"),
                    ),
                    rx.text(
                        "Kazanıldı",
                        font_size="11.5px",
                        color=rx.cond(DashboardState.hide_kazanildi, "#64748b", "#cbd5e1"),
                        text_decoration=rx.cond(DashboardState.hide_kazanildi, "line-through", "none"),
                        user_select="none",
                    ),
                    spacing="2",
                    align_items="center",
                    cursor="pointer",
                    padding="3px 7px",
                    border_radius="4px",
                    background="rgba(255, 255, 255, 0.03)",
                    on_click=DashboardState.toggle_kazanildi,
                    _hover={"background": "rgba(255, 255, 255, 0.08)"},
                ),
                rx.hstack(
                    rx.box(
                        width="9px",
                        height="9px",
                        border_radius="2px",
                        background=rx.cond(DashboardState.hide_musteride, "#475569", "#06b6d4"),
                    ),
                    rx.text(
                        "Müşteride",
                        font_size="11.5px",
                        color=rx.cond(DashboardState.hide_musteride, "#64748b", "#cbd5e1"),
                        text_decoration=rx.cond(DashboardState.hide_musteride, "line-through", "none"),
                        user_select="none",
                    ),
                    spacing="2",
                    align_items="center",
                    cursor="pointer",
                    padding="3px 7px",
                    border_radius="4px",
                    background="rgba(255, 255, 255, 0.03)",
                    on_click=DashboardState.toggle_musteride,
                    _hover={"background": "rgba(255, 255, 255, 0.08)"},
                ),
                rx.hstack(
                    rx.box(
                        width="9px",
                        height="9px",
                        border_radius="2px",
                        background=rx.cond(DashboardState.hide_reddedildi, "#475569", "#ef4444"),
                    ),
                    rx.text(
                        "Reddedildi (Zaman Aşımı)",
                        font_size="11.5px",
                        color=rx.cond(DashboardState.hide_reddedildi, "#64748b", "#cbd5e1"),
                        text_decoration=rx.cond(DashboardState.hide_reddedildi, "line-through", "none"),
                        user_select="none",
                    ),
                    spacing="2",
                    align_items="center",
                    cursor="pointer",
                    padding="3px 7px",
                    border_radius="4px",
                    background="rgba(255, 255, 255, 0.03)",
                    on_click=DashboardState.toggle_reddedildi,
                    _hover={"background": "rgba(255, 255, 255, 0.08)"},
                ),
                justify="center",
                spacing="2",
                width="100%",
                flex_wrap="wrap",
                padding_top="4px",
            ),
            width="100%",
            spacing="1",
        ),
        background="#0a0f1d",
        border="1px solid #1e293b",
        border_radius="12px",
        padding="16px",
    )

def dashboard_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Header Barı
            rx.hstack(
                rx.hstack(
                    rx.heading("Dashboard (Analiz)", size="4", color="#ffffff"),
                    rx.text("/", color="#475569"),
                    rx.text("PetroTek Engineering", color="#94a3b8", font_size="13px"),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                # TCMB Rozeti + Para Birimi Seçicisi + Yeni Teklif Butonu
                rx.hstack(
                    rx.badge(
                        rx.icon("landmark", size=13),
                        DashboardState.last_rate_update,
                        color_scheme="green",
                        variant="surface",
                        radius="full",
                        size="1",
                    ),
                    rx.icon_button(
                        rx.icon("refresh-cw", size=13),
                        loading=DashboardState.is_updating_rates,
                        on_click=DashboardState.refresh_tcmb_now,
                        variant="ghost",
                        color_scheme="gray",
                        size="1",
                    ),
                    rx.segmented_control.root(
                        rx.segmented_control.item("TRY (₺)", value="TRY"),
                        rx.segmented_control.item("USD ($)", value="USD"),
                        rx.segmented_control.item("EUR (€)", value="EUR"),
                        value=DashboardState.selected_currency,
                        on_change=DashboardState.set_currency,
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

            # 4 Kritik KPI Kartı (Tıklanabilir Filtreler)
            rx.hstack(
                kpi_box("Talep Edilen Teklif", DashboardState.total_quotes_count.to(str), DashboardState.total_quotes_amount_str, "", "layers", "ALL"),
                kpi_box(">1 Gün Geciken Hazırlık", DashboardState.delayed_count.to(str), "", "Müdahale gereken acil talepler", "clock", "DELAYED", is_alert=True),
                kpi_box("Cevap Beklenen (Müşteride)", DashboardState.waiting_customer_count.to(str), DashboardState.waiting_customer_amount_str, "", "send", "WAITING"),
                kpi_box("Kazanılan & Sipariş", DashboardState.won_count.to(str), DashboardState.won_amount_str, "", "trophy", "WON"),
                width="100%",
                spacing="3",
            ),

            # Grafikler Alanı (2 Kolon)
            rx.grid(
                pie_chart_card(),
                # Sağ: Yaşlanma Dağılımı Bar Grafiği
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Cevap Beklenenlerin Yaşlanma Dağılımı", font_size="13px", font_weight="600", color="#ffffff"),
                            rx.spacer(),
                            rx.text("Hacim Dağılımı", font_size="11px", color="#64748b"),
                            width="100%",
                        ),
                        rx.box(
                            rx.recharts.bar_chart(
                                rx.recharts.bar(data_key="hacim", fill="#22d3ee", radius=[4, 4, 0, 0]),
                                rx.recharts.x_axis(data_key="range", stroke="#64748b", font_size="11px"),
                                rx.recharts.y_axis(stroke="#64748b", font_size="11px"),
                                rx.recharts.graphing_tooltip(),
                                data=DashboardState.aging_bar_data,
                                width="100%",
                                height=220,
                            ),
                            width="100%",
                        ),
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="16px",
                ),
                columns="2",
                spacing="3",
                width="100%",
            ),

            # Kayıtlı Teklif Portföyü Tablosu
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.hstack(
                            rx.icon("folder-kanban", size=16, color="#38bdf8"),
                            rx.text("KAYITLI TEKLİF PORTFÖYÜ", font_size="13px", font_weight="bold", color="#ffffff"),
                            rx.badge(DashboardState.filtered_quotes_count.to(str) + " Teklif", color_scheme="gray", variant="surface", radius="full", size="1"),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.input(
                                rx.input.slot(rx.icon("search", size=14, color="#64748b")),
                                placeholder="No, Müşteri veya Konu...",
                                value=DashboardState.search_query,
                                on_change=DashboardState.set_search_query,
                                size="1",
                                width="220px",
                            ),
                            rx.select(
                                ["Tümü", "Müşteride", "Hazırlanıyor", "Kazanıldı", "Reddedildi (Zaman Aşımı)"],
                                value=DashboardState.status_filter,
                                on_change=DashboardState.set_status_filter,
                                size="1",
                            ),
                            rx.button(
                                rx.icon("plus", size=14),
                                "Yeni",
                                color_scheme="blue",
                                size="1",
                                on_click=rx.redirect("/teklif-hazirla"),
                            ),
                            spacing="2",
                        ),
                        width="100%",
                        padding_bottom="8px",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("TEKLİF KODU"),
                                rx.table.column_header_cell("MÜŞTERİ / TESİS"),
                                rx.table.column_header_cell("KONU"),
                                rx.table.column_header_cell("SORUMLU"),
                                rx.table.column_header_cell("DURUM"),
                                rx.table.column_header_cell("MALİYET"),
                                rx.table.column_header_cell("SATIŞ TUTARI"),
                                rx.table.column_header_cell("KÂR MARJI"),
                                rx.table.column_header_cell("İŞLEM"),
                            )
                        ),
# dashboard_view.py içindeki rx.table.body kısmında ilgili hücreyi şöyle değiştirin:

                        rx.table.body(
                            rx.foreach(
                                DashboardState.filtered_quotes,
                                lambda row: rx.table.row(
                                    rx.table.cell(rx.text(row["kod"].to(str), font_size="12px", font_weight="bold", color="#ffffff")),
                                    rx.table.cell(rx.text(row["musteri"].to(str), font_size="12px", font_weight="600", color="#cbd5e1")),
                                    rx.table.cell(rx.text(row["konu"].to(str), font_size="12px", color="#94a3b8")),
                                    rx.table.cell(rx.text(row["sorumlu"].to(str), font_size="12px", color="#94a3b8")),
                                    rx.table.cell(status_badge(row["durum"].to(str))),
                                    rx.table.cell(rx.text(row["formatted_maliyet"].to(str), font_size="12px", color="#cbd5e1")),
                                    rx.table.cell(rx.text(row["formatted_satis"].to(str), font_size="12px", font_weight="bold", color="#ffffff")),
                                    rx.table.cell(
                                        rx.text(
                                            row["formatted_kar_marji"].to(str),
                                            font_size="12px",
                                            font_weight="bold",
                                            color="#4ade80",
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.icon_button(
                                            rx.icon("sliders-horizontal", size=14),
                                            variant="ghost",
                                            color_scheme="gray",
                                            size="1",
                                        ),
                                        text_align="center",
                                    ),
                                    align="center",
                                )
                            )
                        ),
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                width="100%",
                padding="16px",
            ),
            spacing="3",
            width="100%",
        ),
        padding="20px 28px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#060913",
    )

def dashboard_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        dashboard_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=DashboardState.on_load
    )