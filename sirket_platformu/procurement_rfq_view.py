import reflex as rx
from .procurement_rfq_state import ProcurementRfqState
from .quote_builder import sidebar


def procurement_rfq_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Üst Bar (Breadcrumb & Aksiyonlar)
            rx.hstack(
                rx.hstack(
                    rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                    rx.text("📦", font_size="16px"),
                    rx.heading("Satınalma & RFQ İhracı", size="4", color="#ffffff", font_weight="700"),
                    rx.text("/", color="#475569"),
                    rx.text("PetroTek Engineering", color="#94a3b8", font_size="13px"),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    # Döviz Seçim Butonları
                    rx.segmented_control.root(
                        rx.segmented_control.item("TRY (₺)", value="TRY (₺)"),
                        rx.segmented_control.item("USD ($)", value="USD ($)"),
                        rx.segmented_control.item("EUR (€)", value="EUR (€)"),
                        value=ProcurementRfqState.currency,
                        on_change=ProcurementRfqState.set_currency,
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

            # Modül Başlığı ve Açıklaması
            rx.vstack(
                rx.hstack(
                    rx.text("📦", font_size="18px"),
                    rx.text(
                        "Satınalma & Tedarikçi RFQ İhracı",
                        font_size="16px",
                        font_weight="800",
                        color="#ffffff",
                        letter_spacing="-0.01em",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Teklif kalemlerini tedarikçilere fiyat sormaya hazır standart sarı dolgulu Excel formatında indirin veya otomatik e-posta gönderin.",
                    font_size="12.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="1",
                padding_y="6px",
            ),

            # Üst Seçim Kartı: İşlem Yapılacak Teklif & İhracat Formatı
            rx.card(
                rx.grid(
                    rx.vstack(
                        rx.text("İşlem Yapılacak Teklif:", font_size="11.5px", color="#94a3b8", font_weight="600"),
                        rx.select(
                            ProcurementRfqState.teklif_secenekleri,
                            value=ProcurementRfqState.secilen_teklif,
                            on_change=ProcurementRfqState.set_secilen_teklif,
                            width="100%",
                            size="2",
                        ),
                        align_items="start",
                        width="100%",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("İhracat Formatı:", font_size="11.5px", color="#94a3b8", font_weight="600"),
                        rx.select(
                            ProcurementRfqState.ihracat_formatlari,
                            value=ProcurementRfqState.secilen_format,
                            on_change=ProcurementRfqState.set_secilen_format,
                            width="100%",
                            size="2",
                        ),
                        align_items="start",
                        width="100%",
                        spacing="1",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                border_radius="12px",
                padding="18px 22px",
                width="100%",
            ),

            # Alt Simülatör Kartı: TEDARİKÇİYE E-POSTA GÖNDERİM SİMÜLATÖRÜ
            rx.card(
                rx.vstack(
                    rx.text(
                        "TEDARİKÇİYE E-POSTA GÖNDERİM SİMÜLATÖRÜ",
                        font_size="11.5px",
                        font_weight="800",
                        color="#38bdf8",
                        letter_spacing="0.05em",
                    ),
                    rx.grid(
                        rx.vstack(
                            rx.text("Tedarikçi E-Posta Adresleri:", font_size="11.5px", color="#94a3b8"),
                            rx.input(
                                value=ProcurementRfqState.tedarikci_epostalar,
                                on_change=ProcurementRfqState.set_tedarikci_epostalar,
                                width="100%",
                                size="2",
                                background="#030712",
                                border="1px solid #1e293b",
                                color="#ffffff",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Son Yanıt Tarihi:", font_size="11.5px", color="#94a3b8"),
                            rx.input(
                                value=ProcurementRfqState.son_yanit_tarihi,
                                on_change=ProcurementRfqState.set_son_yanit_tarihi,
                                width="100%",
                                size="2",
                                background="#030712",
                                border="1px solid #1e293b",
                                color="#ffffff",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),

                    # E-Posta Gövde Önizleme Alanı
                    rx.box(
                        rx.vstack(
                            rx.text("Sayın Yetkili,", font_size="12px", font_weight="700", color="#38bdf8"),
                            rx.text(
                                "Aşağıda detayları belirtilen projemiz kapsamında ihtiyaç duyulan enstrüman ve malzemeler için birim fiyat ve teslimat süresi teklifinizi rica ederiz. Ekteki sarı dolgulu alanları doldurarak yanıtlamanızı rica ederiz.",
                                font_size="12px",
                                color="#cbd5e1",
                                line_height="1.5",
                            ),
                            rx.text(
                                "Ek: " + ProcurementRfqState.ek_dosya_adi,
                                font_size="12px",
                                font_weight="600",
                                color="#94a3b8",
                                font_family="monospace",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        background="#050a16",
                        border="1px solid #131d33",
                        border_radius="8px",
                        padding="16px",
                        width="100%",
                        margin_top="6px",
                    ),

                    # Alt Aksiyon Butonları
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            "RFQ Excel'i İndir",
                            background="#1e293b",
                            color="#ffffff",
                            font_size="12.5px",
                            font_weight="600",
                            border_radius="8px",
                            padding_x="20px",
                            padding_y="16px",
                            on_click=ProcurementRfqState.export_rfq_excel,
                            _hover={"background": "#334155", "transform": "translateY(-1px)"},
                        ),
                        rx.button(
                            "Tedarikçilere İlet (SMTP)",
                            background="#0284c7",
                            color="#ffffff",
                            font_size="12.5px",
                            font_weight="600",
                            border_radius="8px",
                            padding_x="22px",
                            padding_y="16px",
                            on_click=ProcurementRfqState.send_supplier_email,
                            _hover={"background": "#0369a1", "transform": "translateY(-1px)"},
                        ),
                        spacing="3",
                        width="100%",
                        align_items="center",
                        padding_top="10px",
                    ),
                    spacing="3",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                border_radius="12px",
                padding="20px 22px",
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


def procurement_rfq_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        procurement_rfq_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=ProcurementRfqState.on_load,
    )