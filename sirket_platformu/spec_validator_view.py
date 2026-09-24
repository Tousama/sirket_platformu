import reflex as rx
from .spec_validator_state import SpecValidatorState
from .quote_builder import sidebar


def spec_status_badge(uygunluk: str) -> rx.Component:
    return rx.match(
        uygunluk,
        (
            "Uygun",
            rx.badge(
                "Uygun",
                color_scheme="green",
                variant="solid",
                radius="full",
                size="1",
                font_weight="700",
                padding_x="12px",
                padding_y="3px",
            ),
        ),
        (
            "İnceleme Gerekli",
            rx.badge(
                "İnceleme Gerekli",
                color_scheme="amber",
                variant="solid",
                radius="full",
                size="1",
                font_weight="700",
                padding_x="10px",
                padding_y="3px",
            ),
        ),
        rx.badge(uygunluk, radius="full", size="1"),
    )


def datasheet_library_card() -> rx.Component:
    """Kullanıcının datasheet yükleyebileceği ve kayıtlı föyleri görebileceği kart tasarımı"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("layers", size=16, color="#38bdf8"),
                    rx.text("KAYITLI FABRİKA DATASHEET HAVUZU", font_size="12px", font_weight="800", color="#ffffff"),
                    rx.badge(
                        SpecValidatorState.datasheet_sayisi.to(str) + " Föy Kayıtlı",
                        color_scheme="cyan",
                        variant="surface",
                        size="1",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    # Havuzu Temizle Butonu
                    rx.button(
                        rx.icon("trash", size=13),
                        "Havuzu Temizle",
                        variant="ghost",
                        color_scheme="ruby",
                        size="1",
                        on_click=SpecValidatorState.clear_all_datasheets,
                    ),
                    # Datasheet PDF Yükleme Butonu
                    rx.upload(
                        rx.hstack(
                            rx.icon("upload", size=14, color="#34d399"),
                            rx.text(
                                rx.cond(
                                    SpecValidatorState.son_yuklenen_datasheet != "",
                                    SpecValidatorState.son_yuklenen_datasheet,
                                    "+ Datasheet PDF Yükle",
                                ),
                                font_size="11.5px",
                                font_weight="700",
                                color="#34d399",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        id="datasheet_pdf_upload",
                        border="1px dashed #34d399",
                        padding="5px 14px",
                        border_radius="7px",
                        background="rgba(52, 211, 153, 0.08)",
                        cursor="pointer",
                        on_drop=SpecValidatorState.handle_datasheet_upload(rx.upload_files(upload_id="datasheet_pdf_upload")),
                    ),
                    spacing="2",
                    align_items="center",
                ),
                width="100%",
                align_items="center",
                padding_bottom="10px",
                border_bottom="1px solid #151e33",
            ),
            
            # Kayıtlı Datasheetler Tablosu
            rx.cond(
                SpecValidatorState.datasheet_sayisi > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("MODEL / CİHAZ", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("REFERANS PDF", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("KORUMA (IP)", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("EX-PROOF", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("SİNYAL / ÇIKIŞ", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("BAĞLANTI", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("İŞLEM", font_size="11px", color="#94a3b8", width="60px"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            SpecValidatorState.datasheet_listesi,
                            lambda ds: rx.table.row(
                                rx.table.cell(rx.text(ds["model"].to(str), font_size="12px", font_weight="700", color="#ffffff")),
                                rx.table.cell(
                                    rx.hstack(
                                        rx.icon("file-text", size=13, color="#38bdf8"),
                                        rx.text(ds["dosya"].to(str), font_size="11.5px", color="#94a3b8"),
                                        spacing="1",
                                        align_items="center",
                                    )
                                ),
                                rx.table.cell(rx.badge(ds["ip"].to(str), color_scheme="green", variant="surface", size="1")),
                                rx.table.cell(rx.text(ds["ex"].to(str), font_size="11.5px", color="#cbd5e1")),
                                rx.table.cell(rx.text(ds["sinyal"].to(str), font_size="11.5px", color="#cbd5e1")),
                                rx.table.cell(rx.text(ds["baglanti"].to(str), font_size="11.5px", color="#cbd5e1")),
                                rx.table.cell(
                                    rx.icon_button(
                                        rx.icon("trash-2", size=13, color="#f87171"),
                                        variant="ghost",
                                        color_scheme="ruby",
                                        size="1",
                                        on_click=SpecValidatorState.delete_datasheet(ds["dosya"].to(str)),
                                    )
                                ),
                                align="center",
                                border_bottom="1px solid #151e33",
                                padding_y="8px",
                            )
                        )
                    ),
                    width="100%",
                ),
                rx.text(
                    "Henüz bir fabrika datasheet'i yüklenmedi. Yukarıdaki butondan cihaza ait PDF dosyasını yükleyebilirsiniz.",
                    font_size="12px",
                    color="#64748b",
                    padding_y="12px",
                )
            ),
            spacing="2",
            width="100%",
        ),
        background="#0a1020",
        border="1px solid #151e33",
        border_radius="14px",
        padding="18px 22px",
        width="100%",
    )


def spec_validator_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            # 1. Üst Header Barı
            rx.hstack(
                rx.hstack(
                    rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                    rx.icon("file-text", size=16, color="#cbd5e1"),
                    rx.heading(
                        "Teknik Şartname & Datasheet Doğrulayıcı",
                        size="4",
                        color="#ffffff",
                        font_weight="700",
                    ),
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
                        value=SpecValidatorState.currency,
                        on_change=SpecValidatorState.set_currency,
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

            # 2. Modül Başlığı ve Teklif Seçici
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.icon("file-text", size=18, color="#ffffff"),
                        rx.text(
                            "Tek Tıkla Şartname & Teknik Föy Uygunluk Doğrulayıcı",
                            font_size="16px",
                            font_weight="800",
                            color="#ffffff",
                            letter_spacing="-0.01em",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "Müşteri teknik şartnamesini teklif BOM açıklamalarıyla tarayıp Teknik Uygunluk & Sapma Tablosu (Compliance Matrix) üretin.",
                        font_size="12.5px",
                        color="#94a3b8",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.text("Aktif Teklif / BOM:", font_size="12px", color="#94a3b8", font_weight="600"),
                    rx.select(
                        SpecValidatorState.teklif_secenekleri,
                        value=SpecValidatorState.secilen_teklif,
                        on_change=SpecValidatorState.set_secilen_teklif,
                        size="2",
                        radius="medium",
                        color_scheme="blue",
                        width="240px",
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
                padding_y="4px",
            ),

            # 3. Şartname Giriş Kartı
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "ŞARTNAME METNİ / MADDELERİ",
                            font_size="11px",
                            font_weight="800",
                            color="#38bdf8",
                            letter_spacing="0.04em",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.button(
                                rx.icon("sparkles", size=13),
                                "Metni Düzenle",
                                variant="ghost",
                                color_scheme="cyan",
                                size="1",
                                on_click=SpecValidatorState.format_current_text,
                            ),
                            rx.upload(
                                rx.hstack(
                                    rx.icon("upload-cloud", size=14, color="#38bdf8"),
                                    rx.text(
                                        rx.cond(
                                            SpecValidatorState.yuklenen_dosya_adi != "",
                                            SpecValidatorState.yuklenen_dosya_adi,
                                            "Şartname Yükle (PDF / Word)",
                                        ),
                                        font_size="11.5px",
                                        font_weight="600",
                                        color="#cbd5e1",
                                    ),
                                    spacing="2",
                                    align_items="center",
                                ),
                                id="spec_upload_box",
                                border="1px dashed #38bdf8",
                                padding="4px 12px",
                                border_radius="6px",
                                background="rgba(56, 189, 248, 0.05)",
                                cursor="pointer",
                                on_drop=SpecValidatorState.handle_file_upload(rx.upload_files(upload_id="spec_upload_box")),
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    rx.text_area(
                        value=SpecValidatorState.sartname_metni,
                        on_change=SpecValidatorState.set_sartname_metni,
                        placeholder="Müşteri şartnamesi maddelerini buraya yapıştırın veya sağ üstten dosya yükleyin...",
                        height="125px",
                        width="100%",
                        background="#070c18",
                        border="1px solid #1e293b",
                        border_radius="8px",
                        color="#f1f5f9",
                        font_size="12.5px",
                        line_height="1.6",
                        padding="12px 14px",
                    ),
                    rx.button(
                        "BOM Kalemlerini Şartnameye Göre Doğrula",
                        loading=SpecValidatorState.is_analyzing,
                        on_click=SpecValidatorState.validate_bom_items,
                        background="#0284c7",
                        color="#ffffff",
                        font_size="13px",
                        font_weight="700",
                        border_radius="8px",
                        padding_x="18px",
                        padding_y="10px",
                        cursor="pointer",
                        _hover={"background": "#0369a1"},
                    ),
                    spacing="3",
                    align_items="start",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                border_radius="14px",
                padding="20px 24px",
                width="100%",
            ),

            # 4. Kayıtlı Datasheet Havuzu Kartı
            datasheet_library_card(),

            # 5. Teknik Uygunluk & Sapma Matrisi Kartı
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Teknik Uygunluk & Sapma Matrisi (Compliance Matrix)",
                            font_size="13.5px",
                            font_weight="700",
                            color="#ffffff",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.text(
                                f"{SpecValidatorState.uygun_sayisi} Uygun",
                                font_size="13px",
                                font_weight="700",
                                color="#4ade80",
                            ),
                            rx.text("|", color="#475569", font_weight="600"),
                            rx.text(
                                f"{SpecValidatorState.inceleme_sayisi} İnceleme Gerekli",
                                font_size="13px",
                                font_weight="700",
                                color="#4ade80",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        width="100%",
                        padding_bottom="10px",
                        border_bottom="1px solid #151e33",
                    ),

                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    "TEKLİF EDİLEN EKİPMAN",
                                    color="#94a3b8",
                                    font_size="11px",
                                    font_weight="700",
                                    width="28%",
                                ),
                                rx.table.column_header_cell(
                                    "REFERANS DATASHEET",
                                    color="#94a3b8",
                                    font_size="11px",
                                    font_weight="700",
                                    width="20%",
                                ),
                                rx.table.column_header_cell(
                                    "UYGUNLUK",
                                    color="#94a3b8",
                                    font_size="11px",
                                    font_weight="700",
                                    width="14%",
                                ),
                                rx.table.column_header_cell(
                                    "TEKNİK KARŞILAŞTIRMA & AÇIKLAMA",
                                    color="#94a3b8",
                                    font_size="11px",
                                    font_weight="700",
                                    width="38%",
                                ),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                SpecValidatorState.matrix_rows,
                                lambda row: rx.table.row(
                                    rx.table.cell(
                                        rx.text(
                                            row["ekipman"].to(str),
                                            font_size="12.5px",
                                            font_weight="700",
                                            color="#ffffff",
                                        )
                                    ),
                                    rx.table.cell(
                                        rx.badge(
                                            rx.icon("file-check", size=12),
                                            row["datasheet"].to(str),
                                            color_scheme="cyan",
                                            variant="surface",
                                            size="1",
                                        )
                                    ),
                                    rx.table.cell(spec_status_badge(row["uygunluk"].to(str))),
                                    rx.table.cell(
                                        rx.text(
                                            row["aciklama"].to(str),
                                            font_size="12px",
                                            color="#cbd5e1",
                                            line_height="1.5",
                                        )
                                    ),
                                    align="center",
                                    border_bottom="1px solid #151e33",
                                    padding_y="12px",
                                ),
                            )
                        ),
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                border_radius="14px",
                padding="20px 24px",
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


def spec_validator_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        spec_validator_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=SpecValidatorState.on_load,
    )