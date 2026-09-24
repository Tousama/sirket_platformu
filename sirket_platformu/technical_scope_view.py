import reflex as rx
from .technical_scope_state import TechnicalScopeState
from .quote_builder import sidebar


def card_header_text(num_str: str, text_str: str) -> rx.Component:
    return rx.text(
        rx.text.span(num_str, font_weight="bold", color="#38bdf8"),
        rx.text.span(text_str, font_weight="600", color="#38bdf8"),
        font_size="11.5px",
        letter_spacing="0.5px",
    )


def upload_box() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("sparkles", size=18, color="#c084fc"),
                        padding="6px",
                        border_radius="8px",
                        background="rgba(168, 85, 247, 0.15)",
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.text("Dinamik Şartname Analizi (AI / NLP Motoru)", font_size="13.5px", font_weight="bold", color="#ffffff"),
                            rx.cond(
                                TechnicalScopeState.tespit_edilen_tip != "",
                                rx.badge(TechnicalScopeState.tespit_edilen_tip, color_scheme="green", variant="surface", radius="full", size="1"),
                                rx.badge("Petrol & Endüstriyel Tesis Odaklı", color_scheme="purple", variant="surface", radius="full", size="1"),
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.text(
                            "Müşteri teknik şartnamesini yükleyin; sistem kurum, referans no, iş kapsamı maddeleri ve sorumluluk sınırlarını dinamik ayrıştırsın.",
                            font_size="12px",
                            color="#94a3b8",
                        ),
                        align_items="start",
                        spacing="0",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("wand-sparkles", size=16),
                    "Şartnameyi Çözümle",
                    color_scheme="purple",
                    size="3",
                    radius="large",
                    padding_x="22px",
                    loading=TechnicalScopeState.is_analyzing,
                    on_click=TechnicalScopeState.handle_upload_and_analyze(
                        rx.upload_files(upload_id="sartname_file_upload")
                    ),
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 4px 12px rgba(168, 85, 247, 0.35)"},
                ),
                width="100%",
                align_items="center",
            ),
            rx.upload(
                rx.vstack(
                    rx.box(
                        rx.icon("upload-cloud", size=32, color="#38bdf8"),
                        padding="10px",
                        border_radius="full",
                        background="rgba(56, 189, 248, 0.1)",
                    ),
                    rx.text(
                        "Teknik Şartname (PDF veya Word) dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın",
                        font_size="13px",
                        font_weight="600",
                        color="#e2e8f0",
                    ),
                    rx.hstack(
                        rx.text("Desteklenen Formatlar: PDF, DOCX", font_size="11.5px", color="#64748b"),
                        rx.text("•", color="#475569", font_size="11.5px"),
                        rx.text("Maks. 50 MB", font_size="11.5px", color="#64748b"),
                        rx.text("•", color="#475569", font_size="11.5px"),
                        rx.foreach(
                            rx.selected_files("sartname_file_upload"),
                            lambda f: rx.badge(rx.icon("file-check", size=12), f, color_scheme="green", variant="solid", radius="full", size="1")
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    spacing="2",
                    align_items="center",
                    justify="center",
                    padding_y="22px",
                    width="100%",
                ),
                id="sartname_file_upload",
                border="2px dashed rgba(56, 189, 248, 0.35)",
                border_radius="12px",
                background="rgba(56, 189, 248, 0.02)",
                cursor="pointer",
                width="100%",
                accept={
                    "application/pdf": [".pdf"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                    "application/msword": [".doc"],
                },
                max_files=1,
                _hover={
                    "border_color": "#38bdf8",
                    "background": "rgba(56, 189, 248, 0.06)",
                    "transition": "all 0.2s ease-in-out"
                },
            ),
            spacing="3",
            width="100%",
        ),
        background="#0a0f1d",
        border="1px solid rgba(168, 85, 247, 0.3)",
        border_radius="14px",
        padding="18px 22px",
        width="100%",
    )


def feedback_box() -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon("brain-circuit", size=17, color="#10b981"),
                    rx.text("NLP Geri Bildirim & Kendi Kendine Öğrenme (Feedback Loop)", font_size="12.5px", font_weight="bold", color="#ffffff"),
                    rx.badge(
                        f"{TechnicalScopeState.saved_feedback_count} Kayıtlı Tercih",
                        color_scheme="green",
                        variant="surface",
                        radius="full",
                        size="1"
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    "Metin kutularında yaptığınız düzeltmeleri kaydedin. Model gelecekte benzer kurum şartnamelerinde bu tercihleri otomatik uygulayacaktır.",
                    font_size="11.5px",
                    color="#94a3b8",
                ),
                align_items="start",
                spacing="0",
            ),
            rx.spacer(),
            rx.hstack(
                rx.input(
                    placeholder="Düzeltme Notu (örn: 'Ada-5 katık enjektörleri eklendi')",
                    value=TechnicalScopeState.feedback_notes,
                    on_change=TechnicalScopeState.set_feedback_notes,
                    width="320px",
                    size="2",
                ),
                rx.button(
                    rx.icon("save", size=15),
                    "Tercihi Kaydet & Modeli Eğit",
                    color_scheme="green",
                    size="2",
                    on_click=TechnicalScopeState.save_user_feedback,
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 2px 10px rgba(16, 185, 129, 0.3)"},
                ),
                spacing="2",
                align_items="center",
            ),
            width="100%",
            align_items="center",
        ),
        background="#0a0f1d",
        border="1px solid rgba(16, 185, 129, 0.3)",
        border_radius="12px",
        padding="12px 18px",
        width="100%",
    )


