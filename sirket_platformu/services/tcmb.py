import urllib.request
import xml.etree.ElementTree as ET

def get_tcmb_kurlar():
    """TCMB'den güncel USD ve EUR efektif satış kurlarını çeker."""
    kurlar = {"USD": 48.7479, "EUR": 55.9390}
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            tree = ET.fromstring(response.read())
            for currency in tree.findall("Currency"):
                kod = currency.get("CurrencyCode")
                if kod in ["USD", "EUR"]:
                    forex_selling = currency.find("BanknoteSelling")
                    if forex_selling is not None and forex_selling.text:
                        kurlar[kod] = float(forex_selling.text.replace(",", "."))
                    else:
                        forex_selling = currency.find("ForexSelling")
                        if forex_selling is not None and forex_selling.text:
                            kurlar[kod] = float(forex_selling.text.replace(",", "."))
    except Exception:
        pass
    return kurlar