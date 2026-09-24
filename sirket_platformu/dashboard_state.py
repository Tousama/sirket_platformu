import reflex as rx
import asyncio
import json
from typing import List, Dict, Any, Union
from datetime import datetime
from .services.db_service import get_all_teklifler_from_db


# =====================================================================
# Yardımcı fonksiyonlar (modül düzeyi, saf Python)
# =====================================================================

def _normalize_kalemler(kalemler) -> list:
    """
    DB'den gelen kalemler liste, JSON string, None veya başka bir şey olabilir.
    Her zaman geçerli bir liste döndürür.
    """
    if not kalemler:
        return []
    if isinstance(kalemler, list):
        return [k for k in kalemler if isinstance(k, dict)]
    if isinstance(kalemler, str):
        try:
            parsed = json.loads(kalemler)
            if isinstance(parsed, list):
                return [k for k in parsed if isinstance(k, dict)]
        except Exception:
            return []
    return []


def _extract_currency_from_kalemler(kalemler) -> tuple:
    """
    Kalemlerden belge para birimi ve toplam ORIJINAL satış tutarını çıkarır.
    Orijinal tutar önceliği:
      1. k["tutar_orijinal"]
      2. k["toplam"] / k["toplam_tutar"]
      3. para_birimi != TRY ise: miktar * birim_satis
      4. para_birimi == TRY ise: toplam_tl
    """
    kalemler = _normalize_kalemler(kalemler)
    if not kalemler:
        return "TRY", 0.0

    # 1. Belge para birimi
    doc_pb = "TRY"
    for k in kalemler:
        pb = str(k.get("para_birimi", "")).upper().strip()
        if pb in ("TRY", "EUR", "USD"):
            doc_pb = pb
            break

    # 2. Orijinal toplam tutar
    satis_orijinal = 0.0
    for k in kalemler:
        mik = float(k.get("miktar", 1.0) or 1.0)
        k_pb = str(k.get("para_birimi", doc_pb)).upper().strip()

        # a) Doğrudan tutar alanları
        tutar = k.get("tutar_orijinal")
        if tutar is None:
            tutar = k.get("toplam")
        if tutar is None:
            tutar = k.get("toplam_tutar")

        if tutar is not None:
            try:
                satis_orijinal += float(tutar)
                continue
            except (TypeError, ValueError):
                pass

        # b) Döviz kalemi ve tutar yoksa: miktar × birim_satis
        if k_pb != "TRY":
            b_fiyat = float(
                k.get("birim_satis")
                or k.get("birim_fiyat")
                or k.get("fiyat")
                or 0.0
            )
            if b_fiyat > 0:
                satis_orijinal += mik * b_fiyat
                continue

        # c) TRY kalemi ise toplam_tl kullan
        t_tl = float(k.get("toplam_tl", 0.0) or 0.0)
        satis_orijinal += t_tl

    return doc_pb, satis_orijinal


def _build_quote_dict(t: Dict[str, Any]) -> Dict[str, Any]:
    """
    DB'den gelen teklifi dashboard formatına çevirir + döviz bilgisi ekler.
    Bu fonksiyon, DB'de kalemlerin JSON olarak saklandığı durumu da destekler.
    """
    # 1. Tutarlar
    satis = float(t.get("satis_toplam", 0.0) or t.get("satis_try", 0.0) or 0.0)
    maliyet = float(t.get("maliyet_toplam", 0.0) or t.get("maliyet_try", 0.0) or 0.0)

    # 2. Marj
    if maliyet == 0.0:
        marj_val = 100.0
    elif satis > 0:
        marj_val = round(((satis - maliyet) / satis) * 100, 1)
    else:
        marj_val = 0.0
    marj_val = int(marj_val) if float(marj_val).is_integer() else marj_val

    # 3. Kalemler
    raw_kalemler = (
        t.get("kalemler")
        or t.get("items")
        or t.get("quote_items")
        or t.get("kalem_listesi")
        or []
    )
    kalemler = _normalize_kalemler(raw_kalemler)

    # 4. Üst seviye para birimi / orijinal tutar (varsa)
    ust_pb = str(t.get("para_birimi", "")).upper().strip()
    ust_orijinal = float(t.get("satis_orijinal", 0.0) or 0.0)

    # 5. Kalemlerden tespit
    doc_pb, satis_orijinal = _extract_currency_from_kalemler(kalemler)

    # 6. Fallback: kalem boşsa üst seviye alanları kullan
    if doc_pb == "TRY" and ust_pb in ("EUR", "USD"):
        doc_pb = ust_pb
    if satis_orijinal == 0.0 and ust_orijinal > 0:
        satis_orijinal = ust_orijinal

    # 7. Hâlâ orijinal tutar yoksa: TL varsay
    if satis_orijinal == 0.0 and satis > 0:
        satis_orijinal = satis
        doc_pb = "TRY"

    # 8. Upload esnasında kullanılan kur
    kullanilan_kur = 1.0
    if doc_pb != "TRY" and satis_orijinal > 0:
        kullanilan_kur = round(satis / satis_orijinal, 4)

    return {
        "kod": str(t.get("kod", "")),
        "musteri": str(t.get("musteri", "-")),
        "konu": str(t.get("konu", "-")),
        "tarih": str(t.get("teklif_tarihi", t.get("tarih", "-"))),
        "sorumlu": str(t.get("sorumlu", "-")),
        "satis_try": satis,
        "maliyet_try": maliyet,
        "kar_marji": marj_val,
        "durum": str(t.get("durum", "Müşteride")),
        "yaslanma_gun": int(t.get("yaslanma_gun", 0) or 0),
        "kalemler": kalemler,
        "para_birimi": doc_pb,
        "satis_orijinal": satis_orijinal,
        "kullanilan_kur": kullanilan_kur,
    }


def _display_satis(q: Dict[str, Any], selected_currency: str, dashboard_rate: float) -> float:
    """
    Teklifin satış tutarını seçili para biriminde döner.
    - Belge para birimi seçiliyse: doğrudan satis_orijinal (çift çevrim YOK).
    - Farklı döviz isteniyorsa: TL üzerinden dashboard kuruyla çevir.
    """
    doc_pb = str(q.get("para_birimi", "TRY")).upper()
    sel = (selected_currency or "TRY").upper()
    satis_try = float(q.get("satis_try", 0.0))
    satis_orijinal = float(q.get("satis_orijinal", 0.0))

    if sel == "TRY":
        return satis_try

    if doc_pb == sel and satis_orijinal > 0:
        return satis_orijinal

    if dashboard_rate > 0:
        return satis_try / dashboard_rate
    return satis_try


def _display_maliyet(q: Dict[str, Any], selected_currency: str, dashboard_rate: float) -> float:
    """Maliyet TL bazlıdır; seçili para birimine çevirir."""
    sel = (selected_currency or "TRY").upper()
    maliyet_try = float(q.get("maliyet_try", 0.0))
    if sel == "TRY":
        return maliyet_try
    if dashboard_rate > 0:
        return maliyet_try / dashboard_rate
    return maliyet_try


def _format_tr(val: float) -> str:
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fetch_initial_quotes() -> List[Dict[str, Any]]:
    try:
        db_teklifler = get_all_teklifler_from_db()
        return [_build_quote_dict(t) for t in db_teklifler]
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
        """Dashboard açıldığında TCMB kurlarını + teklifleri yeniler."""
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
        """
        SQLite'tan teklifleri + TCMB'den güncel USD/EUR kurlarını yükler.
        Her dashboard açılışında ve yenilemede çağrılır.
        """
        # 1. TCMB'den güncel kurları çek
        try:
            from .services.tcmb import get_tcmb_kurlar
            kurlar = get_tcmb_kurlar()
            usd = float(kurlar.get("USD") or 0.0)
            eur = float(kurlar.get("EUR") or 0.0)
            if usd > 0:
                self.kur_usd = usd
            if eur > 0:
                self.kur_eur = eur
            self.last_rate_update = datetime.now().strftime("%H:%M")
        except Exception:
            pass

        # 2. Teklifleri yükle
        try:
            db_teklifler = get_all_teklifler_from_db()
            self.raw_quotes = [_build_quote_dict(t) for t in db_teklifler]
        except Exception:
            self.raw_quotes = []

    async def update_rates(self):
        self.is_updating_rates = True
        yield
        await asyncio.sleep(1)
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False

    async def refresh_tcmb_now(self):
        """Yenile butonuna tıklandığında TCMB kuru + veriler yenilenir."""
        self.is_updating_rates = True
        yield

        # TCMB'den güncel kurları çek
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

        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False
        yield rx.toast.info("Veriler ve teklif tablosu güncellendi.", position="top-right")

    async def start_hourly_rate_scheduler(self):
        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")

    # -------------------------------------------------------------
    # Kur ve Sembol
    # -------------------------------------------------------------
    @rx.var
    def currency_symbol(self) -> str:
        curr = str(self.selected_currency).upper()
        if "USD" in curr:
            return "$"
        if "EUR" in curr:
            return "€"
        return "₺"

    @rx.var
    def active_rate(self) -> float:
        """Seçili döviz için TL bölme katsayısı (TCMB kuru)."""
        curr = str(self.selected_currency).upper()
        if "USD" in curr and self.kur_usd > 0:
            return float(self.kur_usd)
        if "EUR" in curr and self.kur_eur > 0:
            return float(self.kur_eur)
        return 1.0

    # -------------------------------------------------------------
    # KPI Toplamları
    # -------------------------------------------------------------
    @rx.var
    def total_quotes_count(self) -> int:
        return len(self.raw_quotes)

    @rx.var
    def total_quotes_amount(self) -> float:
        rate = self.active_rate
        return sum(_display_satis(q, self.selected_currency, rate) for q in self.raw_quotes)

    @rx.var
    def total_quotes_amount_str(self) -> str:
        return _format_tr(self.total_quotes_amount)

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
        rate = self.active_rate
        return sum(
            _display_satis(q, self.selected_currency, rate)
            for q in self.raw_quotes
            if q.get("durum") == "Müşteride"
        )

    @rx.var
    def waiting_customer_amount_str(self) -> str:
        return _format_tr(self.waiting_customer_amount)

    @rx.var
    def won_count(self) -> int:
        return sum(1 for q in self.raw_quotes if q.get("durum") in ["Onaylandı", "Kazanıldı"])

    @rx.var
    def won_amount(self) -> float:
        rate = self.active_rate
        return sum(
            _display_satis(q, self.selected_currency, rate)
            for q in self.raw_quotes
            if q.get("durum") in ["Onaylandı", "Kazanıldı"]
        )

    @rx.var
    def won_amount_str(self) -> str:
        return _format_tr(self.won_amount)

    # -------------------------------------------------------------
    # Tablo Filtresi + Görüntüleme Formatları
    # -------------------------------------------------------------
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

            satis_val = _display_satis(q, self.selected_currency, rate)
            maliyet_val = _display_maliyet(q, self.selected_currency, rate)

            s_str = _format_tr(satis_val) + f" {symbol}"
            m_str = _format_tr(maliyet_val) + f" {symbol}"

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

    # -------------------------------------------------------------
    # Grafikler
    # -------------------------------------------------------------
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