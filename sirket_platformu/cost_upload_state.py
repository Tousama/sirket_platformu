import reflex as rx
from typing import List, Dict, Any
from io import BytesIO
import pandas as pd

from .dashboard_state import DashboardState
from .revision_diff_state import VERSIONS_DB

try:
    from .services.tcmb import get_tcmb_kurlar
    from .services.parsers import parse_sayi
except ImportError:
    from services.tcmb import get_tcmb_kurlar
    from services.parsers import parse_sayi


class CostUploadState(rx.State):
    teklif_secenekleri: List[str] = [
        "PT202609201555 Deneme - Shell (Satış: 349.890,00 ₺)",
        "PT202609191725 - OMC Sıvı Depolama (Satış: 513.679,94 ₺)",
        "PT2026088103 - AVES GÜNEY Motorin Pompası (Satış: 320.000,00 ₺)",
        "PT202600155 - Shell Derince Bakım (Satış: 46.200,00 ₺)",
    ]
    secilen_teklif: str = "PT202609191725 - OMC Sıvı Depolama (Satış: 513.679,94 ₺)"

    dosya_adi: str = "Dosya seçilmedi"
    # Başlangıçta boş: mock/yapay veriler kaldırıldı
    eslesen_kalemler: List[Dict[str, Any]] = []

    sistem_bildirim_metni: str = "Sistem: 30 gün yanıt bekleyen 1 teklif otomatik zaman aşımına alındı."

    @rx.var
    def has_matches(self) -> bool:
        return len(self.eslesen_kalemler) > 0

    @rx.var
    def eslesen_sayisi_str(self) -> str:
        return f"{len(self.eslesen_kalemler)} Kalem Eşleşti"

    def set_secilen_teklif(self, val: str):
        self.secilen_teklif = val

    async def handle_cost_upload(self, files: List[rx.UploadFile]):
        if not files:
            return

        file = files[0]
        self.dosya_adi = file.filename
        content = await file.read()
        file_stream = BytesIO(content)

        fn_low = file.filename.lower()
        bulunan_kalemler = []

        if fn_low.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(file_stream, header=None)
                for _, row in df.iterrows():
                    row_vals = [str(v).strip() for v in row.values if pd.notna(v)]
                    row_str = " ".join(row_vals).lower()

                    for target in ["vegapuls 6x", "vegaswing 61", "cerabar", "micropilot", "scully", "pakkens"]:
                        if target in row_str:
                            nums = [parse_sayi(v) for v in row_vals if parse_sayi(v) > 0]
                            if nums:
                                f_val = nums[-1]
                                pb = "EUR" if any(x in row_str for x in ["€", "eur"]) else ("USD" if any(x in row_str for x in ["$", "usd"]) else "TRY")
                                if "vegapuls" in target:
                                    mat_name = "VEGAPULS 6X Radar"
                                    ted = "VEGA Grieshaber KG"
                                elif "vegaswing" in target:
                                    mat_name = "VEGASWING 61 Seviye Şalteri"
                                    ted = "VEGA Grieshaber KG"
                                elif "scully" in target:
                                    mat_name = "Scully Sensör Seti"
                                    ted = "Scully Systems"
                                else:
                                    mat_name = target.title()
                                    ted = "Tedarikçi Firma"

                                bulunan_kalemler.append({
                                    "malzeme": mat_name,
                                    "gelen_fiyat_str": f"{f_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                    "gelen_fiyat": f_val,
                                    "pb": pb,
                                    "tedarikci": ted,
                                })
            except Exception:
                pass

        self.eslesen_kalemler = bulunan_kalemler

        if bulunan_kalemler:
            return rx.toast.success(
                f"'{file.filename}' başarıyla ayrıştırıldı. {len(bulunan_kalemler)} kalem eşleşti!",
                position="top-right",
            )
        else:
            return rx.toast.warning(
                f"'{file.filename}' okundu ancak kayıtlı teklifle eşleşen malzeme bulunamadı.",
                position="top-right",
            )

    async def maliyetleri_isle_ve_kaydet(self):
        if not self.eslesen_kalemler:
            return rx.toast.error("İşlenecek eşleşmiş maliyet kalemi bulunamadı.", position="top-right")

        kurlar = get_tcmb_kurlar()
        eur_kuru = float(kurlar.get("EUR", 56.16))
        usd_kuru = float(kurlar.get("USD", 48.66))

        toplam_eklenen_maliyet_tl = 0.0
        for k in self.eslesen_kalemler:
            rate = eur_kuru if k["pb"] == "EUR" else (usd_kuru if k["pb"] == "USD" else 1.0)
            toplam_eklenen_maliyet_tl += float(k["gelen_fiyat"]) * rate

        clean_kod = self.secilen_teklif.split()[0].strip()

        dash_state = await self.get_state(DashboardState)
        if hasattr(dash_state, "raw_quotes"):
            for q in dash_state.raw_quotes:
                if clean_kod in q.get("kod", ""):
                    q["maliyet_try"] = round(toplam_eklenen_maliyet_tl, 2)
                    satis = float(q.get("satis_try", 0.0))
                    if satis > 0:
                        q["marj"] = round(((satis - toplam_eklenen_maliyet_tl) / satis) * 100, 1)
                    break

        return rx.toast.success(
            f"Tedarikçi maliyetleri '{clean_kod}' teklifine başarıyla işlendi ve kâr marjı güncellendi!",
            position="top-right",
        )