import reflex as rx
import asyncio
from typing import List, Dict, Any, Union
from datetime import datetime
from .services.db_service import get_all_teklifler_from_db


class DashboardState(rx.State):
    # Ana Teklif Listesi
    raw_quotes: List[Dict[str, Any]] = []

    # KPI Filtreleme ve Arama
    selected_kpi: str = "ALL"
    status_filter: str = "Tümü"
    selected_status: str = "Tümü"
    search_query: str = ""

    # Para Birimi ve Kur Yönetimi
    selected_currency: str = "TRY"
    kur_usd: float = 43.64
    kur_eur: float = 51.84
    last_rate_update: str = "Güncel"
    is_updating_rates: bool = False

    # Pasta Grafik Görünürlük Bayrakları (Legend Toggle)
    hide_hazirlaniyor: bool = False
    hide_musteride: bool = False
    hide_kazanildi: bool = False
    hide_onaylandi: bool = False
    hide_revizyon: bool = False
    hide_reddedildi: bool = False

    # -------------------------------------------------------------
    # Kullanıcı Etkileşim ve Filtreleme Metotları
    # -------------------------------------------------------------
    def select_kpi(self, kpi_key: str):
        """KPI kartlarına tıklandığında filtre durumunu günceller."""
        self.selected_kpi = kpi_key

    def set_currency(self, currency: Union[str, List[str]]):
        """Segmented control para birimi değiştiğinde çalışır."""
        if isinstance(currency, list):
            self.selected_currency = currency[0] if currency else "TRY"
        else:
            self.selected_currency = str(currency)

    def set_search_query(self, query: str):
        """Arama kutusuna metin girildiğinde çalışır."""
        self.search_query = query

    def set_status(self, status: str):
        """Durum filtresi dropdown'ı değiştiğinde çalışır."""
        self.status_filter = status
        self.selected_status = status

    def set_status_filter(self, status: str):
        """Alternatif durum filtresi metodu."""
        self.status_filter = status
        self.selected_status = status

    # -------------------------------------------------------------
    # Pasta Grafik Toggle Metotları
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # Veri Yükleme ve Kur Güncelleme İşlemleri
    # -------------------------------------------------------------
    async def load_quotes(self):
        """Dashboard verilerini SQLite veritabanından çeker ve kalıcı tutar."""
        db_teklifler = get_all_teklifler_from_db()

        yeni_liste = []
        for t in db_teklifler:
            satis = float(t.get("satis_toplam", 0.0) or t.get("satis_try", 0.0))
            maliyet = float(t.get("maliyet_toplam", 0.0) or t.get("maliyet_try", 0.0))

            marj = 100.0 if maliyet == 0 else round(((satis - maliyet) / satis) * 100, 1) if satis > 0 else 0.0

            yeni_liste.append({
                "kod": t["kod"],
                "teklif_kodu": t["kod"],
                "musteri": t.get("musteri", "-"),
                "konu": t.get("konu", "-"),
                "tarih": t.get("teklif_tarihi", "-"),
                "sorumlu": t.get("sorumlu", "-"),
                "muhendis": t.get("sorumlu", "-"),
                "satis_try": satis,
                "satis_str": f"{satis:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                "maliyet_try": maliyet,
                "maliyet_str": f"{maliyet:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", "."),
                "marj": marj,
                "kar_marji": marj,
                "durum": t.get("durum", "Müşteride"),
                "yaslanma_gun": int(t.get("yaslanma_gun", 0)),
                "kalemler": t.get("kalemler", []),
            })

        self.raw_quotes = yeni_liste

    async def update_rates(self):
        """Kur yenileme işlemi."""
        self.is_updating_rates = True
        yield
        await asyncio.sleep(1)
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False

    async def refresh_tcmb_now(self):
        """Butona tıklandığında hem kurları hem teklifleri SQLite'tan yeniler."""
        self.is_updating_rates = True
        yield
        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")
        self.is_updating_rates = False
        yield rx.toast.info("Veriler ve TCMB kurları güncellendi.", position="top-right")

    async def start_hourly_rate_scheduler(self):
        """Uygulama açılışında çağrılan başlangıç senkronizasyonu."""
        await self.load_quotes()
        self.last_rate_update = datetime.now().strftime("%H:%M")

    # -------------------------------------------------------------
    # Dinamik Hesaplanmış Değerler (@rx.var)
    # -------------------------------------------------------------
    @rx.var
    def currency_symbol(self) -> str:
        """Seçili para biriminin sembolünü döndürür."""
        semboller = {"TRY": "₺", "USD": "$", "EUR": "€"}
        return semboller.get(self.selected_currency, "₺")

    @rx.var
    def total_quotes_count(self) -> int:
        return len(self.raw_quotes)

    @rx.var
    def total_quotes_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes)
        if self.selected_currency == "USD" and self.kur_usd > 0:
            return toplam_try / self.kur_usd
        elif self.selected_currency == "EUR" and self.kur_eur > 0:
            return toplam_try / self.kur_eur
        return toplam_try

    @rx.var
    def total_quotes_amount_str(self) -> str:
        tutar = self.total_quotes_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def delayed_count(self) -> int:
        """Geciken hazırlık veya yanıt bekleyen teklif sayısı."""
        return sum(
            1 for q in self.raw_quotes
            if int(q.get("yaslanma_gun", 0)) > 1 and q.get("durum") not in ["Onaylandı", "Kazanıldı"]
        )

    @rx.var
    def waiting_customer_count(self) -> int:
        """Müşteride bekleyen teklif sayısı."""
        return sum(1 for q in self.raw_quotes if q.get("durum") == "Müşteride")

    @rx.var
    def waiting_customer_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes if q.get("durum") == "Müşteride")
        if self.selected_currency == "USD" and self.kur_usd > 0:
            return toplam_try / self.kur_usd
        elif self.selected_currency == "EUR" and self.kur_eur > 0:
            return toplam_try / self.kur_eur
        return toplam_try

    @rx.var
    def waiting_customer_amount_str(self) -> str:
        tutar = self.waiting_customer_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def won_count(self) -> int:
        """Onaylanan / Kazanılan teklif sayısı."""
        return sum(1 for q in self.raw_quotes if q.get("durum") in ["Onaylandı", "Kazanıldı"])

    @rx.var
    def won_amount(self) -> float:
        toplam_try = sum(float(q.get("satis_try", 0.0)) for q in self.raw_quotes if q.get("durum") in ["Onaylandı", "Kazanıldı"])
        if self.selected_currency == "USD" and self.kur_usd > 0:
            return toplam_try / self.kur_usd
        elif self.selected_currency == "EUR" and self.kur_eur > 0:
            return toplam_try / self.kur_eur
        return toplam_try

    @rx.var
    def won_amount_str(self) -> str:
        tutar = self.won_amount
        return f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def revision_count(self) -> int:
        """Revizyon sürecindeki teklif sayısı."""
        return sum(
            1 for q in self.raw_quotes
            if "rev" in str(q.get("kod", "")).lower() or q.get("durum") == "Revizyonda"
        )

    @rx.var
    def filtered_quotes(self) -> List[Dict[str, Any]]:
        """KPI seçimi, durum filtresi ve arama metnine göre filtrelenmiş liste."""
        sonuclar = self.raw_quotes

        # KPI Kart Filtresi
        if self.selected_kpi == "MUSTERIDE":
            sonuclar = [q for q in sonuclar if q.get("durum") == "Müşteride"]
        elif self.selected_kpi in ["ONAYLANDI", "WON", "KAZANILDI"]:
            sonuclar = [q for q in sonuclar if q.get("durum") in ["Onaylandı", "Kazanıldı"]]
        elif self.selected_kpi == "REVIZYON":
            sonuclar = [q for q in sonuclar if "rev" in str(q.get("kod", "")).lower() or q.get("durum") == "Revizyonda"]
        elif self.selected_kpi == "DELAYED":
            sonuclar = [q for q in sonuclar if int(q.get("yaslanma_gun", 0)) > 1 and q.get("durum") not in ["Onaylandı", "Kazanıldı"]]

        # Dropdown Durum Filtresi (status_filter / selected_status)
        active_status = self.status_filter if self.status_filter != "Tümü" else self.selected_status
        if active_status and active_status != "Tümü":
            sonuclar = [q for q in sonuclar if q.get("durum") == active_status]

        # Metin Arama Filtresi
        if self.search_query.strip():
            q_lower = self.search_query.strip().lower()
            sonuclar = [
                q for q in sonuclar
                if q_lower in str(q.get("kod", "")).lower()
                or q_lower in str(q.get("musteri", "")).lower()
                or q_lower in str(q.get("konu", "")).lower()
            ]

        return sonuclar

    @rx.var
    def filtered_quotes_count(self) -> int:
        """dashboard_view.py içindeki 360. satır rozeti için filtrelenmiş teklif sayısı."""
        return len(self.filtered_quotes)

    # -------------------------------------------------------------
    # Pasta Grafiği İçin Dinamik Veri (@rx.var)
    # -------------------------------------------------------------
    @rx.var
    def status_pie_data(self) -> List[Dict[str, Any]]:
        """dashboard_view.py içindeki pie_chart_card için veri kaynağı."""
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
    def pie_chart_data(self) -> List[Dict[str, Any]]:
        return self.status_pie_data

    # -------------------------------------------------------------
    # Teklif Yaşlanma Çubuk Grafiği (@rx.var)
    # -------------------------------------------------------------
    @rx.var
    def aging_bar_data(self) -> List[Dict[str, Any]]:
        """Tekliflerin bekleme sürelerine (yaslanma_gun) göre dağılım grafiği verisi."""
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

        return [
            {"range": k, "count": v}
            for k, v in araliklar.items()
        ]