import reflex as rx
import asyncio
from typing import List, Dict, Any, Union
from datetime import datetime
from .services.db_service import get_all_teklifler_from_db


def fetch_initial_quotes() -> List[Dict[str, Any]]:
    """Sayfa ayağa kalktığı anda SQLite'tan doğrudan teklifleri yükler."""
    try:
        db_teklifler = get_all_teklifler_from_db()
        yeni_liste = []
        for t in db_teklifler:
            satis = float(t.get("satis_toplam", 0.0) or t.get("satis_try", 0.0) or 0.0)
            maliyet = float(t.get("maliyet_toplam", 0.0) or t.get("maliyet_try", 0.0) or 0.0)
            
            marj = 100.0 if maliyet == 0.0 else (round(((satis - maliyet) / satis) * 100, 1) if satis > 0 else 0.0)
            marj_val = int(marj) if marj.is_integer() else marj

            yeni_liste.append({
                "kod": str(t.get("kod", "")),
                "musteri": str(t.get("musteri", "-")),
                "konu": str(t.get("konu", "-")),
                "tarih": str(t.get("teklif_tarihi", "-")),
                "sorumlu": str(t.get("sorumlu", "-")),
                "satis_try": satis,
                "maliyet_try": maliyet,
                "kar_marji": marj_val,
                "durum": str(t.get("durum", "Müşteride")),
                "yaslanma_gun": int(t.get("yaslanma_gun", 0)),
                "kalemler": t.get("kalemler", []),
            })
        return yeni_liste
    except Exception:
        return []