def technical_scope_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("file-text", size=18, color="#38bdf8"),
                    rx.heading("Teknik Teklif & Kapsam Dosyası Üreteci", size="4", color="#ffffff"),
                    rx.text("/", color="#475569"),
                    rx.text("PetroTek Elektrik", color="#94a3b8", font_size="13px"),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
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

            upload_box(),

            rx.grid(
                rx.card(
                    rx.vstack(
                        card_header_text("1. ", "TEKLİF VE ŞARTNAME BİLGİLERİ"),
                        rx.vstack(
                            rx.text("Referans Teklif (DB):", font_size="11px", color="#94a3b8"),
                            rx.select(
                                TechnicalScopeState.referans_secenekleri,
                                value=TechnicalScopeState.secilen_referans,
                                on_change=TechnicalScopeState.set_secilen_referans,
                                width="100%",
                                size="2",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Şartname Referans / No:", font_size="11px", color="#94a3b8"),
                            rx.input(
                                value=TechnicalScopeState.sartname_no,
                                on_change=TechnicalScopeState.set_sartname_no,
                                width="100%",
                                size="2",
                                placeholder="Örn: TS-GA-DOL-004-R00",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Muhatap & Hitap:", font_size="11px", color="#94a3b8"),
                            rx.input(
                                value=TechnicalScopeState.muhatap_hitap,
                                on_change=TechnicalScopeState.set_muhatap_hitap,
                                width="100%",
                                size="2",
                                placeholder="Örn: Güzel Enerji Akaryakıt A.Ş. - Teknik Müdürlük",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="1",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="16px",
                ),

                rx.card(
                    rx.vstack(
                        card_header_text("2. ", "GİRİŞ YAZISI"),
                        rx.text_area(
                            value=TechnicalScopeState.giris_yazisi,
                            on_change=TechnicalScopeState.set_giris_yazisi,
                            height="165px",
                            width="100%",
                            background="#070b14",
                            border="1px solid #1e293b",
                            font_size="12.5px",
                            line_height="1.5",
                            placeholder="Şartname analiz edildiğinde otomatik oluşturulur...",
                        ),
                        spacing="2",
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

            rx.card(
                rx.vstack(
                    card_header_text("3. ", "İŞ KAPSAMI MADDELERİ (SCOPE OF WORK)"),
                    rx.text_area(
                        value=TechnicalScopeState.is_kapsami,
                        on_change=TechnicalScopeState.set_is_kapsami,
                        height="200px",
                        width="100%",
                        background="#070b14",
                        border="1px solid #1e293b",
                        font_size="12px",
                        font_family="monospace",
                        line_height="1.6",
                        placeholder="İş kapsamı maddeleri...",
                    ),
                    spacing="2",
                    width="100%",
                ),
                background="#0a0f1d",
                border="1px solid #1e293b",
                border_radius="12px",
                padding="16px",
                width="100%",
            ),

            rx.grid(
                rx.card(
                    rx.vstack(
                        card_header_text("4. ", "İŞVEREN SORUMLULUKLARI"),
                        rx.text_area(
                            value=TechnicalScopeState.isveren_sorumluluklari,
                            on_change=TechnicalScopeState.set_isveren_sorumluluklari,
                            height="120px",
                            width="100%",
                            background="#070b14",
                            border="1px solid #1e293b",
                            font_size="12px",
                            font_family="monospace",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background="#0a0f1d",
                    border="1px solid #1e293b",
                    border_radius="12px",
                    padding="16px",
                ),

                rx.card(
                    rx.vstack(
                        card_header_text("5. ", "HARİÇ TUTULANLAR (EXCLUSIONS)"),
                        rx.text_area(
                            value=TechnicalScopeState.haric_tutulanlar,
                            on_change=TechnicalScopeState.set_haric_tutulanlar,
                            height="120px",
                            width="100%",
                            background="#070b14",
                            border="1px solid #1e293b",
                            font_size="12px",
                            font_family="monospace",
                        ),
                        spacing="2",
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

            feedback_box(),

            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.icon("file-text", size=16),
                    "Şartname Uyumlu Teknik Teklifi İndir (.docx)",
                    color_scheme="blue",
                    size="3",
                    border_radius="8px",
                    padding_x="20px",
                    on_click=TechnicalScopeState.export_docx,
                    _hover={"transform": "translateY(-1px)", "transition": "0.15s ease"},
                ),
                width="100%",
                padding_top="6px",
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


def technical_scope_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        technical_scope_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
        on_mount=TechnicalScopeState.on_load,
    )