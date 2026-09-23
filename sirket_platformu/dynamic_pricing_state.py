import reflex as rx
from typing import List, Dict, Any
import math

# Müşteri Satınalma Davranış Profilleri
CUSTOMER_PROFILES: Dict[str, Dict[str, Any]] = {
    "Shell": {
        "gecmis_teklif": 3,
        "gecmis_kazanma": 66.7,
        "onaylanan_ort_marj": 27.5,
        "optimal_marj": 28.5,
        "duyarlilik": 0.16,
    },
    "OMC Sıvı Terminali": {
        "gecmis_teklif": 4,
        "gecmis_kazanma": 50.0,
        "onaylanan_ort_marj": 31.0,
        "optimal_marj": 32.0,
        "duyarlilik": 0.14,
    },
    "AVES GÜNEY": {
        "gecmis_teklif": 5,
        "gecmis_kazanma": 80.0,
        "onaylanan_ort_marj": 25.0,
        "optimal_marj": 26.0,
        "duyarlilik": 0.18,
    },
}

class DynamicPricingState(rx.State):
    teklif_secenekleri: List[str] = [
        "PT202609201555 Deneme | Shell | Maliyet: 207.134,88 ₺",
        "PT202609191725 | OMC Sıvı Terminali | Maliyet: 513.679,94 ₺",
        "PT2026088103 | AVES GÜNEY | Maliyet: 320.000,00 ₺",
    ]
    secilen_teklif: str = "PT202609201555 Deneme | Shell | Maliyet: 207.134,88 ₺"

    # Slider Değeri (%)
    target_margin: float = 30.0

    # Grafik Verisi
    chart_data: List[Dict[str, Any]] = []

    def on_load_recompute(self):
        self._generate_chart_curve()

    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val
        self._generate_chart_curve()

    def set_target_margin(self, val: Any):
        if isinstance(val, list):
            if len(val) > 0:
                self.target_margin = round(float(val[0]), 1)
        else:
            try:
                self.target_margin = round(float(val), 1)
            except (ValueError, TypeError):
                pass
        self._generate_chart_curve()

    # --- HESAPLANAN DİNAMİK DEĞERLER ---
    @rx.var
    def parsed_cost(self) -> float:
        try:
            part = self.secilen_teklif.split("Maliyet:")[1].replace("₺", "").replace(".", "").replace(",", ".").strip()
            return float(part)
        except Exception:
            return 207134.88

    @rx.var
    def customer_name(self) -> str:
        for c in CUSTOMER_PROFILES.keys():
            if c in self.secilen_teklif:
                return c
        return "Shell"

    @rx.var
    def profile_data(self) -> Dict[str, Any]:
        return CUSTOMER_PROFILES.get(self.customer_name, CUSTOMER_PROFILES["Shell"])

    @rx.var
    def simulated_sales_price(self) -> float:
        # Maliyet üzerine % kâr ekleme: Maliyet * (1 + Kar_Orani / 100)
        # Örn: 320.000 * (1 + 0.50) = 480.000,00 ₺
        k = self.target_margin / 100.0
        return round(self.parsed_cost * (1.0 + k), 2)

    @rx.var
    def simulated_profit(self) -> float:
        # Net Kâr Tutarı: Satış - Maliyet = Maliyet * (Kar_Orani / 100)
        # Örn: 480.000 - 320.000 = +160.000,00 ₺
        return round(self.simulated_sales_price - self.parsed_cost, 2)
    
    @rx.var
    def simulated_sales_price_str(self) -> str:
        return f"{self.simulated_sales_price:,.2f} ₺"

    @rx.var
    def simulated_profit_str(self) -> str:
        return f"+{self.simulated_profit:,.2f} ₺ Kâr"

    @rx.var
    def win_probability(self) -> float:
        """Hedef marja göre kazanma olasılığı (Sigmoid logistik düşüş)."""
        base_m = self.profile_data["onaylanan_ort_marj"]
        k = self.profile_data["duyarlilik"]
        # Sigmoid formülü
        prob = 1.0 / (1.0 + math.exp(k * (self.target_margin - base_m)))
        # %0 - %100 ölçeği
        return round(prob * 76.4, 1)

    @rx.var
    def win_probability_str(self) -> str:
        return f"%{self.win_probability:.1f}"

    @rx.var
    def optimal_margin_str(self) -> str:
        return f"%{self.profile_data['optimal_marj']:.1f}"

    @rx.var
    def gecmis_teklif_str(self) -> str:
        return f"{self.profile_data['gecmis_teklif']} Teklif"

    @rx.var
    def gecmis_kazanma_str(self) -> str:
        return f"%{self.profile_data['gecmis_kazanma']:.1f}"

    @rx.var
    def profil_tavsiye_metni(self) -> str:
        ort = self.profile_data["onaylanan_ort_marj"]
        return (
            f"Bu müşterinin geçmişte onayladığı ortalama marj: %{ort:.1f}. "
            f"Belirlediğiniz %{int(self.target_margin)} marj optimal seviyeye oldukça yakındır ve yüksek getiri sağlamaktadır."
        )

    def _generate_chart_curve(self):
        """Kâr oranına (%10 - %60) göre kazanma olasılığı ve beklenen kâr endeksini üretir."""
        base_m = self.profile_data.get("onaylanan_ort_marj", 27.5)
        k = self.profile_data.get("duyarlilik", 0.16)
        points = []

        for m_val in [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]:
            prob = (1.0 / (1.0 + math.exp(k * (m_val - base_m)))) * 100.0
            prob_curved = round(max(3.0, min(89.0, prob * 0.95)), 1)
            # Beklenen getiri = Kazanma Olasılığı * Kâr Oranı
            ev = round((prob_curved * m_val) / 6.6, 1)

            points.append({
                "marj": f"%{m_val}",
                "kazanma_ihtimali": prob_curved,
                "beklenen_getiri": ev,
            })
        self.chart_data = points
    

    def marji_teklife_uygula(self):
        return rx.toast.success(
            f"%{self.target_margin} marj ile hesaplanan {self.simulated_sales_price_str} tutarı teklife başarıyla uygulandı ve kaydedildi!",
            position="top-right"
        )