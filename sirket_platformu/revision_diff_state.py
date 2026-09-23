import reflex as rx
from typing import List, Dict, Any
from .dashboard_state import DashboardState

VERSIONS_DB: Dict[str, Dict[str, Any]] = {
    "PT202609191725 (Rev 0 - Orijinal)": {
        "musteri": "OMC Sıvı Depolama Terminali",
        "konu": "LP Enstrümantasyon & Saha Kablaj İşi",
        "sorumlu": "Muhammed GÜNER",
        "items": {
            "Level Inst. Transmitter": {"miktar": 2.0, "birim": "Adet", "birim_maliyet": 52000.0, "birim_satis": 78000.0},
            "Pressure Transmitter 0-100 bar": {"miktar": 3.0, "birim": "Adet", "birim_maliyet": 24000.0, "birim_satis": 34000.0},
            "Flow Switch (Akış Şalteri)": {"miktar": 1.0, "birim": "Adet", "birim_maliyet": 28000.0, "birim_satis": 43200.0},
            "Saha Enstrümantasyon & Montaj İşçiliği": {"miktar": 1.0, "birim": "Hizmet", "birim_maliyet": 106648.13, "birim_satis": 169108.75},
        }
    },
    "PT202609191725-Rev1 (Müşteri İndirimi)": {
        "musteri": "OMC Sıvı Depolama Terminali",
        "konu": "LP Enstrümantasyon & Saha Kablaj İşi",
        "sorumlu": "Muhammed GÜNER",
        "items": {
            "Level Inst. Transmitter": {"miktar": 2.0, "birim": "Adet", "birim_maliyet": 52000.0, "birim_satis": 74250.0},
            "Pressure Transmitter 0-100 bar": {"miktar": 3.0, "birim": "Adet", "birim_maliyet": 24000.0, "birim_satis": 32400.0},
            "Flow Switch (Akış Şalteri)": {"miktar": 1.0, "birim": "Adet", "birim_maliyet": 28000.0, "birim_satis": 43200.0},
            "Saha Enstrümantasyon & Montaj İşçiliği": {"miktar": 1.0, "birim": "Hizmet", "birim_maliyet": 106648.13, "birim_satis": 155000.0},
        }
    },
    "PT202609191725-Rev2 (Kapsam Daraltma)": {
        "musteri": "OMC Sıvı Depolama Terminali",
        "konu": "LP Enstrümantasyon & Saha Kablaj İşi",
        "sorumlu": "Muhammed GÜNER",
        "items": {
            "Level Inst. Transmitter": {"miktar": 1.0, "birim": "Adet", "birim_maliyet": 52000.0, "birim_satis": 74250.0},
            "Pressure Transmitter 0-100 bar": {"miktar": 2.0, "birim": "Adet", "birim_maliyet": 24000.0, "birim_satis": 32400.0},
            "Flow Switch (Akış Şalteri)": {"miktar": 1.0, "birim": "Adet", "birim_maliyet": 28000.0, "birim_satis": 43200.0},
            "Saha Enstrümantasyon & Montaj İşçiliği": {"miktar": 1.0, "birim": "Hizmet", "birim_maliyet": 75000.0, "birim_satis": 120000.0},
        }
    },
}

