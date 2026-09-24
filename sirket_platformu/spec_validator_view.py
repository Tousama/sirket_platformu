import reflex as rx
from .spec_validator_state import SpecValidatorState
from .quote_builder import sidebar


def discrepancy_badge(level: str):
    return rx.match(
        level,
        ("danger", rx.badge("Kritik Uyumsuzluk", color_scheme="red", variant="solid")),
        ("warning", rx.badge("Teknik Sapma", color_scheme="orange", variant="solid")),
        ("success", rx.badge("Uygun", color_scheme="green", variant="solid")),
        rx.badge("Uygun", color_scheme="green", variant="soft"),
    )


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
                    rx.button(
                        rx.icon("trash", size=13),
                        "Havuzu Temizle",
                        variant="ghost",
                        color_scheme="ruby",
                        size="1",
                        on_click=SpecValidatorState.clear_all_datasheets,
                    ),
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
    return rx.vstack(
        rx.heading("Teknik Şartname & Sapma Doğrulayıcı", size="6", color="#ffffff"),
        rx.text(
            "Müşteri teknik şartnamesini girin; seçtiğiniz teklif kalemlerinin ve fabrika datasheet'lerinin uyumluluğunu denetleyin.",
            color="#94a3b8",
            size="2",
        ),
        
        # Üst Panel: Şartname Girişi ve Cihaz Seçici
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.text("Şartname Metni:", font_size="12px", font_weight="700", color="#ffffff"),
                    rx.text_area(
                        placeholder="Şartname gereksinimlerini buraya yapıştırın...",
                        value=SpecValidatorState.spec_text,
                        on_change=SpecValidatorState.set_spec_text,
                        width="100%",
                        height="130px",
                        background="#070c18",
                        border="1px solid #1e293b",
                        color="#f1f5f9",
                        font_size="12px",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.hstack(
                                rx.icon("scan-search", size=15),
                                rx.text("Şartnameyi Doğrula"),
                                spacing="1",
                                align_items="center",
                            ),
                            on_click=[
                                SpecValidatorState.run_spec_analysis,
                                SpecValidatorState.validate_bom_items,
                            ],
                            loading=SpecValidatorState.is_analyzing,
                            color_scheme="blue",
                            size="2",
                        ),
                        rx.spacer(),
                        rx.upload(
                            rx.hstack(
                                rx.icon("file-up", size=14, color="#38bdf8"),
                                rx.text("Şartname Dosyası Yükle", font_size="11.5px", color="#38bdf8"),
                                spacing="1",
                                align_items="center",
                            ),
                            id="spec_file_upload",
                            border="1px dashed #0284c7",
                            padding="4px 12px",
                            border_radius="6px",
                            background="rgba(2, 132, 199, 0.08)",
                            cursor="pointer",
                            on_drop=SpecValidatorState.handle_file_upload(rx.upload_files(upload_id="spec_file_upload")),
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    spacing="2",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                padding="16px",
            ),

            rx.card(
                rx.vstack(
                    rx.text("Doğrulanacak Cihazı Seçin:", font_size="12px", font_weight="700", color="#ffffff"),
                    rx.select(
                        SpecValidatorState.cihaz_secenekleri,
                        value=SpecValidatorState.secilen_cihaz_etiketi,
                        on_change=SpecValidatorState.set_secilen_cihaz,
                        size="2",
                        width="100%",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text(SpecValidatorState.selected_equipment["name"], font_size="12px", font_weight="700", color="#ffffff"),
                            rx.hstack(
                                rx.badge(f"IP{SpecValidatorState.selected_equipment['ip_rating']}", color_scheme="green", size="1"),
                                rx.cond(
                                    SpecValidatorState.selected_equipment["is_atex"],
                                    rx.badge("ATEX Zone 1/2", color_scheme="orange", size="1"),
                                    rx.badge("Non-Ex", color_scheme="gray", size="1"),
                                ),
                                rx.badge(SpecValidatorState.selected_equipment["voltage"], color_scheme="blue", size="1"),
                                rx.badge(SpecValidatorState.selected_equipment["protocol"], color_scheme="purple", size="1"),
                                spacing="2",
                            ),
                            spacing="1",
                        ),
                        background="#070c18",
                        border="1px solid #1e293b",
                        border_radius="8px",
                        padding="10px 12px",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                background="#0a1020",
                border="1px solid #151e33",
                padding="16px",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        # Sonuç Paneli: Seçilen Cihaza Özel Parametrik Uyumsuzluklar
        rx.cond(
            SpecValidatorState.validation_results.length() > 0,
            rx.card(
                rx.vstack(
                    rx.heading("Seçili Cihaz İçin Parametre Doğrulama Raporu", size="4", color="#ffffff"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("PARAMETRE", font_size="11px", color="#94a3b8"),
                                rx.table.column_header_cell("DURUM", font_size="11px", color="#94a3b8"),
                                rx.table.column_header_cell("MÜHENDİSLİK DETAYI", font_size="11px", color="#94a3b8"),
                                rx.table.column_header_cell("KRİTİKLİK", font_size="11px", color="#94a3b8"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                SpecValidatorState.validation_results,
                                lambda item: rx.table.row(
                                    rx.table.cell(rx.text(item["param"], font_weight="700", font_size="12px", color="#ffffff")),
                                    rx.table.cell(rx.text(item["status"], font_size="12px", color="#cbd5e1")),
                                    rx.table.cell(rx.text(item["detail"], font_size="12px", color="#94a3b8")),
                                    rx.table.cell(discrepancy_badge(item["level"])),
                                    border_bottom="1px solid #151e33",
                                    padding_y="8px",
                                )
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
                padding="16px",
                width="100%",
            ),
        ),

        # Teklif BOM & Datasheet Eşleşme Tablosu
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("table-properties", size=18, color="#34d399"),
                    rx.heading("Teklif Kalemleri Şartname Uygunluk Matrisi", size="4", color="#ffffff"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh-cw", size=13),
                        "Matrisi Güncelle",
                        size="1",
                        variant="surface",
                        color_scheme="green",
                        on_click=SpecValidatorState.validate_bom_items,
                    ),
                    width="100%",
                    align_items="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("EKİPMAN TANIMI", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("REFERANS DATASHEET", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("UYGUNLUK", font_size="11px", color="#94a3b8"),
                            rx.table.column_header_cell("MÜHENDİSLİK ANALİZ NOTU", font_size="11px", color="#94a3b8"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            SpecValidatorState.matrix_rows,
                            lambda row: rx.table.row(
                                rx.table.cell(rx.text(row["ekipman"].to(str), font_size="12px", font_weight="700", color="#ffffff")),
                                rx.table.cell(rx.text(row["datasheet"].to(str), font_size="11.5px", color="#38bdf8")),
                                rx.table.cell(spec_status_badge(row["uygunluk"].to(str))),
                                rx.table.cell(rx.text(row["aciklama"].to(str), font_size="11.5px", color="#94a3b8")),
                                border_bottom="1px solid #151e33",
                                padding_y="8px",
                            )
                        )
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            background="#0a1020",
            border="1px solid #151e33",
            border_radius="14px",
            padding="18px 22px",
            width="100%",
        ),

        # Kayıtlı Datasheet Havuzu Bileşeni
        datasheet_library_card(),

        spacing="4",
        width="100%",
        padding="20px",
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