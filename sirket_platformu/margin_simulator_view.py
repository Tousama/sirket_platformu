import reflex as rx
from .margin_simulator_state import MarginSimulatorState
from .quote_builder import sidebar

def sim_result_card(title: str, val_str: str, val_color: str = "#ffffff") -> rx.Component:
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
        padding="16px 12px",
        flex="1",
    )

def margin_simulator_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.text("🎯", font_size="16px"),
                    rx.heading("Marj & İskonto Simülatörü", size="4", color="#ffffff"),
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
                    rx.text("Proaktif Marj, İskonto & Kur Şoku Simülatörü", font_size="15px", font_weight="700", color="#ffffff"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Pazarlık masasında müşteri iskontosunun, olası döviz artışının ve hedef marj kilidinin projeye etkisini canlı simüle edin.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # YENİ: Hazırlanan Teklif Seçim Alanı
            rx.card(
                rx.vstack(
                    rx.text("Simüle Edilecek Teklifi Seçin:", font_size="12px", font_weight="600", color="#ffffff"),
                    rx.select(
                        MarginSimulatorState.teklif_secenekleri,
                        value=MarginSimulatorState.secilen_teklif,
                        on_change=MarginSimulatorState.set_secilen_teklif,
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

            # Üst 3 Kontrol Kartı (İskonto, Kur Şoku, Taban Marj Kilidi)
            rx.grid(
                # Kart 1: Müşteri İskonto Talebi
                rx.card(
                    rx.vstack(
                        rx.text("MÜŞTERİ İSKONTO TALEBİ", font_size="11.5px", font_weight="bold", color="#f59e0b"),
                        rx.text("İskonto Oranı (%):", font_size="11.5px", color="#94a3b8"),
                        rx.slider(
                            value=[MarginSimulatorState.iskonto_orani],
                            on_change=MarginSimulatorState.set_iskonto,
                            min=0,
                            max=30,
                            step=0.5,
                            width="100%",
                            size="2",
                            accent_color="amber",
                        ),
                        rx.hstack(
                            rx.spacer(),
                            rx.text(
                                "%" + MarginSimulatorState.iskonto_orani.to(str),
                                font_size="13px",
                                font_weight="bold",
                                color="#f59e0b",
                            ),
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="18px",
                ),

                # Kart 2: Döviz Kuru Şoku
                rx.card(
                    rx.vstack(
                        rx.text("DÖVİZ KURU ŞOKU", font_size="11.5px", font_weight="bold", color="#f43f5e"),
                        rx.text("EUR/USD Olası Artışı (%):", font_size="11.5px", color="#94a3b8"),
                        rx.slider(
                            value=[MarginSimulatorState.doviz_soku_orani],
                            on_change=MarginSimulatorState.set_doviz_soku,
                            min=0,
                            max=40,
                            step=1,
                            width="100%",
                            size="2",
                            accent_color="ruby",
                        ),
                        rx.hstack(
                            rx.spacer(),
                            rx.text(
                                "%" + MarginSimulatorState.doviz_soku_orani.to(str) + " Artış",
                                font_size="13px",
                                font_weight="bold",
                                color="#f43f5e",
                            ),
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="18px",
                ),

                # Kart 3: Hedef Asgari Marj Kilidi
                rx.card(
                    rx.vstack(
                        rx.text("HEDEF ASGARİ MARJ KİLİDİ", font_size="11.5px", font_weight="bold", color="#38bdf8"),
                        rx.text("İstenen Taban Marj (%):", font_size="11.5px", color="#94a3b8"),
                        rx.input(
                            value=MarginSimulatorState.taban_marj_str,
                            on_change=MarginSimulatorState.set_taban_marj_str,
                            size="2",
                            width="100%",
                            background="#070b14",
                            border="1px solid #1e293b",
                            color="#ffffff",
                        ),
                        rx.text(
                            "Bu marjın altına düşmeyecek en dip satış fiyatı otomatik hesaplanır.",
                            font_size="10.5px",
                            color="#64748b",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="18px",
                ),
                columns="3",
                spacing="3",
                width="100%",
            ),

            # Alt Panel: SİMÜLASYON SONUCU & KARAR MATRİSİ
            rx.card(
                rx.vstack(
                    rx.text("SİMÜLASYON SONUCU & KARAR MATRİSİ", font_size="12px", font_weight="bold", color="#38bdf8", letter_spacing="0.5px"),
                    
                    # 4 Sonuç Kartı
                    rx.hstack(
                        sim_result_card("SİMÜLE MALİYET", MarginSimulatorState.simule_maliyet_str, "#ffffff"),
                        sim_result_card("İSKONTOLU SATIŞ", MarginSimulatorState.iskontolu_satis_str, "#38bdf8"),
                        sim_result_card("SİMÜLE NET KÂR", MarginSimulatorState.simule_net_kar_str, "#22c55e"),
                        sim_result_card("YENİ KÂR MARJI", MarginSimulatorState.yeni_kar_marji_str, "#4ade80"),
                        spacing="3",
                        width="100%",
                    ),

                    # Güvenli Bölge / Risk Uyarı Paneli
                    rx.card(
                        rx.hstack(
                            rx.icon(
                                rx.cond(MarginSimulatorState.is_guvenli_bolge, "check-check", "triangle-alert"),
                                size=18,
                                color=rx.cond(MarginSimulatorState.is_guvenli_bolge, "#22c55e", "#ef4444"),
                            ),
                            rx.text(
                                rx.text.span(
                                    rx.cond(MarginSimulatorState.is_guvenli_bolge, "Güvenli Bölge: ", "Riskli Bölge: "),
                                    font_weight="bold",
                                    color="#ffffff"
                                ),
                                rx.text.span(MarginSimulatorState.durum_mesaji, color="#cbd5e1"),
                                font_size="12.5px",
                                line_height="1.5",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        background=rx.cond(MarginSimulatorState.is_guvenli_bolge, "#062218", "#2a0808"),
                        border=rx.cond(MarginSimulatorState.is_guvenli_bolge, "1px solid #166534", "1px solid #991b1b"),
                        border_radius="8px",
                        padding="12px 18px",
                        width="100%",
                    ),

                    # Alt Satır: En Dip Son Fiyat & Simüle Satış Fiyatını Teklife Kaydet Butonu
                    rx.hstack(
                        rx.text(
                            "Pazarlıkta verilebilecek en dip son fiyat: ",
                            font_size="13px",
                            color="#94a3b8",
                        ),
                        rx.text(
                            MarginSimulatorState.en_dip_fiyat_str,
                            font_size="13.5px",
                            font_weight="bold",
                            color="#ffffff",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Simüle Satış Fiyatını Teklife Kaydet",
                            color_scheme="blue",
                            size="3",
                            padding_x="22px",
                            border_radius="8px",
                            on_click=MarginSimulatorState.teklife_kaydet,
                            _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 12px rgba(2, 132, 199, 0.4)"},
                        ),
                        width="100%",
                        align_items="center",
                        padding_top="6px",
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
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#060913",
    )

def margin_simulator_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        margin_simulator_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=MarginSimulatorState.on_load_sync_quotes,
    )