class RevisionDiffState(rx.State):
    eski_versiyon_secenekleri: List[str] = list(VERSIONS_DB.keys())
    secilen_eski_versiyon: str = "PT202609191725 (Rev 0 - Orijinal)"

    yeni_versiyon_secenekleri: List[str] = list(VERSIONS_DB.keys())
    secilen_yeni_versiyon: str = "PT202609191725 (Rev 0 - Orijinal)"

    yeni_revizyon_kodu: str = "PT202609191725-Rev3"
    revizyon_gerekcesi: str = "Kalem bazlı birim fiyat ve kapsam düzenlemesi"

    toplam_maliyet_str: str = "0,00 ₺"
    maliyet_fark_str: str = "0,00 ₺ (Aynı)"

    toplam_satis_str: str = "0,00 ₺"
    satis_fark_str: str = "0,00 ₺ (Aynı)"

    kar_marji_str: str = "%0.0"
    marj_fark_str: str = "%0.0 (Aynı)"

    diff_items: List[Dict[str, Any]] = []

    def on_load_recompute(self):
        self._calculate_diff()

    def set_secilen_eski_versiyon(self, val: str):
        self.secilen_eski_versiyon = val
        self._calculate_diff()

    def set_secilen_yeni_versiyon(self, val: str):
        self.secilen_yeni_versiyon = val
        self._calculate_diff()

    def set_yeni_revizyon_kodu(self, val: str):
        self.yeni_revizyon_kodu = val

    def set_revizyon_gerekcesi(self, val: str):
        self.revizyon_gerekcesi = val

    def _calculate_diff(self):
        v_old = VERSIONS_DB.get(self.secilen_eski_versiyon, {})
        v_new = VERSIONS_DB.get(self.secilen_yeni_versiyon, {})

        if not v_old or not v_new:
            return

        all_materials = list(dict.fromkeys(list(v_old.get("items", {}).keys()) + list(v_new.get("items", {}).keys())))
        new_diff_items = []

        for mat in all_materials:
            old_item = v_old.get("items", {}).get(mat, {"miktar": 0.0, "birim": "Adet", "birim_maliyet": 0.0, "birim_satis": 0.0})
            new_item = v_new.get("items", {}).get(mat, {"miktar": 0.0, "birim": "Adet", "birim_maliyet": 0.0, "birim_satis": 0.0})

            eski_miktar = float(old_item["miktar"])
            yeni_miktar = float(new_item["miktar"])

            eski_birim_satis = float(old_item.get("birim_satis", 0.0))
            yeni_birim_satis = float(new_item.get("birim_satis", eski_birim_satis))
            birim_cost = float(new_item.get("birim_maliyet", old_item.get("birim_maliyet", 0.0)))

            eski_toplam_satis = eski_miktar * eski_birim_satis
            yeni_toplam_satis = yeni_miktar * yeni_birim_satis
            fark_val = yeni_toplam_satis - eski_toplam_satis

            durum_degisti = (round(fark_val, 2) != 0 or eski_miktar != yeni_miktar or round(eski_birim_satis - yeni_birim_satis, 2) != 0)

            new_diff_items.append({
                "malzeme": mat,
                "birim": new_item.get("birim", "Adet"),
                "birim_maliyet": birim_cost,
                "eski_miktar": f"{int(eski_miktar)} {old_item['birim']}",
                "yeni_miktar": str(int(yeni_miktar)),
                "eski_birim_satis": f"{eski_birim_satis:,.2f}",
                # İnput içinde saf float tutulur (birim satış fiyatı)
                "yeni_birim_satis": str(round(yeni_birim_satis, 2)),
                "yeni_birim_satis_num": yeni_birim_satis,
                "eski_toplam_satis": f"{eski_toplam_satis:,.2f}",
                "yeni_toplam_satis": f"{yeni_toplam_satis:,.2f}",
                "yeni_toplam_satis_num": yeni_toplam_satis,
                "fark": f"{fark_val:,.2f}" if fark_val <= 0 else f"+{fark_val:,.2f}",
                "is_negative": (fark_val < 0),
                "durum": "Güncellendi" if durum_degisti else "Aynı",
                "badge_color": "amber" if durum_degisti else "gray",
            })

        self.diff_items = new_diff_items
        self._recompute_totals_from_items()

    def update_item_qty(self, malzeme: str, val: str):
        """Miktar değiştiğinde: Birim Fiyat korunur, Toplam Satış ve Maliyet paralel güncellenir."""
        try:
            new_qty = float(val) if val.strip() else 0.0
        except ValueError:
            new_qty = 0.0

        for row in self.diff_items:
            if row["malzeme"] == malzeme:
                row["yeni_miktar"] = str(int(new_qty)) if new_qty.is_integer() else str(new_qty)
                unit_price = float(row.get("yeni_birim_satis_num", 0.0))
                
                # Yeni Toplam Satış = Yeni Miktar * Birim Satış
                new_total_sales = round(new_qty * unit_price, 2)
                row["yeni_toplam_satis_num"] = new_total_sales
                row["yeni_toplam_satis"] = f"{new_total_sales:,.2f}"

                # Eski toplam satışla fark
                eski_toplam = float(row["eski_toplam_satis"].replace(".", "").replace(",", "."))
                fark_val = new_total_sales - eski_toplam
                row["fark"] = f"{fark_val:,.2f}" if fark_val <= 0 else f"+{fark_val:,.2f}"
                row["is_negative"] = (fark_val < 0)

                row["durum"] = "Güncellendi" if round(fark_val, 2) != 0 else "Aynı"
                row["badge_color"] = "amber" if round(fark_val, 2) != 0 else "gray"
                break

        self._recompute_totals_from_items()

    def update_item_unit_price(self, malzeme: str, val: str):
        """Birim Satış Fiyatı değiştiğinde: Toplam Satış = Miktar * Yeni Birim Fiyat olarak güncellenir."""
        val_str = str(val).strip()
        if not val_str:
            return

        clean = val_str.replace("₺", "").replace(" ", "").replace(",", ".")
        try:
            new_unit_price = float(clean)
        except ValueError:
            return

        for row in self.diff_items:
            if row["malzeme"] == malzeme:
                row["yeni_birim_satis"] = val_str
                row["yeni_birim_satis_num"] = new_unit_price

                try:
                    qty = float(row.get("yeni_miktar", 0.0))
                except ValueError:
                    qty = 0.0

                new_total_sales = round(qty * new_unit_price, 2)
                row["yeni_toplam_satis_num"] = new_total_sales
                row["yeni_toplam_satis"] = f"{new_total_sales:,.2f}"

                eski_toplam = float(row["eski_toplam_satis"].replace(".", "").replace(",", "."))
                fark_val = new_total_sales - eski_toplam
                row["fark"] = f"{fark_val:,.2f}" if fark_val <= 0 else f"+{fark_val:,.2f}"
                row["is_negative"] = (fark_val < 0)

                row["durum"] = "Güncellendi" if round(fark_val, 2) != 0 else "Aynı"
                row["badge_color"] = "amber" if round(fark_val, 2) != 0 else "gray"
                break

        self._recompute_totals_from_items()

    def _recompute_totals_from_items(self):
        v_old = VERSIONS_DB.get(self.secilen_eski_versiyon, {})

        # 1. Eski toplam maliyet ve satış
        c_old = sum(float(it.get("birim_maliyet", 0.0)) * float(it.get("miktar", 1.0)) for it in v_old.get("items", {}).values())
        s_old = sum(float(it.get("birim_satis", 0.0)) * float(it.get("miktar", 1.0)) for it in v_old.get("items", {}).values())

        # 2. Yeni toplam maliyet (Yeni Miktar * Birim Maliyet)
        total_new_cost = 0.0
        for row in self.diff_items:
            try:
                q = float(row.get("yeni_miktar", 0.0))
            except ValueError:
                q = 0.0
            total_new_cost += q * float(row.get("birim_maliyet", 0.0))

        # 3. Yeni toplam satış (Yeni Miktar * Yeni Birim Satış)
        total_new_sales = sum(float(row.get("yeni_toplam_satis_num", 0.0)) for row in self.diff_items)

        diff_c = total_new_cost - c_old
        diff_s = total_new_sales - s_old
        m_new = ((total_new_sales - total_new_cost) / total_new_sales * 100) if total_new_sales > 0 else 0
        m_old = ((s_old - c_old) / s_old * 100) if s_old > 0 else 0
        diff_m = m_new - m_old

        self.toplam_maliyet_str = f"{total_new_cost:,.2f} ₺"
        if round(diff_c, 2) < 0:
            self.maliyet_fark_str = f"{diff_c:,.2f} ₺ (Tasarruf)"
        elif round(diff_c, 2) > 0:
            self.maliyet_fark_str = f"+{diff_c:,.2f} ₺ (Maliyet Artışı)"
        else:
            self.maliyet_fark_str = "0,00 ₺ (Aynı)"

        self.toplam_satis_str = f"{total_new_sales:,.2f} ₺"
        if round(diff_s, 2) < 0:
            pct = abs(diff_s / s_old * 100) if s_old > 0 else 0
            self.satis_fark_str = f"{diff_s:,.2f} ₺ (%{pct:.1f} İskonto)"
        elif round(diff_s, 2) > 0:
            self.satis_fark_str = f"+{diff_s:,.2f} ₺ (İlave Bedel)"
        else:
            self.satis_fark_str = "0,00 ₺ (Aynı)"

        self.kar_marji_str = f"%{m_new:.1f}"
        self.marj_fark_str = f"{'+' if diff_m > 0 else ''}%{diff_m:.1f} Marj" if round(diff_m, 1) != 0 else "%0.0 (Aynı)"

    async def revizyon_kopyala_ve_baslat(self):
        if not self.yeni_revizyon_kodu.strip():
            return rx.toast.error("Lütfen geçerli bir revizyon kodu girin.", position="top-right")

        clean_kod = self.yeni_revizyon_kodu.strip()
        v_base = VERSIONS_DB.get(self.secilen_yeni_versiyon, VERSIONS_DB.get(self.secilen_eski_versiyon, {}))

        orijinal_musteri = v_base.get("musteri", "OMC Sıvı Depolama Terminali")
        orijinal_konu = v_base.get("konu", "LP Enstrümantasyon & Saha Kablaj İşi")
        orijinal_sorumlu = v_base.get("sorumlu", "Muhammed GÜNER")

        total_new_cost = 0.0
        total_new_sales = 0.0
        saved_items = {}

        for row in self.diff_items:
            try:
                q = float(row.get("yeni_miktar", 0.0))
            except ValueError:
                q = 0.0
            unit_cost = float(row.get("birim_maliyet", 0.0))
            unit_sale = float(row.get("yeni_birim_satis_num", 0.0))

            total_new_cost += q * unit_cost
            total_new_sales += (q * unit_sale)

            saved_items[row["malzeme"]] = {
                "miktar": q,
                "birim": row.get("birim", "Adet"),
                "birim_maliyet": unit_cost,
                "birim_satis": unit_sale,
            }

        marj = round(((total_new_sales - total_new_cost) / total_new_sales * 100), 1) if total_new_sales > 0 else 0.0

        yeni_dashboard_satiri = {
            "kod": clean_kod,
            "musteri": orijinal_musteri,
            "konu": f"{orijinal_konu} ({clean_kod})",
            "sorumlu": orijinal_sorumlu,
            "durum": "Hazırlanıyor",
            "maliyet_try": round(total_new_cost, 2),
            "satis_try": round(total_new_sales, 2),
            "marj": marj,
            "tarih": "2026-09-23",
            "yaslanma_gun": 0,
            "para_birimi": "TRY",
        }

        dash_state = await self.get_state(DashboardState)
        dash_state.raw_quotes.insert(0, yeni_dashboard_satiri)

        yeni_ad = f"{clean_kod} ({self.revizyon_gerekcesi[:25]})"
        VERSIONS_DB[yeni_ad] = {
            "musteri": orijinal_musteri,
            "konu": orijinal_konu,
            "sorumlu": orijinal_sorumlu,
            "items": saved_items,
        }
        self.eski_versiyon_secenekleri = list(VERSIONS_DB.keys())
        self.yeni_versiyon_secenekleri = list(VERSIONS_DB.keys())
        self.secilen_yeni_versiyon = yeni_ad

        return rx.toast.success(
            f"'{clean_kod}' ({orijinal_musteri}) birim fiyat ve miktarlarıyla Dashboard'a aktarıldı!",
            position="top-right"
        )