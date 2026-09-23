import reflex as rx
from .dynamic_pricing_state import DynamicPricingState
from .quote_builder import sidebar

def stat_kpi_card(title: str, val_str: str, val_color: str = "#38bdf8") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(title, font_size="10.5px", color="#94a3b8", font_weight="600", text_align="center"),
            rx.text(val_str, font_size="20px", font_weight="bold", color=val_color, text_align="center"),
            align_items="center",
            justify="center",
            spacing="1",
        ),
        background="#070b14",
        border="1px solid #1e293b",
        border_radius="10px",
        padding="14px",
        flex="1",
    )

def dynamic_pricing_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("🎯", font_size="16px"),
                    rx.heading("Dinamik Fiyatlama & Kazanma Tahmini", size="4", color="#ffffff"),
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
                    rx.text("🎯", font_size="16px"),
                    rx.text("Dinamik Fiyatlama & Kazanma Tahmini", font_size="15px", font_weight="700", color="#ffffff"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Kâr marjını müşterinin geçmiş ihale kabul davranışına ve beklenen getiriye (expected profit) göre optimize edin.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # Üst Kısım: Teklif Seçimi ve Simüle Satış Fiyatı Kartı
            rx.card(
                rx.hstack(
                    rx.vstack(
                        rx.text("Analiz Edilecek Teklifi Seçin:", font_size="11.5px", color="#94a3b8"),
                        rx.select(
                            DynamicPricingState.teklif_secenekleri,
                            value=DynamicPricingState.secilen_teklif,
                            on_change=DynamicPricingState.set_secilen_teklif,
                            width="100%",
                            size="2",
                        ),
                        align_items="start",
                        flex="3",
                        spacing="2",
                    ),
                    # Sağ Simüle Satış Fiyatı Kartı
                    rx.card(
                        rx.vstack(
                            rx.text("SİMÜLE SATIŞ FİYATI", font_size="10px", color="#94a3b8", font_weight="bold", letter_spacing="0.5px"),
                            rx.text(DynamicPricingState.simulated_sales_price_str, font_size="22px", font_weight="bold", color="#ffffff"),
                            rx.text(DynamicPricingState.simulated_profit_str, font_size="12px", font_weight="600", color="#4ade80"),
                            align_items="center",
                            justify="center",
                            spacing="1",
                        ),
                        background="#070b14",
                        border="1px solid #1e293b",
                        border_radius="10px",
                        padding="14px 24px",
                        flex="1.8",
                    ),
                    width="100%",
                    spacing="4",
                    align_items="center",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="18px",
                width="100%",
            ),

            # Test Edilen Hedef Kâr Marjı (Slider Alanı)
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text("Test Edilen Hedef Kâr Marjı:", font_size="12.5px", font_weight="600", color="#ffffff"),
                        rx.spacer(),
                        rx.text(
                            "%" + DynamicPricingState.target_margin.to(str),
                            font_size="14px",
                            font_weight="bold",
                            color="#38bdf8",
                            font_family="monospace",
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    rx.slider(
                        value=[DynamicPricingState.target_margin],
                        on_change=DynamicPricingState.set_target_margin,  # <-- on_value_change yerine on_change
                        min=5,
                        max=70,
                        step=0.5,
                        width="100%",
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="16px 20px",
                width="100%",
            ),

            # 4'lü KPI Kartı
            rx.hstack(
                stat_kpi_card("KAZANMA OLASILIĞI", DynamicPricingState.win_probability_str, "#22c55e"),
                stat_kpi_card("OPTİMAL KÂR MARJI", DynamicPricingState.optimal_margin_str, "#38bdf8"),
                stat_kpi_card("MÜŞTERİ TEKLİF GEÇMİŞİ", DynamicPricingState.gecmis_teklif_str, "#ffffff"),
                stat_kpi_card("GEÇMİŞ KAZANMA ORANI", DynamicPricingState.gecmis_kazanma_str, "#facc15"),
                spacing="3",
                width="100%",
            ),

            # Müşteri Satınalma Profili Bilgi Bandı
            rx.card(
                rx.hstack(
                    rx.icon("info", size=18, color="#38bdf8"),
                    rx.vstack(
                        rx.text("Müşteri Satınalma Profili:", font_size="12px", font_weight="bold", color="#ffffff"),
                        rx.text(DynamicPricingState.profil_tavsiye_metni, font_size="12px", color="#cbd5e1"),
                        align_items="start",
                        spacing="0",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                background="#070e22",
                border="1px solid #1e3a8a",
                border_radius="10px",
                padding="14px 18px",
                width="100%",
            ),

            # Kâr Marjı - Kazanma İhtimali ve Beklenen Getiri Eğrisi (Grafik)
            rx.card(
                rx.vstack(
                    rx.text("Kâr Marjı - Kazanma İhtimali ve Beklenen Getiri Eğrisi", font_size="13px", font_weight="600", color="#ffffff"),
                    
                    # Lejant
                    rx.hstack(
                        rx.hstack(
                            rx.box(width="10px", height="10px", background="#38bdf8", border_radius="2px"),
                            rx.text("Kazanma İhtimali (%)", font_size="11.5px", color="#94a3b8"),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.hstack(
                            rx.box(width="10px", height="10px", border="2px dashed #22c55e", border_radius="2px"),
                            rx.text("Beklenen Getiri Endeksi", font_size="11.5px", color="#94a3b8"),
                            spacing="1",
                            align_items="center",
                        ),
                        spacing="4",
                        justify="center",
                        width="100%",
                        padding_bottom="8px",
                    ),

                    # Recharts Alanı
                    rx.recharts.line_chart(
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke="#1e293b"),
                        rx.recharts.x_axis(data_key="marj", stroke="#64748b", font_size="11px"),
                        rx.recharts.y_axis(stroke="#64748b", font_size="11px"),
                        rx.recharts.tooltip(
                            content_style={"background": "#070b14", "border": "1px solid #1e293b", "border-radius": "8px", "color": "#ffffff"}
                        ),
                        rx.recharts.line(
                            data_key="kazanma_ihtimali",
                            stroke="#38bdf8",
                            stroke_width=2.5,
                            dot={"r": 3, "fill": "#38bdf8"},
                            type_="monotone",
                        ),
                        rx.recharts.line(
                            data_key="beklenen_getiri",
                            stroke="#22c55e",
                            stroke_width=2.5,
                            stroke_dasharray="4 4",
                            dot={"r": 3, "fill": "#22c55e"},
                            type_="monotone",
                        ),
                        data=DynamicPricingState.chart_data,
                        width="100%",
                        height=260,
                    ),
                    spacing="2",
                    width="100%",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="18px",
                width="100%",
            ),

            # Alt Aksiyon Butonu
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.icon("check", size=16),
                    "Bu Marjı Teklife Uygula ve Kaydet",
                    color_scheme="blue",
                    size="3",
                    padding_x="24px",
                    border_radius="8px",
                    on_click=DynamicPricingState.marji_teklife_uygula,
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(2, 132, 199, 0.4)"},
                ),
                width="100%",
                padding_top="4px",
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

def dynamic_pricing_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        dynamic_pricing_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=DynamicPricingState.on_load_recompute,
    )