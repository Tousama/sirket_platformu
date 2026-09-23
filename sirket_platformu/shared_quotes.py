"""
Tüm modüller arasında paylaşılan, SQLite tabanlı canlı teklif ve maliyet havuzu.
"""
from typing import Dict, Any
from .services.db_service import save_teklif_full, get_all_teklifler_from_db, add_tedarikci_maliyet

GLOBAL_TEKLIFLER: Dict[str, Dict[str, Any]] = {}

def sync_from_sqlite():
    """Uygulama başladığında SQLite'taki verileri GLOBAL_TEKLIFLER hafızasına yükler."""
    global GLOBAL_TEKLIFLER
    kayitlar = get_all_teklifler_from_db()
    for t in kayitlar:
        kod = t["kod"]
        GLOBAL_TEKLIFLER[kod] = {
            "kod": kod,
            "baslik": f"{kod} - {t.get('musteri', '')}",
            "musteri": t.get("musteri", ""),
            "konu": t.get("konu", ""),
            "teklif_tarihi": t.get("teklif_tarihi", ""),
            "sorumlu": t.get("sorumlu", ""),
            "durum": t.get("durum", "Müşteride"),
            "yaslanma_gun": t.get("yaslanma_gun", 0),
            "satis_try": t.get("satis_toplam", 0.0),
            "maliyet_try": t.get("maliyet_toplam", 0.0),
            "kalemler": t.get("kalemler", []),
        }

# Dosya import edildiğinde veritabanından hafızayı doldur
sync_from_sqlite()

SHARED_QUOTES = GLOBAL_TEKLIFLER

def register_quote(kod: str, baslik: str, kalemler: list, musteri: str = "", extra_data: dict = None):
    """Yeni teklifi hem SQLite'a hem de canlı hafızaya kaydeder."""
    clean_kod = kod.strip().upper()
    teklif_obj = {
        "kod": clean_kod,
        "musteri": musteri,
        "satis_try": sum(float(k.get("tutar_tl", 0.0)) for k in kalemler),
        "durum": "Müşteride",
    }
    if extra_data:
        teklif_obj.update(extra_data)

    # 1. SQLite'a kalıcı olarak yaz
    save_teklif_full(teklif_obj, kalemler)

    # 2. Canlı belleği güncelle
    GLOBAL_TEKLIFLER[clean_kod] = {
        "kod": clean_kod,
        "baslik": baslik or f"{clean_kod} - {musteri}".strip(" -"),
        "musteri": musteri,
        "kalemler": kalemler,
    }
def update_supplier_cost(kod: str, tedarikci_adi: str, maliyet_kalemleri: list):
    """Tedarikçiden gelen birim fiyatları ilgili teklifin kalemlerine yazar."""
    clean_kod = kod.strip().upper()
    if clean_kod in GLOBAL_TEKLIFLER:
        teklif_kalemleri = GLOBAL_TEKLIFLER[clean_kod]["kalemler"]
        for m_item in maliyet_kalemleri:
            m_ad = m_item.get("malzeme", "").lower()
            m_fiyat = float(m_item.get("gelen_fiyat", 0.0))
            for tk in teklif_kalemleri:
                tk_ad = tk["malzeme_adi"].lower()
                if any(x in tk_ad for x in ["radar", "vegapuls"]) and ("radar" in m_ad or "vegapuls" in m_ad):
                    tk["fiyatlar"][tedarikci_adi] = m_fiyat
                elif any(x in tk_ad for x in ["swing", "şalter", "level s"]) and ("swing" in m_ad or "level s" in m_ad or "şalter" in m_ad):
                    tk["fiyatlar"][tedarikci_adi] = m_fiyat
                    
                    
SHARED_QUOTES = GLOBAL_TEKLIFLER