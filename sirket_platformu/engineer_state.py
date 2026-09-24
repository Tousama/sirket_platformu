from typing import Any, Dict, List, Union
import reflex as rx
from .services.db_service import add_muhendis, delete_muhendis, get_all_muhendisler


class EngineerState(rx.State):
  currency: str = "TRY (₺)"

  # Yeni Mühendis Ekleme Form Alanları
  yeni_ad_soyad: str = ""
  yeni_unvan: str = "Elektrik-Elektronik Mühendisi"

  # Listelenecek Mühendisler
  engineers: List[Dict[str, Any]] = []

  def set_currency(self, val: Union[str, List[str]]):
    v = val[0] if isinstance(val, list) and val else str(val)
    self.currency = v

  def set_yeni_ad_soyad(self, val: str):
    self.yeni_ad_soyad = val

  def set_yeni_unvan(self, val: str):
    self.yeni_unvan = val

  async def on_load(self):
    """Sayfa açıldığında mühendis listesini SQLite'tan çeker."""
    await self.refresh_engineers()

  async def refresh_engineers(self):
    self.engineers = get_all_muhendisler()

  async def add_engineer(self):
    """Yeni mühendisi veritabanına ekler."""
    if not self.yeni_ad_soyad.strip():
      yield rx.toast.warning("Lütfen Ad Soyad alanını doldurun.", position="top-right")
      return

    add_muhendis(self.yeni_ad_soyad, self.yeni_unvan)
    self.yeni_ad_soyad = ""
    await self.refresh_engineers()
    yield rx.toast.success("Mühendis başarıyla eklendi.", position="top-right")

  async def remove_engineer(self, muhendis_id: int, ad_soyad: str):
    """Seçilen mühendisi ekipten siler."""
    delete_muhendis(muhendis_id)
    await self.refresh_engineers()
    yield rx.toast.info(f"'{ad_soyad}' ekipten silindi.", position="top-right")