class DashboardState(rx.State):
    # Boş liste yerine ilk açılışta doğrudan veritabanını okur
    raw_quotes: List[Dict[str, Any]] = fetch_initial_quotes()

    selected_kpi: str = "ALL"
    status_filter: str = "Tümü"
    selected_status: str = "Tümü"
    search_query: str = ""

    selected_currency: str = "TRY"
    currency: str = "TRY (₺)"
    kur_usd: float = 43.64
    kur_eur: float = 51.84
    last_rate_update: str = "Güncel"
    is_updating_rates: bool = False

    hide_hazirlaniyor: bool = False
    hide_musteride: bool = False
    hide_kazanildi: bool = False
    hide_onaylandi: bool = False
    hide_revizyon: bool = False
    hide_reddedildi: bool = False

    async def on_load(self):
        """Dashboard açıldığında verileri yeniler."""
        await self.load_quotes()

    def select_kpi(self, kpi_key: str):
        self.selected_kpi = kpi_key

    def set_currency(self, currency: Union[str, List[str]]):
        """Segmented control tıklandığında para birimini temizler ve anında dönüştürür."""
        val = currency[0] if isinstance(currency, list) and currency else str(currency)
        if "USD" in val.upper():
            self.selected_currency = "USD"
            self.currency = "USD ($)"
        elif "EUR" in val.upper():
            self.selected_currency = "EUR"
            self.currency = "EUR (€)"
        else:
            self.selected_currency = "TRY"
            self.currency = "TRY (₺)"

    def set_search_query(self, query: str):
        self.search_query = query

    def set_status(self, status: str):
        self.status_filter = status
        self.selected_status = status

    def set_status_filter(self, status: str):
        self.status_filter = status
        self.selected_status = status

    def toggle_hazirlaniyor(self):
        self.hide_hazirlaniyor = not self.hide_hazirlaniyor

    def toggle_musteride(self):
        self.hide_musteride = not self.hide_musteride

    def toggle_kazanildi(self):
        self.hide_kazanildi = not self.hide_kazanildi
        self.hide_onaylandi = self.hide_kazanildi

    def toggle_onaylandi(self):
        self.hide_onaylandi = not self.hide_onaylandi
        self.hide_kazanildi = self.hide_onaylandi

    def toggle_revizyon(self):
        self.hide_revizyon = not self.hide_revizyon

    def toggle_reddedildi(self):
        self.hide_reddedildi = not self.hide_reddedildi

    async def load_quotes(self):
        """SQLite veritabanından tüm teklifleri eksiksiz yükler."""
        db_teklifler = get_all_teklifler_from_db()

        yeni_liste = []
        for t in db_teklifler:
            satis = float(t.get("satis_toplam", 0.0) or t.get("satis_try", 0.0) or 0.0)
            maliyet = float(t.get("maliyet_toplam", 0.0) or t.get("maliyet_try", 0.0) or 0.0)
            
            marj = 100.0 if maliyet == 0.0 else (round(((satis - maliyet) / satis) * 100, 1) if satis > 0 else 0.0)
            marj_val = int(marj) if marj.is_integer() else marj

            yeni_liste.append({
                "kod": str(t.get("kod", "")),
                "musteri": str(t.get("musteri", "-")),
                "konu": str(t.get("konu", "-")),
                "tarih": str(t.get("teklif_tarihi", "-")),
                "sorumlu": str(t.get("sorumlu", "-")),
                "satis_try": satis,
                "maliyet_try": maliyet,
                "kar_marji": marj_val,
                "durum": str(t.get("durum", "Müşteride")),
                "yaslanma_gun": int(t.get("yaslanma_gun", 0)),
                "kalemler": t.get("kalemler", []),
            })

        self.raw_quotes = yeni_liste

    async def update_rates(self):
        self.is_updating_rates = True
        yield
        await asyncio.sleep(1)
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False

    async def refresh_tcmb_now(self):
        """Yenile butonuna tıklandığında anında SQLite'tan çeker."""
        self.is_updating_rates = True
        yield
        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False
        yield rx.toast.info("Veriler ve teklif tablosu güncellendi.", position="top-right")

    async def start_hourly_rate_scheduler(self):
        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")

    # -------------------------------------------------------------
    # Kur ve Sembol Hesaplamaları
    # -------------------------------------------------------------
    @rx.var
    def currency_symbol(self) -> str:
        curr = str(self.selected_currency).upper()
        if "USD" in curr:
            return "$"
        elif "EUR" in curr:
            return "€"
        return "₺"

    @rx.var
    def active_rate(self) -> float:
        """Seçili döviz için TL bölme katsayısı."""
        curr = str(self.selected_currency).upper()
        if "USD" in curr and self.kur_usd > 0:
            return float(self.kur_usd)
        elif "EUR" in curr and self.kur_eur > 0:
            return float(self.kur_eur)
        return 1.0

    @rx.var
    def total_quotes_count(self) -> int:
        return len(self.raw_quotes)

    @rx.var
    def total_quotes_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes)
        return toplam_try / self.active_rate

    @rx.var
    def total_quotes_amount_str(self) -> str:
        tutar = self.total_quotes_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def delayed_count(self) -> int:
        return sum(
            1 for q in self.raw_quotes
            if int(q.get("yaslanma_gun", 0)) > 1 and q.get("durum") not in ["Onaylandı", "Kazanıldı"]
        )

    @rx.var
    def waiting_customer_count(self) -> int:
        return sum(1 for q in self.raw_quotes if q.get("durum") == "Müşteride")

    @rx.var
    def waiting_customer_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes if q.get("durum") == "Müşteride")
        return toplam_try / self.active_rate

    @rx.var
    def waiting_customer_amount_str(self) -> str:
        tutar = self.waiting_customer_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def won_count(self) -> int:
        return sum(1 for q in self.raw_quotes if q.get("durum") in ["Onaylandı", "Kazanıldı"])

    @rx.var
    def won_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes if q.get("durum") in ["Onaylandı", "Kazanıldı"])
        return toplam_try / self.active_rate

    @rx.var
    def won_amount_str(self) -> str:
        tutar = self.won_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def filtered_quotes(self) -> list[dict]:
        rate = self.active_rate
        symbol = self.currency_symbol

        quotes = self.raw_quotes or []
        result = []
        q_search = self.search_query.strip().lower()

        for q in quotes:
            if q_search:
                k = str(q.get("kod", "")).lower()
                m = str(q.get("musteri", "")).lower()
                c = str(q.get("konu", "")).lower()
                if q_search not in k and q_search not in m and q_search not in c:
                    continue

            d = str(q.get("durum", ""))
            if self.status_filter not in ["Tümü", "Tüm Durumlar"] and d != self.status_filter:
                continue

            if self.selected_kpi == "DELAYED" and int(q.get("yaslanma_gun", 0)) <= 1:
                continue
            elif self.selected_kpi == "WAITING" and d != "Müşteride":
                continue
            elif self.selected_kpi == "WON" and d not in ["Onaylandı", "Kazanıldı"]:
                continue

            satis_raw = float(q.get("satis_try", 0.0))
            maliyet_raw = float(q.get("maliyet_try", 0.0))

            satis_val = satis_raw / rate if rate > 0 else satis_raw
            maliyet_val = maliyet_raw / rate if rate > 0 else maliyet_raw

            s_str = f"{satis_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" {symbol}"
            m_str = f"{maliyet_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" {symbol}"

            raw_marj = str(q.get("kar_marji", "100")).replace("%", "")
            marj_str = f"%{raw_marj}"

            item = dict(q)
            item["formatted_satis"] = s_str
            item["formatted_maliyet"] = m_str
            item["formatted_kar_marji"] = marj_str
            result.append(item)

        return result

    @rx.var
    def filtered_quotes_count(self) -> int:
        return len(self.filtered_quotes)

    @rx.var
    def status_pie_data(self) -> List[Dict[str, Any]]:
        durum_sayilari = {
            "Hazırlanıyor": 0,
            "Müşteride": 0,
            "Kazanıldı": 0,
            "Revizyonda": 0,
            "Reddedildi": 0,
        }
        for q in self.raw_quotes:
            d = q.get("durum", "Müşteride")
            if "rev" in str(q.get("kod", "")).lower() or d == "Revizyonda":
                durum_sayilari["Revizyonda"] += 1
            elif d in ["Onaylandı", "Kazanıldı"]:
                durum_sayilari["Kazanıldı"] += 1
            elif d in ["Reddedildi", "Kaybedildi"]:
                durum_sayilari["Reddedildi"] += 1
            elif d in durum_sayilari:
                durum_sayilari[d] += 1
            else:
                durum_sayilari["Müşteride"] += 1

        is_kazanildi_hidden = self.hide_kazanildi or self.hide_onaylandi

        chart_data = []
        if not self.hide_hazirlaniyor and durum_sayilari["Hazırlanıyor"] > 0:
            chart_data.append({"name": "Hazırlanıyor", "value": durum_sayilari["Hazırlanıyor"], "fill": "#22d3ee"})
        if not self.hide_musteride and durum_sayilari["Müşteride"] > 0:
            chart_data.append({"name": "Müşteride", "value": durum_sayilari["Müşteride"], "fill": "#3b82f6"})
        if not is_kazanildi_hidden and durum_sayilari["Kazanıldı"] > 0:
            chart_data.append({"name": "Kazanıldı", "value": durum_sayilari["Kazanıldı"], "fill": "#10b981"})
        if not self.hide_revizyon and durum_sayilari["Revizyonda"] > 0:
            chart_data.append({"name": "Revizyonda", "value": durum_sayilari["Revizyonda"], "fill": "#f59e0b"})
        if not self.hide_reddedildi and durum_sayilari["Reddedildi"] > 0:
            chart_data.append({"name": "Reddedildi", "value": durum_sayilari["Reddedildi"], "fill": "#ef4444"})

        return chart_data

    @rx.var
    def aging_bar_data(self) -> List[Dict[str, Any]]:
        araliklar = {
            "0-3 Gün": 0,
            "4-7 Gün": 0,
            "8-14 Gün": 0,
            "15+ Gün": 0,
        }
        for q in self.raw_quotes:
            gun = int(q.get("yaslanma_gun", 0))
            if gun <= 3:
                araliklar["0-3 Gün"] += 1
            elif gun <= 7:
                araliklar["4-7 Gün"] += 1
            elif gun <= 14:
                araliklar["8-14 Gün"] += 1
            else:
                araliklar["15+ Gün"] += 1

        return [{"range": k, "hacim": v} for k, v in araliklar.items()]