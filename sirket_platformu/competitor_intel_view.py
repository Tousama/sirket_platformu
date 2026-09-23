import reflex as rx
from .competitor_intel_state import CompetitorIntelState
from .quote_builder import sidebar

def kpi_card(title: str, main_val: str, sub_val: str, main_color: str = "#ffffff", sub_color: str = "#94a3b8") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(title, font_size="11px", color="#94a3b8", font_weight="600", text_align="center"),
            rx.text(main_val, font_size="21px", font_weight="bold", color=main_color, text_align="center"),
            rx.text(sub_val, font_size="11.5px", color=sub_color, font_weight="500", text_align="center"),
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

def tab_button(text: str, tab_id: str) -> rx.Component:
    is_active = CompetitorIntelState.active_tab == tab_id
    return rx.box(
        rx.text(
            text,
            font_size="13px",
            font_weight=rx.cond(is_active, "600", "500"),
            color=rx.cond(is_active, "#38bdf8", "#94a3b8"),
            cursor="pointer",
        ),
        padding_y="8px",
        padding_x="16px",
        border_bottom=rx.cond(is_active, "2px solid #38bdf8", "2px solid transparent"),
        on_click=lambda: CompetitorIntelState.set_active_tab(tab_id),
        _hover={"color": "#ffffff"},
        transition="all 0.2s ease",
    )

