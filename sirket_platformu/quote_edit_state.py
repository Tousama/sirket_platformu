import reflex as rx
from typing import List, Dict, Any, Union
from .services.db_service import (
    get_all_teklifler_from_db,
    get_teklif_by_kod,
    update_teklif_meta,
    delete_teklif_permanently,
    get_audit_logs,
    add_audit_log,
    update_kalem_maliyet,
    update_kalem_satis,
)
from .dashboard_state import DashboardState
from .global_state import GlobalState


class QuoteEditState(GlobalState):
    currency: str = "TRY (₺)"

    available_quotes: List[Dict[str, Any]] = []
    quote_options: List[str] = []
    selected_quote_label: str = ""
    current_code: str = ""

    edit_musteri: str = ""
    edit_durum: str = "Müşteride"
    edit_satis: str = "0.00"
    edit_maliyet: str = "0.00"
    edit_konu: str = ""

    items: List[Dict[str, Any]] = []
    audit_logs: List[Dict[str, Any]] = []
    _item_currency_map: Dict[int, str] = {}

    status_options: List[str] = [
        "Müşteride",
        "Hazırlanıyor",
        "Kazanıldı",
        "Onaylandı",
        "Revizyonda",
        "Reddedildi",
        "Reddedildi (Zaman Aşımı)"
    ]

    # ---------------------------------------------------------------
    # YARDIMCILAR
    # ---------------------------------------------------------------
    def _rate_for(self, pb: str) -> float:
        pb = (pb or "TRY").upper()
        if pb == "EUR":
            return float(self.kur_eur) if float(self.kur_eur or 0) > 0 else 1.0
        if pb == "USD":
            return float(self.kur_usd) if float(self.kur_usd or 0) > 0 else 1.0
        return 1.0

    @staticmethod
    def _parse_number(raw) -> float:
        try:
            s = str(raw).strip()
            for ch in ("₺", "$", "€", " ", "\u00a0"):
                s = s.replace(ch, "")
            if not s:
                return 0.0
            if "," in s and "." in s:
                if s.rfind(",") > s.rfind("."):
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(",", "")
            elif "," in s:
                s = s.replace(",", ".")
            return round(float(s), 2)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def _find_item_current_tl(self, kalem_id: int, field: str) -> float:
        try:
            kid = int(kalem_id)
        except (ValueError, TypeError):
            return 0.0
        for it in self.items:
            try:
                if it.get("id") is not None and int(it["id"]) == kid:
                    return self._parse_number(it.get(field, "0"))
            except (ValueError, TypeError):
                continue
        return 0.0

    async def _refresh_rates(self):
        try:
            from .services.tcmb import get_tcmb_kurlar
            kurlar = get_tcmb_kurlar()
            usd = float(kurlar.get("USD") or 0.0)
            eur = float(kurlar.get("EUR") or 0.0)
            if usd > 0:
                self.kur_usd = usd
            if eur > 0:
                self.kur_eur = eur
        except Exception:
            pass

    def set_currency(self, val: Union[str, List[str]]):
        v = val[0] if isinstance(val, list) and val else str(val)
        self.currency = v

    @rx.var
    def audit_logs_count(self) -> int:
        return len(self.audit_logs)

    async def on_load(self):
        await self._refresh_rates()
        await self.refresh_quote_list()

    async def refresh_quote_list(self):
        teklifler = get_all_teklifler_from_db()
        self.available_quotes = teklifler

        options = []
        for t in teklifler:
            kod = t.get("kod", "")
            musteri = t.get("musteri", "-")
            durum = t.get("durum", "Müşteride")
            options.append(f"{kod} - {musteri} ({durum})")

        self.quote_options = options

        if options:
            if not self.selected_quote_label or self.selected_quote_label not in options:
                self.selected_quote_label = options[0]
            self.load_selected_quote_details(self.selected_quote_label)
        else:
            self.selected_quote_label = ""
            self.current_code = ""
            self.edit_musteri = ""
            self.edit_durum = "Müşteride"
            self.edit_satis = "0.00"
            self.edit_maliyet = "0.00"
            self.edit_konu = ""
            self.items = []
            self.audit_logs = []
            self._item_currency_map = {}

    def set_selected_quote_label(self, label: str):
        self.selected_quote_label = label
        self.load_selected_quote_details(label)

    def load_selected_quote_details(self, label: str):
        if not label:
            return
        kod = label.split(" - ")[0].strip()
        self.current_code = kod

        t = get_teklif_by_kod(kod)
        if t:
            self.edit_musteri = str(t.get("musteri", ""))
            self.edit_durum = str(t.get("durum", "Müşteride"))

            satis_val = float(t.get("satis_toplam", 0.0) or t.get("satis_try", 0.0))
            maliyet_val = float(t.get("maliyet_toplam", 0.0) or t.get("maliyet_try", 0.0))

            self.edit_satis = f"{satis_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.edit_maliyet = f"{maliyet_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.edit_konu = str(t.get("konu", ""))
            self.audit_logs = get_audit_logs(kod)

            raw_kalemler = t.get("kalemler", [])
            formatted_items = []
            self._item_currency_map = {}

            for k in raw_kalemler:
                mik = float(k.get("miktar", 1.0))
                kid = k.get("id")
                pb = str(k.get("para_birimi", "TRY")).upper()
                rate = self._rate_for(pb)

                b_satis_ham = float(k.get("birim_satis", 0.0) or k.get("birim_fiyat", 0.0))
                b_maliyet_ham = float(k.get("birim_maliyet", 0.0))

                b_satis_tl = b_satis_ham * rate
                b_maliyet_tl = b_maliyet_ham * rate

                toplam_satis_tl = mik * b_satis_tl
                toplam_maliyet_tl = mik * b_maliyet_tl

                if toplam_maliyet_tl > 0:
                    k_marj = int(round(((toplam_satis_tl / toplam_maliyet_tl) - 1) * 100))
                elif toplam_satis_tl > 0:
                    k_marj = 100
                else:
                    k_marj = 0

                if kid is not None:
                    self._item_currency_map[int(kid)] = pb

                formatted_items.append({
                    "id": kid,
                    "malzeme_adi": k.get("malzeme_adi", "Tanımsız Malzeme"),
                    "miktar": f"{mik:g}",
                    "birim": k.get("birim", "Adet"),
                    "birim_satis_val": f"{b_satis_tl:.2f}" if b_satis_tl > 0 else "",
                    "birim_maliyet_val": f"{b_maliyet_tl:.2f}" if b_maliyet_tl > 0 else "",
                    "toplam_satis_str": f"{toplam_satis_tl:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                    "toplam_maliyet_str": f"{toplam_maliyet_tl:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                    "kar_marji_str": f"%{k_marj}",
                    "para_birimi": pb,
                    "birim_satis_orj": b_satis_ham,
                })
            self.items = formatted_items
        else:
            self.items = []
            self.audit_logs = []
            self._item_currency_map = {}

    def set_edit_musteri(self, val: str):
        self.edit_musteri = val

    def set_edit_durum(self, val: str):
        self.edit_durum = val

    def set_edit_satis(self, val: str):
        self.edit_satis = val

    def set_edit_maliyet(self, val: str):
        self.edit_maliyet = val

    def set_edit_konu(self, val: str):
        self.edit_konu = val

    # ---------------------------------------------------------------
    # DÜZENLEME: Idempotent
    # ---------------------------------------------------------------
    async def update_item_sale(self, kalem_id: int, new_sale_str: str):
        val_tl = self._parse_number(new_sale_str)

        mevcut_tl = self._find_item_current_tl(kalem_id, "birim_satis_val")
        if abs(val_tl - mevcut_tl) < 0.005:
            return

        pb = self._item_currency_map.get(int(kalem_id), "TRY")
        rate = self._rate_for(pb)
        val_orj = val_tl / rate if rate > 0 else val_tl

        yeni_toplam_satis = update_kalem_satis(int(kalem_id), val_orj, self.current_code)
        self.edit_satis = f"{yeni_toplam_satis:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.load_selected_quote_details(self.selected_quote_label)

        try:
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        yield rx.toast.success("Kalem satış fiyatı güncellendi.", position="bottom-right")

    async def update_item_cost(self, kalem_id: int, new_cost_str: str):
        val_tl = self._parse_number(new_cost_str)

        mevcut_tl = self._find_item_current_tl(kalem_id, "birim_maliyet_val")
        if abs(val_tl - mevcut_tl) < 0.005:
            return

        pb = self._item_currency_map.get(int(kalem_id), "TRY")
        rate = self._rate_for(pb)
        val_orj = val_tl / rate if rate > 0 else val_tl

        yeni_toplam_maliyet = update_kalem_maliyet(int(kalem_id), val_orj, self.current_code)
        self.edit_maliyet = f"{yeni_toplam_maliyet:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.load_selected_quote_details(self.selected_quote_label)

        try:
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        yield rx.toast.info("Kalem maliyeti güncellendi.", position="bottom-right")

    async def save_changes(self):
        if not self.current_code:
            yield rx.toast.error("İşlem yapılacak teklif bulunamadı.", position="top-right")
            return

        satis_val = self._parse_number(self.edit_satis)
        maliyet_val = self._parse_number(self.edit_maliyet)

        update_teklif_meta(
            teklif_kodu=self.current_code,
            musteri=self.edit_musteri.strip(),
            durum=self.edit_durum,
            satis=satis_val,
            maliyet=maliyet_val,
            konu=self.edit_konu.strip(),
            aciklama_notu=f"Teklif parametreleri ve durum ({self.edit_durum}) güncellendi."
        )

        self.audit_logs = get_audit_logs(self.current_code)

        try:
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        await self.refresh_quote_list()
        yield rx.toast.success(f"'{self.current_code}' teklifi güncellendi ve loglandı.", position="top-right")

    async def delete_quote(self):
        if not self.current_code:
            return

        kod = self.current_code
        delete_teklif_permanently(kod)

        try:
            dash_state = await self.get_state(DashboardState)
            await dash_state.load_quotes()
        except Exception:
            pass

        await self.refresh_quote_list()
        yield rx.toast.warning(f"'{kod}' teklifi ve bağlı tüm kayıtlar silindi.", position="top-right")