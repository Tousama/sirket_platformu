import reflex as rx
import asyncio
import imaplib
import email
from email.header import decode_header
import ssl
import re
import io
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Union

from .dashboard_state import DashboardState

try:
    from .services.parsers import extract_pdf_full, extract_excel_full_with_cost_sheets
except ImportError:
    try:
        from services.parsers import extract_pdf_full, extract_excel_full_with_cost_sheets
    except ImportError:
        extract_pdf_full = None
        extract_excel_full_with_cost_sheets = None

try:
    from .shared_quotes import SHARED_QUOTES
except ImportError:
    SHARED_QUOTES = {}

try:
    from .services.db_service import save_teklif_to_db, save_teklif_full, get_all_teklifler_from_db
except ImportError:
    try:
        from services.db_service import save_teklif_to_db, save_teklif_full, get_all_teklifler_from_db
    except ImportError:
        save_teklif_to_db = None
        save_teklif_full = None
        get_all_teklifler_from_db = None


def clean_header_text(header_val: Any) -> str:
    if not header_val:
        return ""
    try:
        decoded_fragments = decode_header(header_val)
        text = ""
        for frag, enc in decoded_fragments:
            if isinstance(frag, bytes):
                text += frag.decode(enc or "utf-8", errors="ignore")
            else:
                text += str(frag)
        return text
    except Exception:
        return str(header_val)


@dataclass
class MailItem:
    id: str = ""
    rfq_code: str = "GENEL RFQ"
    sender: str = ""
    subject: str = ""
    date: str = ""
    attachment_name: str = ""
    attachments_count: int = 0
    has_attachments: bool = False
    is_processed: bool = False


class IncomingMailState(rx.State):
    currency: str = "TRY (₺)"
    is_scanning: bool = False
    
    # Uzman Posta Ayarları
    is_settings_open: bool = False
    imap_server: str = "proxy.uzmanposta.com"
    imap_port: str = "993"
    email_user: str = "m.guner@petrotekelektrik.com.tr"
    email_password: str = "Mu3@19Gu5"
    mail_folder: str = "INBOX"

    incoming_mails: List[MailItem] = []

    def open_settings(self):
        self.is_settings_open = True

    def close_settings(self):
        self.is_settings_open = False

    def set_imap_server(self, v: str):
        self.imap_server = v

    def set_imap_port(self, v: str):
        self.imap_port = v

    def set_email_user(self, v: str):
        self.email_user = v

    def set_email_password(self, v: str):
        self.email_password = v

    def set_currency(self, val: Union[str, List[str]]):
        v = val[0] if isinstance(val, list) and val else str(val)
        self.currency = v
        curr_label = "TRY" if "TRY" in v else ("USD" if "USD" in v else "EUR")
        return rx.toast.info(f"Raporlama para birimi {curr_label} olarak güncellendi.", position="bottom-right")

    async def scan_emails_now(self):
        """E-postaları hızlıca listeler."""
        self.is_scanning = True
        yield

        if not self.email_user or not self.email_password:
            self.is_scanning = False
            yield rx.toast.warning("Lütfen 'IMAP Ayarları'ndan şifrenizi kontrol edin.", position="top-right")
            return

        try:
            def fetch_fast_mails():
                context = ssl.create_default_context()
                mail = imaplib.IMAP4_SSL(self.imap_server, int(self.imap_port), ssl_context=context)
                mail.login(self.email_user.strip(), self.email_password.strip())
                mail.select(self.mail_folder, readonly=True)

                status, messages = mail.search(None, "ALL")
                mail_ids = messages[0].split()
                recent_ids = mail_ids[-30:] if len(mail_ids) > 30 else mail_ids

                fetched_records = []
                for m_id in reversed(recent_ids):
                    res, msg_data = mail.fetch(m_id, "(RFC822)")
                    if not msg_data or not isinstance(msg_data[0], tuple):
                        continue

                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = clean_header_text(msg.get("Subject", ""))
                    sender = clean_header_text(msg.get("From", ""))
                    date_str = clean_header_text(msg.get("Date", ""))[:25]

                    attachments = []
                    for part in msg.walk():
                        if part.get_content_maintype() == "multipart":
                            continue
                        filename = part.get_filename()
                        if filename:
                            clean_fname = clean_header_text(filename)
                            if clean_fname.lower().endswith((".xlsx", ".xls", ".pdf", ".csv")):
                                attachments.append(clean_fname)

                    search_pool = subject + " " + " ".join(attachments)
                    rfq_match = re.search(r"\b(PT\d{6,}[A-Za-z0-9\-_]*)\b", search_pool, re.IGNORECASE)
                    rfq_code = rfq_match.group(1).upper() if rfq_match else "GENEL RFQ"

                    sender_clean = sender.split("<")[-1].replace(">", "").strip() if "<" in sender else sender

                    # Kendi gönderdiğimiz e-postaları gelen kutusunda listeleme
                    if self.email_user.strip().lower() in sender_clean.lower():
                        continue
                    
                    first_att = attachments[0] if attachments else ""

                    fetched_records.append(
                        MailItem(
                            id=str(m_id.decode("utf-8")),
                            rfq_code=rfq_code,
                            sender=sender_clean,
                            subject=subject or "(Konusuz E-Posta)",
                            date=date_str,
                            attachment_name=first_att,
                            attachments_count=len(attachments),
                            has_attachments=len(attachments) > 0,
                            is_processed=False,
                        )
                    )

                mail.close()
                mail.logout()
                return fetched_records

            records = await asyncio.to_thread(fetch_fast_mails)

            if records:
                self.incoming_mails = records
                yield rx.toast.success(f"{len(records)} adet e-posta listelendi.", position="top-right")
            else:
                yield rx.toast.info("Gelen kutusunda e-posta bulunamadı.", position="top-right")

        except Exception as e:
            yield rx.toast.error(f"IMAP Bağlantı Hatası: {str(e)}", position="top-right")

        self.is_scanning = False

    async def download_mail_attachment(self, mail_id: str, attachment_name: str):
        if not attachment_name:
            yield rx.toast.warning("Bu e-postada indirilecek dosya eki yok.", position="bottom-right")
            return

        def fetch_file_bytes():
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(self.imap_server, int(self.imap_port), ssl_context=context)
            mail.login(self.email_user.strip(), self.email_password.strip())
            mail.select(self.mail_folder, readonly=True)

            res, msg_data = mail.fetch(mail_id.encode("utf-8"), "(RFC822)")
            target_bytes = None
            if msg_data and isinstance(msg_data[0], tuple):
                msg = email.message_from_bytes(msg_data[0][1])
                for part in msg.walk():
                    fname = part.get_filename()
                    if fname and clean_header_text(fname) == attachment_name:
                        target_bytes = part.get_payload(decode=True)
                        break
            mail.close()
            mail.logout()
            return target_bytes

        file_bytes = await asyncio.to_thread(fetch_file_bytes)
        if file_bytes:
            yield rx.download(data=file_bytes, filename=attachment_name)
            yield rx.toast.success(f"'{attachment_name}' indirildi.", position="bottom-right")
        else:
            yield rx.toast.error("Dosya sunucudan çekilemedi.", position="top-right")

    async def process_quote_attachment(self, mail_id: str, attachment_name: str, rfq_code: str):
        """Seçilen ek dosyayı indirip parse eder ve SQLite + DashboardState'e tam tutarla yazar."""
        target_mail = next((m for m in self.incoming_mails if m.id == mail_id), None)
        mail_subj = target_mail.subject if target_mail else "Gelen Teklif"
        sender = target_mail.sender if target_mail else "Tedarikçi"

        def fetch_target_bytes():
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(self.imap_server, int(self.imap_port), ssl_context=context)
            mail.login(self.email_user.strip(), self.email_password.strip())
            mail.select(self.mail_folder, readonly=True)

            res, msg_data = mail.fetch(mail_id.encode("utf-8"), "(RFC822)")
            target_bytes = None
            if msg_data and isinstance(msg_data[0], tuple):
                msg = email.message_from_bytes(msg_data[0][1])
                for part in msg.walk():
                    fname = part.get_filename()
                    if fname:
                        clean_fn = clean_header_text(fname)
                        if clean_fn == attachment_name or clean_fn.lower().endswith((".pdf", ".xlsx", ".xls")):
                            target_bytes = part.get_payload(decode=True)
                            break
            mail.close()
            mail.logout()
            return target_bytes

        file_bytes = await asyncio.to_thread(fetch_target_bytes)

        parsed_data = {}
        if file_bytes:
            if attachment_name.lower().endswith(".pdf") and extract_pdf_full:
                parsed_data = extract_pdf_full(file_bytes)
            elif attachment_name.lower().endswith((".xlsx", ".xls")) and extract_excel_full_with_cost_sheets:
                parsed_data = extract_excel_full_with_cost_sheets(io.BytesIO(file_bytes))

        final_code = parsed_data.get("teklif_kodu") or rfq_code
        if not final_code or final_code == "GENEL RFQ":
            code_search = re.search(r"\b(PT\d{6,}[A-Za-z0-9\-_]*)\b", attachment_name + " " + mail_subj, re.IGNORECASE)
            final_code = code_search.group(1).upper() if code_search else f"PT{datetime.now().strftime('%Y%m%d%H%M')}"

        musteri_adi = parsed_data.get("musteri") or sender.split("@")[0].replace(".", " ").title()
        konu = parsed_data.get("konu") or re.sub(r"^(RE:|FW:|FWD:|YNT:)\s*", "", mail_subj, flags=re.IGNORECASE).strip()

        # Sayısal satış tutarı hesabı
        satis_try = float(parsed_data.get("satis_try", 0.0))
        if satis_try <= 0.0 and parsed_data.get("toplam_tutar", 0.0) > 0:
            pb = parsed_data.get("para_birimi", "EUR")
            kur = 51.84 if pb == "EUR" else (43.64 if pb == "USD" else 1.0)
            satis_try = round(float(parsed_data["toplam_tutar"]) * kur, 2)

        maliyet_try = 0.0

        kalemler = parsed_data.get("kalemler", [])
        if not kalemler:
            kalemler = [{
                "malzeme_adi": f"Ek: {attachment_name or 'Teklif Belgesi'}",
                "miktar": 1,
                "birim": "Set",
                "birim_satis": satis_try,
                "toplam_tl": satis_try,
                "para_birimi": "TRY"
            }]

        yeni_kayit = {
            "kod": final_code,
            "musteri": musteri_adi,
            "musteri_iletisim": parsed_data.get("musteri_iletisim", sender),
            "konu": konu[:65],
            "teklif_tarihi": parsed_data.get("teklif_tarihi") or datetime.now().strftime("%d.%m.%Y"),
            "sorumlu": parsed_data.get("muhendis") or "Mustafa GÜRBÜZ",
            "durum": "Müşteride",
            "satis_toplam": satis_try,
            "maliyet_toplam": maliyet_try,
            "satis_try": satis_try,
            "maliyet_try": maliyet_try,
            "yaslanma_gun": 1,
            "kalemler": kalemler
        }

        # 1. SQLite Veritabanına Kaydet
        if save_teklif_to_db:
            try:
                save_teklif_to_db(yeni_kayit)
            except Exception as e:
                print(f"DB Kayıt Hatası: {e}")

        # 2. Ortak hafıza güncelle
        SHARED_QUOTES[final_code] = yeni_kayit

        # 3. Dashboard State'i SQLite'tan Yeniden Yüklet
        try:
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception as e:
            print(f"Dashboard Güncelleme Hatası: {e}")

        for m in self.incoming_mails:
            if m.id == mail_id:
                m.is_processed = True
                m.rfq_code = final_code
                break

        fmt_tutar = f"{satis_try:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
        yield rx.toast.success(
            f"'{final_code}' teklifi işlendi! Satış: {fmt_tutar} olarak portföye eklendi.",
            position="top-right"
        )