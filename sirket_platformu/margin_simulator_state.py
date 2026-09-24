import reflex as rx
from typing import List, Dict, Any
from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB

try:
    from .services.parsers import parse_sayi
except ImportError:
    try:
        from services.parsers import parse_sayi
    except ImportError:
        import re
        def parse_sayi(deger) -> float:
            if not deger:
                return 0.0
            val = str(deger).strip()
            val = re.sub(r"[^\d,\.-]", "", val)
            if not val:
                return 0.0
            if "," in val and "." in val:
                if val.rfind(",") > val.rfind("."):
                    val = val.replace(".", "").replace(",", ".")
                else:
                    val = val.replace(",", "")
            elif "," in val:
                val = val.replace(",", ".")
            try:
                return float(val)
            except ValueError:
                return 0.0


class MarginSimulatorState(rx.State):
    # Teklif Seçenekleri Listesi
    teklif_secenekleri: List[str] = []
    secilen_teklif: str = ""

    # Seçilen Teklifin Orijinal Finansalları
    base_cost: float = 207134.88
    base_sale: float = 349890.00
    secilen_teklif_kodu: str = ""

    # Kullanıcı Kontrolleri
    iskonto_orani: float = 0.0
    doviz_soku_orani: float = 0.0
    taban_marj_orani: float = 25.0
    taban_marj_str: str = "25"

    async def on_load_sync_quotes(self):
        """DashboardState ve VERSIONS_DB'deki gerçek teklifleri çeker ve listeler."""
        dash_state = await self.get_state(DashboardState)
        options = []
        
        # 1. DashboardState.raw_quotes içerisindeki teklifler
        if hasattr(dash_state, "raw_quotes") and dash_state.raw_quotes:
            for q in dash_state.raw_quotes:
                kod = q.get("kod", "")
                musteri = q.get("musteri", "")
                maliyet = float(q.get("maliyet_try", 0.0))
                satis = float(q.get("satis_try", 0.0))
                # Standart Türkçe formatında listele (Binlik nokta, ondalık virgül)
                maliyet_fmt = f"{maliyet:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                satis_fmt = f"{satis:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                label = f"{kod} | {musteri} | Maliyet: {maliyet_fmt} ₺ | Satış: {satis_fmt} ₺"
                if label not in options:
                    options.append(label)

        # 2. VERSIONS_DB içerisindeki versiyonlar (yedek / tamamlayıcı)
        for v_name, v_data in VERSIONS_DB.items():
            kod = v_name.split("(")[0].strip()
            musteri = v_data.get("musteri", "OMC")
            
            # Kalemlerden maliyet ve satış toplamı
            items = v_data.get("items", {})
            maliyet = sum(float(it.get("birim_maliyet", 0.0)) * float(it.get("miktar", 1.0)) for it in items.values())
            satis = sum(float(it.get("birim_satis", 0.0)) * float(it.get("miktar", 1.0)) for it in items.values())
            
            if maliyet == 0:
                maliyet = float(v_data.get("maliyet", 207134.88))
            if satis == 0:
                satis = float(v_data.get("satis", 349890.00))

            maliyet_fmt = f"{maliyet:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            satis_fmt = f"{satis:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            label = f"{v_name} | {musteri} | Maliyet: {maliyet_fmt} ₺ | Satış: {satis_fmt} ₺"
            if label not in options:
                options.append(label)

        if not options:
            options = ["PT202609201555 Deneme | Shell | Maliyet: 207.134,88 ₺ | Satış: 349.890,00 ₺"]

        self.teklif_secenekleri = options
        if not self.secilen_teklif or self.secilen_teklif not in options:
            self.secilen_teklif = options[0]
            self._update_selected_quote_data()

    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val
        self._update_selected_quote_data()

    def _update_selected_quote_data(self):
        """Seçilen teklifin maliyet ve satış tutarını hem Türkçe hem Uluslararası formatı destekleyerek parse eder."""
        try:
            parts = self.secilen_teklif.split("|")
            self.secilen_teklif_kodu = parts[0].strip()

            cost_part = parts[2].split("Maliyet:")[1].replace("₺", "").strip()
            sale_part = parts[3].split("Satış:")[1].replace("₺", "").strip()

            parsed_cost = parse_sayi(cost_part)
            parsed_sale = parse_sayi(sale_part)

            # parsed_cost >= 0 olmalıdır (0,00 ₺ geçerli bir maliyetsizlik durumudur):
            self.base_cost = parsed_cost if parsed_cost >= 0 else 0.0
            self.base_sale = parsed_sale if parsed_sale > 0 else 0.0
        except Exception:
            self.base_cost = 0.0
            self.base_sale = 0.0

    def set_iskonto(self, val: Any):
        if isinstance(val, list) and len(val) > 0:
            self.iskonto_orani = round(float(val[0]), 1)
        else:
            try:
                self.iskonto_orani = round(float(val), 1)
            except (ValueError, TypeError):
                pass

    def set_doviz_soku(self, val: Any):
        if isinstance(val, list) and len(val) > 0:
            self.doviz_soku_orani = round(float(val[0]), 1)
        else:
            try:
                self.doviz_soku_orani = round(float(val), 1)
            except (ValueError, TypeError):
                pass

    def set_taban_marj_str(self, val: str):
        self.taban_marj_str = val
        try:
            clean = val.replace("%", "").replace(",", ".").strip()
            self.taban_marj_orani = float(clean) if clean else 0.0
        except ValueError:
            pass

    # --- HESAPLANAN DİNAMİK ALANLAR ---
    @rx.var
    def simule_maliyet(self) -> float:
        return round(self.base_cost * (1.0 + (self.doviz_soku_orani / 100.0)), 2)

    @rx.var
    def simule_maliyet_str(self) -> str:
        # Türkçe basamak formatı (Örn: 310.648,13 ₺)
        return f"{self.simule_maliyet:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"

    @rx.var
    def iskontolu_satis(self) -> float:
        return round(self.base_sale * (1.0 - (self.iskonto_orani / 100.0)), 2)

    @rx.var
    def iskontolu_satis_str(self) -> str:
        return f"{self.iskontolu_satis:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"

    @rx.var
    def simule_net_kar(self) -> float:
        return round(self.iskontolu_satis - self.simule_maliyet, 2)

    @rx.var
    def simule_net_kar_str(self) -> str:
        return f"{self.simule_net_kar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"

    @rx.var
    def yeni_kar_marji(self) -> float:
        if self.simule_maliyet <= 0:
            # Maliyet henüz girilmemişse marj tam satış üzerinden %100 kabul edilir
            return 100.0 if self.iskontolu_satis > 0 else 0.0
        # Satış üzerinden marj hesabı: (Net Kar / Satış) * 100
        if self.iskontolu_satis > 0:
            return round((self.simule_net_kar / self.iskontolu_satis) * 100.0, 1)
        return 0.0

    @rx.var
    def yeni_kar_marji_str(self) -> str:
        return f"%{self.yeni_kar_marji:.1f}"

    @rx.var
    def en_dip_fiyat(self) -> float:
        if self.simule_maliyet <= 0:
            return 0.0
        return round(self.simule_maliyet * (1.0 + (self.taban_marj_orani / 100.0)), 2)

    @rx.var
    def en_dip_fiyat_str(self) -> str:
        return f"{self.en_dip_fiyat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"

    @rx.var
    def is_guvenli_bolge(self) -> bool:
        return self.yeni_kar_marji >= self.taban_marj_orani

    @rx.var
    def durum_mesaji(self) -> str:
        if self.is_guvenli_bolge:
            return (
                f"%{self.iskonto_orani:.1f} iskonto uygulanmasına rağmen teklif "
                f"%{self.taban_marj_orani:.1f} asgari hedef marjın üzerinde kalmakta ve "
                f"{self.simule_net_kar_str} net kâr bırakmaktadır."
            )
        else:
            return (
                f"DİKKAT: Uygulanan iskonto ve kur şoku sonrasında kâr marjı (%{self.yeni_kar_marji:.1f}), "
                f"belirlenen %{self.taban_marj_orani:.1f} asgari taban marjın altına düşmüştür!"
            )

    async def teklife_kaydet(self):
        """Simüle edilen satış fiyatı ve marjı seçilen teklife doğrudan uygular."""
        clean_code = self.secilen_teklif_kodu.split("(")[0].strip()

        # 1. DashboardState.raw_quotes üzerinde güncelle
        dash_state = await self.get_state(DashboardState)
        guncellendi = False
        if hasattr(dash_state, "raw_quotes"):
            for q in dash_state.raw_quotes:
                if clean_code in q.get("kod", ""):
                    q["satis_try"] = self.iskontolu_satis
                    q["maliyet_try"] = self.simule_maliyet
                    q["marj"] = self.yeni_kar_marji
                    guncellendi = True
                    break

        # 2. VERSIONS_DB üzerinde güncelle
        for v_name in VERSIONS_DB.keys():
            if clean_code in v_name:
                VERSIONS_DB[v_name]["maliyet"] = self.simule_maliyet
                VERSIONS_DB[v_name]["satis"] = self.iskontolu_satis
                break

        return rx.toast.success(
            f"'{clean_code}' teklifinin satış fiyatı {self.iskontolu_satis_str}, marjı %{self.yeni_kar_marji:.1f} olarak güncellendi!",
            position="top-right"
        )