def competitor_intel_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("🎯", font_size="16px"),
                    rx.heading("Rakip Fiyat Tahmini & İstihbarat", size="4", color="#ffffff"),
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
                    rx.text("Rakip Fiyat Tahmini & İstihbarat (Competitor Intelligence)", font_size="15px", font_weight="700", color="#ffffff"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Rakiplerin geçmiş ihalelerdeki fiyatlama davranışlarını modelleyin; ihaleyi kazanacak optimal fiyatı (Sweet Spot) tespit edin.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # Sekmeler (Tabs Bar)
            rx.hstack(
                tab_button("Optimal Teklif Önerisi (Tahmin)", "tahmin"),
                tab_button("Sonuçlanan İhale / Rakip Fiyatı Kaydet", "kaydet"),
                tab_button("Rakip Kâr Marjı Profilleri", "profiller"),
                width="100%",
                border_bottom="1px solid #1e293b",
                spacing="2",
            ),

            # SEKME 1: Optimal Teklif Önerisi (Görseldeki Birebir Arayüz)
            rx.cond(
                CompetitorIntelState.active_tab == "tahmin",
                rx.vstack(
                    # Seçim Alanı ve Simüle Et Butonu
                    rx.card(
                        rx.hstack(
                            rx.vstack(
                                rx.text("Fiyatlanacak Teklif:", font_size="11.5px", color="#94a3b8"),
                                rx.select(
                                    CompetitorIntelState.teklif_secenekleri,
                                    value=CompetitorIntelState.secilen_teklif,
                                    on_change=CompetitorIntelState.set_secilen_teklif,
                                    width="100%",
                                    size="2",
                                ),
                                align_items="start",
                                flex="3",
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Muhtemel Rakip Firma:", font_size="11.5px", color="#94a3b8"),
                                rx.select(
                                    CompetitorIntelState.rakip_secenekleri,
                                    value=CompetitorIntelState.secilen_rakip,
                                    on_change=CompetitorIntelState.set_secilen_rakip,
                                    width="100%",
                                    size="2",
                                ),
                                align_items="start",
                                flex="2",
                                spacing="1",
                            ),
                            rx.button(
                                "Simüle Et",
                                color_scheme="blue",
                                size="3",
                                padding_x="28px",
                                border_radius="8px",
                                on_click=CompetitorIntelState.simule_et,
                                margin_top="18px",
                                _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(2, 132, 199, 0.4)"},
                            ),
                            width="100%",
                            spacing="3",
                            align_items="center",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="18px",
                        width="100%",
                    ),

                    # SİMÜLASYON & İHALE KAZANMA TAHMİNİ KARTI
                    rx.card(
                        rx.vstack(
                            rx.text("SİMÜLASYON & İHALE KAZANMA TAHMİNİ", font_size="12px", font_weight="bold", color="#38bdf8", letter_spacing="0.5px"),
                            
                            # 4'lü KPI Kutusu
                            rx.hstack(
                                kpi_card("BİZİM MALİYETİMİZ", CompetitorIntelState.bizim_maliyet_str, "", "#ffffff", "#94a3b8"),
                                kpi_card("TAHMİNİ RAKİP FİYATI", CompetitorIntelState.tahmini_rakip_fiyati_str, CompetitorIntelState.rakip_marj_str, "#facc15", "#facc15"),
                                kpi_card("ÖNERİLEN FİYAT (SWEET SPOT)", CompetitorIntelState.onerilen_fiyat_str, CompetitorIntelState.onerilen_marj_str, "#38bdf8", "#38bdf8"),
                                kpi_card("VERİ GÜVENİLİRLİĞİ", CompetitorIntelState.veri_guvenilirligi, CompetitorIntelState.gecmis_ihale_sayisi_str, "#22c55e", "#94a3b8"),
                                spacing="3",
                                width="100%",
                            ),

                            # Alt Tavsiye Kutusu
                            rx.card(
                                rx.hstack(
                                    rx.text("💡", font_size="16px"),
                                    rx.text(
                                        rx.text.span("Tavsiye: ", font_weight="bold", color="#ffffff"),
                                        rx.text.span(CompetitorIntelState.tavsiye_metni, color="#cbd5e1"),
                                        font_size="12.5px",
                                        line_height="1.5",
                                    ),
                                    spacing="2",
                                    align_items="start",
                                ),
                                background="#070e22",
                                border="1px solid #1e3a8a",
                                border_radius="8px",
                                padding="14px 18px",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        background="#0a0f1d",
                        border="1px solid #1e293b",
                        border_radius="12px",
                        padding="20px",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),

            # SEKME 2: Sonuçlanan İhale / Rakip Fiyatı Kaydet
            rx.cond(
                CompetitorIntelState.active_tab == "kaydet",
                rx.card(
                    rx.vstack(
                        rx.text("GEÇMİŞ İHALE & İSTİHBARAT VERİ GİRİŞİ", font_size="12px", font_weight="bold", color="#38bdf8"),
                        rx.text("Rakip firmaların teklif ettiği nihai fiyatları sisteme girerek makine öğrenmesi ve Sweet Spot algoritmasını eğitin.", font_size="12px", color="#94a3b8"),
                        rx.grid(
                            rx.vstack(
                                rx.text("İhale / Müşteri Adı:", font_size="11.5px", color="#94a3b8"),
                                rx.input(placeholder="Örn: Tüpraş Kırıkkale Tank Sahası", on_change=CompetitorIntelState.set_yeni_ihale_musteri, width="100%"),
                                align_items="start", width="100%", spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Rakip Firma:", font_size="11.5px", color="#94a3b8"),
                                rx.select(CompetitorIntelState.rakip_secenekleri, value=CompetitorIntelState.yeni_ihale_rakip, on_change=CompetitorIntelState.set_yeni_ihale_rakip, width="100%"),
                                align_items="start", width="100%", spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Rakibin Teklif Fiyatı (₺):", font_size="11.5px", color="#94a3b8"),
                                rx.input(placeholder="Örn: 310000", on_change=CompetitorIntelState.set_yeni_ihale_rakip_fiyat, width="100%"),
                                align_items="start", width="100%", spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Bizim Tahmini Maliyetimiz (₺):", font_size="11.5px", color="#94a3b8"),
                                rx.input(placeholder="Örn: 220000", on_change=CompetitorIntelState.set_yeni_ihale_bizim_maliyet, width="100%"),
                                align_items="start", width="100%", spacing="1",
                            ),
                            columns="2",
                            spacing="3",
                            width="100%",
                        ),
                        rx.button(
                            rx.icon("database", size=15),
                            "İstihbarat Havuzuna Kaydet",
                            color_scheme="green",
                            size="2",
                            border_radius="8px",
                            on_click=CompetitorIntelState.ihale_kaydet,
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="20px",
                    width="100%",
                ),
            ),

            # SEKME 3: Rakip Kâr Marjı Profilleri
            rx.cond(
                CompetitorIntelState.active_tab == "profiller",
                rx.card(
                    rx.vstack(
                        rx.text("KAYITLI RAKİP FİRMALAR & FİYATLAMA DAVRANIŞLARI", font_size="12px", font_weight="bold", color="#38bdf8"),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("RAKİP FİRMA"),
                                    rx.table.column_header_cell("ORT. BRÜT MARJ"),
                                    rx.table.column_header_cell("GEÇMİŞ İHALE"),
                                    rx.table.column_header_cell("VERİ GÜVENİLİRLİĞİ"),
                                    rx.table.column_header_cell("FİYATLAMA STRATEJİSİ"),
                                )
                            ),
                            rx.table.body(
                                rx.table.row(
                                    rx.table.cell(rx.text("Atlas Otomasyon", font_weight="600", color="#ffffff")),
                                    rx.table.cell(rx.badge("%33.3", color_scheme="amber", variant="surface")),
                                    rx.table.cell("3 İhale"),
                                    rx.table.cell(rx.badge("Yüksek", color_scheme="green", variant="surface")),
                                    rx.table.cell("Standart Kâr Odaklı"),
                                ),
                                rx.table.row(
                                    rx.table.cell(rx.text("Delta Vana & Enstrümantasyon", font_weight="600", color="#ffffff")),
                                    rx.table.cell(rx.badge("%28.5", color_scheme="red", variant="surface")),
                                    rx.table.cell("5 İhale"),
                                    rx.table.cell(rx.badge("Çok Yüksek", color_scheme="green", variant="surface")),
                                    rx.table.cell("Agresif / Kırıcı Fiyat"),
                                ),
                                rx.table.row(
                                    rx.table.cell(rx.text("Proses Mühendislik A.Ş.", font_weight="600", color="#ffffff")),
                                    rx.table.cell(rx.badge("%38.0", color_scheme="purple", variant="surface")),
                                    rx.table.cell("2 İhale"),
                                    rx.table.cell(rx.badge("Orta", color_scheme="amber", variant="surface")),
                                    rx.table.cell("Yüksek Fiyat / Kalite Odaklı"),
                                ),
                            ),
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="20px",
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

def competitor_intel_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        competitor_intel_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )