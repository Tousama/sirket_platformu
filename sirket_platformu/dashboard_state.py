import asyncio
import xml.etree.ElementTree as ET
import httpx
import reflex as rx
from typing import List, Dict, Any, Union

class DashboardState(rx.State):
    # Üst Bar Seçimleri
    selected_currency: str = "TRY"
    search_query: str = ""
    status_filter: str = "Tüm Durumlar"

    # Döviz Kurları (Varsayılan değerler + TCMB'den güncellenenler)
    exchange_rates: Dict[str, float] = {
        "TRY": 1.0,
        "USD": 38.50,
        "EUR": 42.00,
    }
    
    # Kur takip durumu
    last_rate_update: str = "Henüz güncellenmedi"
    is_updating_rates: bool = False
    rate_loop_running: bool = False

    # Gizleme bayrakları
    hide_musteride: bool = False
    hide_hazirlaniyor: bool = False
    hide_kazanildi: bool = False
    hide_reddedildi: bool = False

    # KPI Filtresi
    selected_kpi: str = "ALL"

    # Ham Teklif Portföyü Verileri (Taban para birimi: TRY)
    raw_quotes: List[Dict[str, Any]] = [
        {
            "kod": "PT202609201555 Deneme",
            "musteri": "Shell",
            "konu": "Enstruman Temini",
            "sorumlu": "Muhammed Güner",
            "durum": "Müşteride",
            "maliyet_try": 207134.88,
            "satis_try": 349898.00,
            "marj": 68.9,
            "yaslanma_gun": 2,
        },
        {
            "kod": "PT202609191725-Rev1",
            "musteri": "OMC",
            "konu": "LP Enstrumantasyon (Rev1)",
            "sorumlu": "Muhammed Güner",
            "durum": "Müşteride",
            "maliyet_try": 513679.94,
            "satis_try": 693467.92,
            "marj": 35.0,
            "yaslanma_gun": 3,
        },
        {
            "kod": "PT202609191650",
            "musteri": "OMC",
            "konu": "Radar & Pressure Gauge Temini",
            "sorumlu": "Muhammed Güner",
            "durum": "Hazırlanıyor",
            "maliyet_try": 185400.00,
            "satis_try": 245000.00,
            "marj": 32.1,
            "yaslanma_gun": 1,
        },
        {
            "kod": "PT2026088103",
            "musteri": "Doğukan KILIÇ",
            "konu": "AVES GÜNEY Motorin Pompası Scully",
            "sorumlu": "Muhammed Güner",
            "durum": "Kazanıldı",
            "maliyet_try": 98000.00,
            "satis_try": 151063.92,
            "marj": 54.1,
            "yaslanma_gun": 0,
        },
        {
            "kod": "PT2026088039",
            "musteri": "GİZEM AKYILDIZ",
            "konu": "DERİNCE SHELL TERMİNALİ UPS BAĞLANTISI",
            "sorumlu": "Mert EDİS",
            "durum": "Reddedildi (Zaman Aşımı)",
            "maliyet_try": 212180.08,
            "satis_try": 284478.83,
            "marj": 34.1,
            "yaslanma_gun": 35,
        },
    ]

    # TCMB Kurlarını Asenkron Olarak Çekme ve Saatlik Döngü
    @rx.event(background=True)
    async def start_hourly_rate_scheduler(self):
        async with self:
            if self.rate_loop_running:
                return
            self.rate_loop_running = True

        while True:
            # 1. Kurları TCMB today.xml üzerinden çek
            await self._fetch_tcmb_rates()
            # 2. 1 Saat (3600 saniye) bekle
            await asyncio.sleep(3600)

    async def _fetch_tcmb_rates(self):
        async with self:
            self.is_updating_rates = True

        try:
            url = "https://www.tcmb.gov.tr/kurlar/today.xml"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                new_rates = {"TRY": 1.0}
                
                for currency in root.findall("Currency"):
                    code = currency.attrib.get("CurrencyCode")
                    if code in ["USD", "EUR"]:
                        # ForexSelling (Döviz Satış) veya BanknoteSelling kuru
                        val = currency.find("ForexSelling").text or currency.find("BanknoteSelling").text
                        if val:
                            new_rates[code] = float(val.replace(",", "."))
                
                from datetime import datetime
                now_str = datetime.now().strftime("%H:%M:%S")

                async with self:
                    if "USD" in new_rates:
                        self.exchange_rates["USD"] = new_rates["USD"]
                    if "EUR" in new_rates:
                        self.exchange_rates["EUR"] = new_rates["EUR"]
                    self.last_rate_update = f"TCMB ({now_str})"
                    self.is_updating_rates = False
            else:
                async with self:
                    self.is_updating_rates = False
        except Exception:
            async with self:
                self.is_updating_rates = False

    # Manuel Yenileme Butonu İçin
    @rx.event(background=True)
    async def refresh_tcmb_now(self):
        await self._fetch_tcmb_rates()

    # Para Birimi Seçimi
    def set_currency(self, val: Union[str, List[str]]):
        if isinstance(val, list):
            self.selected_currency = val[0] if val else "TRY"
        else:
            self.selected_currency = val

    def set_search_query(self, val: str):
        self.search_query = val

    def set_status_filter(self, val: str):
        self.status_filter = val

    def select_kpi(self, kpi_name: str):
        if self.selected_kpi == kpi_name:
            self.selected_kpi = "ALL"
        else:
            self.selected_kpi = kpi_name

    def toggle_musteride(self):
        self.hide_musteride = not self.hide_musteride

    def toggle_hazirlaniyor(self):
        self.hide_hazirlaniyor = not self.hide_hazirlaniyor

    def toggle_kazanildi(self):
        self.hide_kazanildi = not self.hide_kazanildi

    def toggle_reddedildi(self):
        self.hide_reddedildi = not self.hide_reddedildi

    @rx.var
    def currency_symbol(self) -> str:
        if self.selected_currency == "USD":
            return "$"
        elif self.selected_currency == "EUR":
            return "€"
        return "₺"

    @rx.var
    def current_rate(self) -> float:
        return self.exchange_rates.get(self.selected_currency, 1.0)

    # Seçili Para Birimine Çevrilmiş Teklif Listesi
    @rx.var
    def all_quotes(self) -> List[Dict[str, Any]]:
        rate = self.current_rate
        converted = []
        for q in self.raw_quotes:
            c_maliyet = q["maliyet_try"] / rate
            c_satis = q["satis_try"] / rate
            converted.append({
                "kod": q["kod"],
                "musteri": q["musteri"],
                "konu": q["konu"],
                "sorumlu": q["sorumlu"],
                "durum": q["durum"],
                "maliyet": c_maliyet,
                "satis": c_satis,
                "maliyet_str": f"{c_maliyet:,.2f}",
                "satis_str": f"{c_satis:,.2f}",
                "marj": q["marj"],
                "yaslanma_gun": q["yaslanma_gun"],
            })
        return converted

    @rx.var
    def total_quotes_count(self) -> int:
        return len(self.all_quotes)

    @rx.var
    def total_quotes_amount_str(self) -> str:
        total = sum(q["satis"] for q in self.all_quotes)
        return f"{total:,.2f}"

    @rx.var
    def delayed_count(self) -> int:
        return sum(1 for q in self.all_quotes if q["durum"] == "Hazırlanıyor" and q["yaslanma_gun"] >= 1)

    @rx.var
    def waiting_customer_count(self) -> int:
        return sum(1 for q in self.all_quotes if q["durum"] == "Müşteride")

    @rx.var
    def waiting_customer_amount_str(self) -> str:
        total = sum(q["satis"] for q in self.all_quotes if q["durum"] == "Müşteride")
        return f"{total:,.2f}"

    @rx.var
    def won_count(self) -> int:
        return sum(1 for q in self.all_quotes if q["durum"] == "Kazanıldı")

    @rx.var
    def won_amount_str(self) -> str:
        total = sum(q["satis"] for q in self.all_quotes if q["durum"] == "Kazanıldı")
        return f"{total:,.2f}"

    @rx.var
    def filtered_quotes(self) -> List[Dict[str, Any]]:
        q_list = self.all_quotes

        if self.selected_kpi == "DELAYED":
            q_list = [q for q in q_list if q["durum"] == "Hazırlanıyor" and q["yaslanma_gun"] >= 1]
        elif self.selected_kpi == "WAITING":
            q_list = [q for q in q_list if q["durum"] == "Müşteride"]
        elif self.selected_kpi == "WON":
            q_list = [q for q in q_list if q["durum"] == "Kazanıldı"]

        if self.status_filter != "Tüm Durumlar":
            q_list = [q for q in q_list if q["durum"] == self.status_filter]

        if self.search_query.strip():
            query = self.search_query.lower()
            q_list = [
                q for q in q_list
                if query in q["kod"].lower()
                or query in q["musteri"].lower()
                or query in q["konu"].lower()
                or query in q["sorumlu"].lower()
            ]

        return q_list

    @rx.var
    def filtered_quotes_count(self) -> int:
        return len(self.filtered_quotes)

    @rx.var
    def status_pie_data(self) -> List[Dict[str, Any]]:
        counts = {}
        for q in self.all_quotes:
            st = q["durum"]
            if st == "Müşteride" and self.hide_musteride:
                continue
            if st == "Hazırlanıyor" and self.hide_hazirlaniyor:
                continue
            if st == "Kazanıldı" and self.hide_kazanildi:
                continue
            if st == "Reddedildi (Zaman Aşımı)" and self.hide_reddedildi:
                continue
            counts[st] = counts.get(st, 0) + 1

        color_map = {
            "Müşteride": "#06b6d4",
            "Hazırlanıyor": "#22d3ee",
            "Kazanıldı": "#10b981",
            "Reddedildi (Zaman Aşımı)": "#ef4444",
        }
        return [
            {"name": name, "value": count, "fill": color_map.get(name, "#64748b")}
            for name, count in counts.items()
        ]

    @rx.var
    def aging_bar_data(self) -> List[Dict[str, Any]]:
        bins = {"0-3 Gün": 0.0, "4-7 Gün": 0.0, "8-15 Gün": 0.0, "16-30 Gün": 0.0, "+30 Gün": 0.0}
        for q in self.all_quotes:
            if q["durum"] == "Müşteride":
                g = q["yaslanma_gun"]
                if g <= 3:
                    bins["0-3 Gün"] += q["satis"]
                elif g <= 7:
                    bins["4-7 Gün"] += q["satis"]
                elif g <= 15:
                    bins["8-15 Gün"] += q["satis"]
                elif g <= 30:
                    bins["16-30 Gün"] += q["satis"]
                else:
                    bins["+30 Gün"] += q["satis"]

        return [{"range": k, "hacim": round(v, 2)} for k, v in bins.items()]