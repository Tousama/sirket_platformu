import reflex as rx
from .labor_engine_state import LaborEngineState
from .quote_builder import sidebar
from typing import Any

def section_title(num_str: str, text_str: str) -> rx.Component:
    return rx.text(
        rx.text.span(num_str, font_weight="bold", color="#38bdf8"),
        rx.text.span(text_str, font_weight="600", color="#38bdf8"),
        font_size="11.5px",
        letter_spacing="0.5px",
    )

def input_field(label: str, value: Any, on_change: Any) -> rx.Component:
    return rx.vstack(
        rx.text(label, font_size="11px", color="#94a3b8"),
        rx.input(
            value=value.to(str),
            on_change=on_change,
            width="100%",
            size="2",
            background="#070b14",
            border="1px solid #1e293b",
        ),
        align_items="start",
        width="100%",
        spacing="1",
    )

def summary_kpi(label: str, val_str: str, unit: str, color_val: str) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(label, font_size="10.5px", color="#94a3b8", font_weight="600"),
            rx.hstack(
                rx.text(val_str, font_size="20px", font_weight="bold", color=color_val),
                rx.text(unit, font_size="12px", color=color_val, margin_top="6px"),
                spacing="2",
                align_items="baseline",
            ),
            align_items="center",
            justify="center",
            spacing="0",
        ),
        background="#070b14",
        border="1px solid #1e293b",
        border_radius="10px",
        padding="12px",
        flex="1",
    )

def labor_engine_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar
            rx.hstack(
                rx.hstack(
                    rx.icon("zap", size=18, color="#f59e0b"),
                    rx.heading("Saha İşçilik & Montaj Motoru (A/S)", size="4", color="#ffffff"),
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
                    rx.text("Saha İşçilik & Montaj Maliyet Motoru (Adam/Saat - A/S)", font_size="15px", font_weight="700", color="#ffffff"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Kablo metrajı, tava, Ex-proof gland ve enstrüman montaj parametreleriyle adam/saat (A/S) ve konaklama maliyetlerini hesaplayıp doğrudan teklif BOM'una aktarın.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="4px",
            ),

            # Üst Seçici Kartı (Teklif & Norm Tabanı)
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text("İşçilik Kalemi Eklenecek Teklif:", font_size="11.5px", color="#94a3b8"),
                        rx.spacer(),
                        rx.hstack(
                            rx.text("Norm Tabanı:", font_size="11.5px", color="#64748b"),
                            rx.text("PetroTek Saha A/S v2.4", font_size="11.5px", font_weight="bold", color="#38bdf8"),
                            spacing="1",
                        ),
                        width="100%",
                    ),
                    rx.select(
                        LaborEngineState.referans_secenekleri,
                        value=LaborEngineState.secilen_teklif,
                        on_change=LaborEngineState.set_secilen_teklif,
                        width="100%",
                        size="2",
                    ),
                    width="100%",
                    spacing="2",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="14px 18px",
                width="100%",
            ),

            # Girdi Alanları (Metraj & Ekip)
            rx.grid(
                # 1. METRAJ & EKİPMAN SAYILARI
                rx.card(
                    rx.vstack(
                        section_title("1. ", "METRAJ & EKİPMAN SAYILARI"),
                        rx.grid(
                            input_field("Kablo Kanalı / Tava (m):", LaborEngineState.kablo_tava_m, LaborEngineState.set_kablo_tava_m),
                            input_field("Kablo Çekimi (m):", LaborEngineState.kablo_cekim_m, LaborEngineState.set_kablo_cekim_m),
                            input_field("Ex-Gland & Uç Bağlantı (ad):", LaborEngineState.gland_baglanti_ad, LaborEngineState.set_gland_baglanti_ad),
                            input_field("Enstrüman & Loop Test (ad):", LaborEngineState.enstruman_test_ad, LaborEngineState.set_enstruman_test_ad),
                            input_field("Saha Panosu (ad):", LaborEngineState.saha_panosu_ad, LaborEngineState.set_saha_panosu_ad),
                            input_field("İlave / Demontaj (A/S):", LaborEngineState.ilave_demontaj_as, LaborEngineState.set_ilave_demontaj_as),
                            columns="2",
                            spacing="3",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="16px",
                ),

                # 2. EKİP & MOBİLİZASYON
                rx.card(
                    rx.vstack(
                        section_title("2. ", "EKİP & MOBİLİZASYON"),
                        rx.grid(
                            input_field("Teknisyen Sayısı:", LaborEngineState.teknisyen_sayisi, LaborEngineState.set_teknisyen_sayisi),
                            input_field("Süpervizör Müh. (Gün):", LaborEngineState.supervizor_gun, LaborEngineState.set_supervizor_gun),
                            input_field("Kişi Başı Harcırah (₺/gün):", LaborEngineState.harcirah_gun_tl, LaborEngineState.set_harcirah_gun_tl),
                            input_field("Otel / Geceleme (₺/oda):", LaborEngineState.otel_gece_tl, LaborEngineState.set_otel_gece_tl),
                            columns="2",
                            spacing="3",
                            width="100%",
                        ),
                        input_field("Ulaşım, Yakıt & Araç Bedeli (₺):", LaborEngineState.ulasim_arac_tl, LaborEngineState.set_ulasim_arac_tl),
                        spacing="3",
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

            # 3. HESAPLANAN SAHA İŞÇİLİK & MALİYET ÖZETİ
            rx.card(
                rx.vstack(
                    section_title("3. ", "HESAPLANAN SAHA İŞÇİLİK & MALİYET ÖZETİ"),

                    # 4 Özet KPI Kutusu
                    rx.hstack(
                        summary_kpi("TEKNİSYEN A/S", LaborEngineState.teknisyen_as.to(str), "A/S", "#ffffff"),
                        summary_kpi("MÜHENDİS A/S", LaborEngineState.muhendis_as.to(str), "A/S", "#38bdf8"),
                        summary_kpi("TAHMİNİ SAHA SÜRESİ", LaborEngineState.tahmini_saha_suresi_gun.to(str), "Gün", "#f59e0b"),
                        summary_kpi("İŞÇİLİK KÂR MARJI", "%" + LaborEngineState.kar_marji_yuzde.to(str), "", "#22c55e"),
                        spacing="3",
                        width="100%",
                    ),

                    # Maliyet / Satış Tablosu
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("KALEM AÇIKLAMASI"),
                                rx.table.column_header_cell("MİKTAR", text_align="center"),
                                rx.table.column_header_cell("MALİYET (₺)", text_align="right"),
                                rx.table.column_header_cell("SATIŞ (₺)", text_align="right"),
                            )
                        ),
                        rx.table.body(
                            rx.table.row(
                                rx.table.cell(rx.text("Teknisyen Saha Montaj & Kablaj (450 ₺/s)", font_size="12px", color="#cbd5e1")),
                                rx.table.cell(rx.text(LaborEngineState.teknisyen_as.to(str) + " A/S", font_size="12px", color="#94a3b8"), text_align="center"),
                                rx.table.cell(rx.text(LaborEngineState.cost_teknisyen_str + " ₺", font_size="12px", color="#cbd5e1"), text_align="right"),
                                rx.table.cell(rx.text(LaborEngineState.price_teknisyen_str + " ₺", font_size="12px", font_weight="600", color="#ffffff"), text_align="right"),
                            ),
                            rx.table.row(
                                rx.table.cell(rx.text("Süpervizörlük, Kalibrasyon & Loop Test (750 ₺/s)", font_size="12px", color="#cbd5e1")),
                                rx.table.cell(rx.text(LaborEngineState.muhendis_as.to(str) + " A/S", font_size="12px", color="#94a3b8"), text_align="center"),
                                rx.table.cell(rx.text(LaborEngineState.cost_muhendis_str + " ₺", font_size="12px", color="#cbd5e1"), text_align="right"),
                                rx.table.cell(rx.text(LaborEngineState.price_muhendis_str + " ₺", font_size="12px", font_weight="600", color="#ffffff"), text_align="right"),
                            ),
                            rx.table.row(
                                rx.table.cell(rx.text("Mobilizasyon, Konaklama & Ulaşım", font_size="12px", color="#cbd5e1")),
                                rx.table.cell(rx.text(LaborEngineState.tahmini_saha_suresi_gun.to(str) + " Gün", font_size="12px", color="#94a3b8"), text_align="center"),
                                rx.table.cell(rx.text(LaborEngineState.cost_mobilizasyon_str + " ₺", font_size="12px", color="#cbd5e1"), text_align="right"),
                                rx.table.cell(rx.text(LaborEngineState.price_mobilizasyon_str + " ₺", font_size="12px", font_weight="600", color="#ffffff"), text_align="right"),
                            ),
                            # GENEL TOPLAM
                            rx.table.row(
                                rx.table.cell(rx.text("GENEL TOPLAM İŞÇİLİK & OPERASYON", font_size="12px", font_weight="bold", color="#38bdf8")),
                                rx.table.cell(rx.text("-", font_size="12px", color="#94a3b8"), text_align="center"),
                                rx.table.cell(rx.text(LaborEngineState.cost_total_str + " ₺", font_size="12.5px", font_weight="bold", color="#38bdf8"), text_align="right"),
                                rx.table.cell(rx.text(LaborEngineState.price_total_str + " ₺", font_size="12.5px", font_weight="bold", color="#22c55e"), text_align="right"),
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
                padding="16px",
                width="100%",
            ),
            
            # 4 Özet KPI Kutusu (Kâr Marjı Elle Düzenlenebilir)
                    rx.hstack(
                        summary_kpi("TEKNİSYEN A/S", LaborEngineState.teknisyen_as.to(str), "A/S", "#ffffff"),
                        summary_kpi("MÜHENDİS A/S", LaborEngineState.muhendis_as.to(str), "A/S", "#38bdf8"),
                        summary_kpi("TAHMİNİ SAHA SÜRESİ", LaborEngineState.tahmini_saha_suresi_gun.to(str), "Gün", "#f59e0b"),
                        # DÜZENLENEBİLİR KÂR MARJI KARTI
                        rx.card(
                            rx.vstack(
                                rx.hstack(
                                    rx.text("İŞÇİLİK KÂR MARJI", font_size="10.5px", color="#94a3b8", font_weight="600"),
                                    rx.badge("Düzenlenebilir", color_scheme="green", variant="surface", size="1"),
                                    spacing="1",
                                    align_items="center",
                                ),
                                rx.hstack(
                                    rx.text("%", font_size="18px", font_weight="bold", color="#22c55e"),
                                    rx.input(
                                        value=LaborEngineState.custom_margin_percent.to(str),
                                        on_change=LaborEngineState.set_custom_margin_percent,
                                        width="75px",
                                        size="2",
                                        font_size="16px",
                                        font_weight="bold",
                                        text_align="center",
                                        color="#22c55e",
                                        background="#030712",
                                        border="1px solid #15803d",
                                        border_radius="6px",
                                    ),
                                    spacing="1",
                                    align_items="center",
                                    justify="center",
                                ),
                                align_items="center",
                                justify="center",
                                spacing="1",
                            ),
                            background="#070b14",
                            border="1.5px solid rgba(34, 197, 94, 0.4)",
                            border_radius="10px",
                            padding="10px",
                            flex="1",
                        ),
                        spacing="3",
                        width="100%",
                    ),

            # Alt Aksiyon Barı (Hizmet Adı + BOM'a Ekle Butonu)
            rx.hstack(
                rx.input(
                    value=LaborEngineState.hizmet_aciklamasi,
                    on_change=LaborEngineState.set_hizmet_aciklamasi,
                    size="3",
                    flex="1",
                    background="#070b14",
                    border="1px solid #1e293b",
                    font_size="12.5px",
                ),
                rx.button(
                    rx.icon("arrow-right-circle", size=17),
                    "Hesaplanan İşi Teklif BOM'una Ekle",
                    color_scheme="green",
                    size="3",
                    padding_x="22px",
                    border_radius="8px",
                    on_click=LaborEngineState.aktar_bom,
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 10px rgba(34, 197, 94, 0.3)"},
                ),
                spacing="3",
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

def labor_engine_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        labor_engine_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )