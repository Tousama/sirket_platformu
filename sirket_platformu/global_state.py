import reflex as rx
from typing import Union, List

class GlobalState(rx.State):
    """Tüm sayfalarda ortak paylaşılan global para birimi ve TCMB kurları."""
    selected_currency: str = "TRY"
    kur_usd: float = 43.64
    kur_eur: float = 51.84

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
        """Seçili para biriminin TRY bölme katsayısı."""
        curr = str(self.selected_currency).upper()
        if "USD" in curr and self.kur_usd > 0:
            return float(self.kur_usd)
        elif "EUR" in curr and self.kur_eur > 0:
            return float(self.kur_eur)
        return 1.0

    def set_currency(self, currency: Union[str, List[str]]):
        val = currency[0] if isinstance(currency, list) and currency else str(currency)
        if "USD" in val:
            self.selected_currency = "USD"
        elif "EUR" in val:
            self.selected_currency = "EUR"
        else:
            self.selected_currency = "TRY"