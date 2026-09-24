import reflex as rx
from typing import List, Dict, Any
import re
from .dashboard_state import DashboardState
from .shared_quotes import SHARED_QUOTES

try:
    from .services.db_service import get_all_teklifler_from_db
except ImportError:
    try:
        from services.db_service import get_all_teklifler_from_db
    except ImportError:
        get_all_teklifler_from_db = None

# Geriye dönük uyumluluk için sözlük tanımlı bırakılır, ancak içerik dinamik doldurulur
VERSIONS_DB: Dict[str, Dict[str, Any]] = {}


class RevisionDiffState(rx.State):
    eski_versiyon_secenekleri: List[str] = []
    secilen_eski_versiyon: str = ""

    yeni_versiyon_secenekleri: List[str] = []
    secilen_yeni_versiyon: str = ""

    yeni_revizyon_kodu: str = ""
    revizyon_gerekcesi: str = "Kalem bazlı birim fiyat ve kapsam düzenlemesi"

    toplam_maliyet_str: str = "0,00 ₺"
    maliyet_fark_str: str = "0,00 ₺ (Aynı)"

    toplam_satis_str: str = "0,00 ₺"
    satis_fark_str: str = "0,00 ₺ (Aynı)"

    kar_marji_str: str = "%0.0"
    marj_fark_str: str = "%0.0 (Aynı)"

    diff_items: List[Dict[str, Any]] = []
    has_revisions: bool = False

    async def on_load_recompute(self):
        """DashboardState ve DB'deki gerçek teklifleri tarar; sadece revizyonu olanları listeler."""
        await self._sync_versions_from_data_source()
        self._calculate_diff()

    async def _sync_versions_from_data_source(self):
        dash_state = await self.get_state(DashboardState)
        raw_list = getattr(dash_state, "raw_quotes", [])

        pool = {}
        if raw_list:
            for q in raw_list:
                kod = q.get("kod") or q.get("teklif_kodu", "")
                if kod:
                    pool[kod] = q

        if get_all_teklifler_from_db:
            try:
                db_quotes = get_all_teklifler_from_db()
                for q in db_quotes:
                    kod = q.get("kod") or q.get("teklif_kodu", "")
                    if kod and kod not in pool:
                        pool[kod] = q
            except Exception:
                pass

        # Teklifleri kök koduna göre grupla (Örn: PT202600153 ve PT202600153-Rev1)
        root_groups: Dict[str, List[Dict[str, Any]]] = {}
        for kod, q in pool.items():
            root_code = re.split(r"[-_\s]?(?:rev|r)\d*", kod, flags=re.IGNORECASE)[0].strip()
            if root_code not in root_groups:
                root_groups[root_code] = []
            root_groups[root_code].append(q)

        # Sadece revizyonlu (en az 2 versiyonu olan) teklifleri VERSIONS_DB formatına aktar
        VERSIONS_DB.clear()
        for root_code, q_list in root_groups.items():
            if len(q_list) >= 2:
                for q in q_list:
                    kod = q.get("kod") or q.get("teklif_kodu", "")
                    kalemler = q.get("kalemler", [])
                    if not kalemler and kod in SHARED_QUOTES:
                        kalemler = SHARED_QUOTES[kod].get("kalemler", [])

                    items_dict = {}
                    for k in kalemler:
                        mat_name = str(k.get("malzeme_adi") or k.get("tanim") or "Tanımsız Kalem")
                        items_dict[mat_name] = {
                            "miktar": float(k.get("miktar", 1.0)),
                            "birim": str(k.get("birim", "Adet")),
                            "birim_maliyet": float(k.get("birim_maliyet", 0.0)),
                            "birim_satis": float(k.get("birim_satis") or k.get("birim_fiyat") or 0.0),
                        }

                    # Kalem detayları yoksa ana toplamlar üzerinden tek kalem oluştur
                    if not items_dict:
                        items_dict[q.get("konu", "Genel Kapsam")] = {
                            "miktar": 1.0,
                            "birim": "Set",
                            "birim_maliyet": float(q.get("maliyet_try", 0.0)),
                            "birim_satis": float(q.get("satis_try") or q.get("satis_orijinal") or 0.0),
                        }

                    VERSIONS_DB[kod] = {
                        "musteri": q.get("musteri", "-"),
                        "konu": q.get("konu", "-"),
                        "sorumlu": q.get("sorumlu", "-"),
                        "items": items_dict,
                    }

        all_keys = list(VERSIONS_DB.keys())
        if len(all_keys) >= 2:
            self.eski_versiyon_secenekleri = all_keys
            self.yeni_versiyon_secenekleri = all_keys
            if self.secilen_eski_versiyon not in all_keys:
                self.secilen_eski_versiyon = all_keys[0]
            if self.secilen_yeni_versiyon not in all_keys:
                self.secilen_yeni_versiyon = all_keys[1]
            self.has_revisions = True
            base_clean = re.split(r"[-_\s]?(?:rev|r)\d*", self.secilen_eski_versiyon, flags=re.IGNORECASE)[0].strip()
            self.yeni_revizyon_kodu = f"{base_clean}-Rev{len(all_keys)}"
        else:
            self.eski_versiyon_secenekleri = []
            self.yeni_versiyon_secenekleri = []
            self.secilen_eski_versiyon = ""
            self.secilen_yeni_versiyon = ""
            self.diff_items = []
            self.has_revisions = False
            self.toplam_maliyet_str = "0,00 ₺"
            self.toplam_satis_str = "0,00 ₺"
            self.kar_marji_str = "%0.0"
            self.maliyet_fark_str = "0,00 ₺ (Aynı)"
            self.satis_fark_str = "0,00 ₺ (Aynı)"
            self.marj_fark_str = "%0.0 (Aynı)"

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
        if not self.has_revisions:
            return

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
                "eski_miktar": f"{int(eski_miktar) if eski_miktar.is_integer() else eski_miktar} {old_item['birim']}",
                "yeni_miktar": str(int(yeni_miktar)) if yeni_miktar.is_integer() else str(yeni_miktar),
                "eski_birim_satis": f"{eski_birim_satis:,.2f}",
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
        try:
            new_qty = float(val) if val.strip() else 0.0
        except ValueError:
            new_qty = 0.0

        for row in self.diff_items:
            if row["malzeme"] == malzeme:
                row["yeni_miktar"] = str(int(new_qty)) if new_qty.is_integer() else str(new_qty)
                unit_price = float(row.get("yeni_birim_satis_num", 0.0))

                new_total_sales = round(new_qty * unit_price, 2)
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

    def update_item_unit_price(self, malzeme: str, val: str):
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

        c_old = sum(float(it.get("birim_maliyet", 0.0)) * float(it.get("miktar", 1.0)) for it in v_old.get("items", {}).values())
        s_old = sum(float(it.get("birim_satis", 0.0)) * float(it.get("miktar", 1.0)) for it in v_old.get("items", {}).values())

        total_new_cost = 0.0
        for row in self.diff_items:
            try:
                q = float(row.get("yeni_miktar", 0.0))
            except ValueError:
                q = 0.0
            total_new_cost += q * float(row.get("birim_maliyet", 0.0))

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

        orijinal_musteri = v_base.get("musteri", "-")
        orijinal_konu = v_base.get("konu", "İş Kapsamı")
        orijinal_sorumlu = v_base.get("sorumlu", "Teknik Departman")

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
            "tarih": "2026-09-24",
            "yaslanma_gun": 0,
            "para_birimi": "TRY",
        }

        dash_state = await self.get_state(DashboardState)
        dash_state.raw_quotes.insert(0, yeni_dashboard_satiri)

        VERSIONS_DB[clean_kod] = {
            "musteri": orijinal_musteri,
            "konu": orijinal_konu,
            "sorumlu": orijinal_sorumlu,
            "items": saved_items,
        }
        self.eski_versiyon_secenekleri = list(VERSIONS_DB.keys())
        self.yeni_versiyon_secenekleri = list(VERSIONS_DB.keys())
        self.secilen_yeni_versiyon = clean_kod

        return rx.toast.success(
            f"'{clean_kod}' revizyonu Dashboard'a aktarıldı!",
            position="top-right"
        )