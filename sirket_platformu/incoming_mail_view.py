import reflex as rx
from .incoming_mail_state import IncomingMailState, MailItem
from .quote_builder import sidebar


def imap_settings_modal() -> rx.Component:
    """IMAP Sunucu ve E-Posta Hesap Ayarları Penceresi"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon("settings", size=18, color="#38bdf8"),
                        rx.heading("IMAP E-Posta Sunucu Ayarları", size="4", color="#ffffff"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            on_click=IncomingMailState.close_settings,
                        )
                    ),
                    width="100%",
                    padding_bottom="10px",
                    border_bottom="1px solid #1e293b",
                ),

                rx.text(
                    "Gelen teklif e-postalarını çekebilmek için IMAP sunucu bilgilerinizi tanımlayın.",
                    font_size="12px",
                    color="#94a3b8",
                ),

                rx.vstack(
                    rx.text("IMAP Sunucu Adresi:", font_size="11.5px", color="#cbd5e1", font_weight="600"),
                    rx.input(
                        value=IncomingMailState.imap_server,
                        on_change=IncomingMailState.set_imap_server,
                        placeholder="proxy.uzmanposta.com",
                        size="2",
                        width="100%",
                        background="#070c18",
                        border="1px solid #1e293b",
                    ),
                    rx.text("Port:", font_size="11.5px", color="#cbd5e1", font_weight="600"),
                    rx.input(
                        value=IncomingMailState.imap_port,
                        on_change=IncomingMailState.set_imap_port,
                        placeholder="993",
                        size="2",
                        width="100%",
                        background="#070c18",
                        border="1px solid #1e293b",
                    ),
                    rx.text("E-Posta Adresi:", font_size="11.5px", color="#cbd5e1", font_weight="600"),
                    rx.input(
                        value=IncomingMailState.email_user,
                        on_change=IncomingMailState.set_email_user,
                        placeholder="m.guner@petrotekelektrik.com.tr",
                        size="2",
                        width="100%",
                        background="#070c18",
                        border="1px solid #1e293b",
                    ),
                    rx.text("E-Posta Şifresi:", font_size="11.5px", color="#cbd5e1", font_weight="600"),
                    rx.input(
                        value=IncomingMailState.email_password,
                        on_change=IncomingMailState.set_email_password,
                        type="password",
                        placeholder="••••••••••••••••",
                        size="2",
                        width="100%",
                        background="#070c18",
                        border="1px solid #1e293b",
                    ),
                    width="100%",
                    spacing="2",
                    padding_y="8px",
                ),

                rx.hstack(
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            "Kaydet ve Kapat",
                            color_scheme="blue",
                            size="2",
                            on_click=IncomingMailState.close_settings,
                        )
                    ),
                    width="100%",
                    padding_top="8px",
                ),
                width="100%",
                spacing="3",
            ),
            background="#0a1020",
            border="1px solid #1e293b",
            border_radius="14px",
            padding="24px",
            max_width="480px",
        ),
        open=IncomingMailState.is_settings_open,
    )


def mail_subject_card(mail: MailItem) -> rx.Component:
    """Konu başlığını öne çıkaran, indirme ve aktarma seçenekli kart"""
    return rx.box(
        rx.vstack(
            # 1. Satır: RFQ Kodu, Konu ve Tarih
            rx.hstack(
                rx.hstack(
                    rx.badge(
                        mail.rfq_code,
                        color_scheme="cyan",
                        variant="surface",
                        radius="medium",
                        font_size="12px",
                        font_weight="700",
                        padding_x="8px",
                        padding_y="3px",
                    ),
                    rx.text(
                        mail.subject,
                        font_size="14.5px",
                        font_weight="700",
                        color="#ffffff",
                        letter_spacing="-0.01em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.text(mail.date, font_size="12px", color="#64748b", font_weight="500"),
                width="100%",
                align_items="center",
            ),

            # 2. Satır: Gönderen
            rx.hstack(
                rx.icon("mail", size=14, color="#64748b"),
                rx.text("Gönderen:", font_size="12px", color="#64748b"),
                rx.text(mail.sender, font_size="12.5px", color="#cbd5e1", font_weight="600"),
                spacing="2",
                align_items="center",
            ),

            # 3. Satır: Varsa Ek Dosya, İndir ve Teklife Aktar Butonları
            rx.cond(
                mail.has_attachments,
                rx.hstack(
                    rx.hstack(
                        rx.icon("paperclip", size=14, color="#f59e0b"),
                        rx.text(mail.attachment_name, font_size="12.5px", color="#e2e8f0", font_weight="500"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.button(
                            rx.icon("download", size=13),
                            "İndir",
                            variant="surface",
                            color_scheme="gray",
                            size="1",
                            cursor="pointer",
                            on_click=IncomingMailState.download_mail_attachment(mail.id, mail.attachment_name),
                        ),
                        rx.button(
                            rx.icon("check", size=13),
                            "Teklife Aktar",
                            color_scheme="green",
                            size="1",
                            cursor="pointer",
                            on_click=IncomingMailState.process_quote_attachment(
                                mail.id,
                                mail.attachment_name,
                                mail.rfq_code,
                            ),
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    background="#0f172a",
                    border="1px solid #1e293b",
                    border_radius="6px",
                    padding="6px 12px",
                    width="100%",
                    align_items="center",
                ),
                rx.hstack(
                    rx.text("(Ek dosya bulunmuyor - Metin içi içerik)", font_size="11.5px", color="#475569", font_style="italic"),
                    padding_top="2px",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        background="#0a1020",
        border="1px solid #1e293b",
        border_radius="12px",
        padding="16px 20px",
        width="100%",
        _hover={"border": "1px solid #334155", "transition": "0.15s ease"},
    )


def incoming_mail_main() -> rx.Component:
    return rx.box(
        rx.vstack(
            imap_settings_modal(),

            # Üst Navigasyon
            rx.hstack(
                rx.hstack(
                    rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                    rx.icon("mail", size=16, color="#cbd5e1"),
                    rx.heading(
                        "Gelen Teklif Mailleri (IMAP)",
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
                    rx.button(
                        rx.icon("settings", size=14),
                        "IMAP Ayarları",
                        variant="surface",
                        color_scheme="gray",
                        size="1",
                        on_click=IncomingMailState.open_settings,
                    ),
                    rx.segmented_control.root(
                        rx.segmented_control.item("TRY (₺)", value="TRY (₺)"),
                        rx.segmented_control.item("USD ($)", value="USD ($)"),
                        rx.segmented_control.item("EUR (€)", value="EUR (€)"),
                        value=IncomingMailState.currency,
                        on_change=IncomingMailState.set_currency,
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
                    spacing="3",
                    align_items="center",
                ),
                width="100%",
                padding_bottom="16px",
                border_bottom="1px solid #151e33",
            ),

            # Modül Başlığı ve Tara Butonu
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.icon("inbox", size=18, color="#38bdf8"),
                        rx.text(
                            "Tedarikçi Gelen E-Posta & Teklif Okuyucu (IMAP)",
                            font_size="16px",
                            font_weight="800",
                            color="#ffffff",
                            letter_spacing="-0.01em",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        "Gelen e-postaları konu bazında inceleyin; dilediğiniz dosyayı tek tıkla indirin veya teklife aktarın.",
                        font_size="12.5px",
                        color="#94a3b8",
                    ),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon("mail-search", size=15, color="#ffffff"),
                        rx.text("E-Postaları Tara", font_size="13px", font_weight="700", color="#ffffff"),
                        spacing="2",
                        align_items="center",
                    ),
                    loading=IncomingMailState.is_scanning,
                    on_click=IncomingMailState.scan_emails_now,
                    background="#1d4ed8",
                    _hover={"background": "#1e40af"},
                    border_radius="8px",
                    padding_x="18px",
                    padding_y="9px",
                    cursor="pointer",
                ),
                width="100%",
                align_items="center",
                padding_y="6px",
            ),

            # E-Posta Kartları
            rx.vstack(
                rx.foreach(
                    IncomingMailState.incoming_mails,
                    mail_subject_card
                ),
                width="100%",
                spacing="3",
                padding_top="8px",
            ),

            spacing="4",
            width="100%",
        ),
        padding="20px 32px",
        flex="1",
        overflow_y="auto",
        height="100vh",
        background="#030712",
    )


def incoming_mail_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        incoming_mail_main(),
        spacing="0",
        width="100%",
        height="100vh",
        overflow="hidden",
    )