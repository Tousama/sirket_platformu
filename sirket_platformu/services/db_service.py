import sqlite3
import os
from typing import List, Dict, Any
from datetime import datetime

# Veritabanı yolunu güvenli belirleme
POSSIBLE_PATHS = [
    os.path.abspath("teklifler.db"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "teklifler.db"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "teklifler.db"),
    r"C:\Users\mgune\Desktop\sirket_platformu\teklifler.db",
    r"C:\Users\PetroTek 2\Desktop\sirket_platformu\teklifler.db"
]

DB_PATH = "teklifler.db"
for p in POSSIBLE_PATHS:
    if os.path.exists(p):
        DB_PATH = p
        break


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklifler (
                kod TEXT PRIMARY KEY,
                musteri TEXT,
                musteri_iletisim TEXT,
                konu TEXT,
                teklif_tarihi TEXT,
                sorumlu TEXT,
                satis_toplam REAL DEFAULT 0.0,
                maliyet_toplam REAL DEFAULT 0.0,
                durum TEXT DEFAULT 'Müşteride',
                yaslanma_gun INTEGER DEFAULT 0,
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklif_kalemleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teklif_kodu TEXT NOT NULL,
                malzeme_adi TEXT NOT NULL,
                miktar REAL NOT NULL,
                birim TEXT NOT NULL,
                birim_satis REAL DEFAULT 0.0,
                toplam_tl REAL DEFAULT 0.0,
                para_birimi TEXT DEFAULT 'TRY',
                FOREIGN KEY (teklif_kodu) REFERENCES teklifler (kod) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tedarikci_maliyetleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kalem_id INTEGER NOT NULL,
                teklif_kodu TEXT NOT NULL,
                tedarikci_adi TEXT NOT NULL,
                birim_maliyet REAL NOT NULL,
                para_birimi TEXT DEFAULT 'TRY',
                notlar TEXT,
                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kalem_id) REFERENCES teklif_kalemleri (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teklif_tarihcesi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teklif_kodu TEXT NOT NULL,
                islem_tarihi TEXT NOT NULL,
                olay_durum TEXT NOT NULL,
                guncel_tutar REAL DEFAULT 0.0,
                aciklama TEXT,
                FOREIGN KEY (teklif_kodu) REFERENCES teklifler (kod) ON DELETE CASCADE
            )
        """)
        conn.commit()

    # Mevcut veritabanında 'birim_maliyet' sütunu yoksa güvenle ekle
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE teklif_kalemleri ADD COLUMN birim_maliyet REAL DEFAULT 0.0")
            conn.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tedarikçi maliyet ekleme
# ---------------------------------------------------------------------------
def add_tedarikci_maliyet(teklif_kodu: str, malzeme_adi: str, tedarikci: str, birim_maliyet: float, para_birimi: str = "TRY"):
    """İlgili malzemenin altına tedarikçi fiyatını ekler/günceller."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        kod = str(teklif_kodu).strip().upper()

        cursor.execute("SELECT id FROM teklif_kalemleri WHERE teklif_kodu = ? AND malzeme_adi = ?", (kod, malzeme_adi))
        row = cursor.fetchone()
        if row:
            kalem_id = row["id"]
            cursor.execute("""
                INSERT INTO tedarikci_maliyetleri (kalem_id, teklif_kodu, tedarikci_adi, birim_maliyet, para_birimi)
                VALUES (?, ?, ?, ?, ?)
            """, (kalem_id, kod, tedarikci, birim_maliyet, para_birimi))
            conn.commit()


def update_kalem_maliyet(kalem_id: int, birim_maliyet: float, teklif_kodu: str):
    """Kalemin birim maliyetini günceller ve teklifin toplam maliyetini otomatik yeniden hesaplar."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE teklif_kalemleri
            SET birim_maliyet = ?
            WHERE id = ?
        """, (birim_maliyet, kalem_id))

        cursor.execute("""
            SELECT SUM(miktar * birim_maliyet) as yeni_toplam_maliyet
            FROM teklif_kalemleri
            WHERE teklif_kodu = ?
        """, (teklif_kodu.strip().upper(),))
        row = cursor.fetchone()
        yeni_maliyet = float(row["yeni_toplam_maliyet"] or 0.0) if row else 0.0

        cursor.execute("""
            UPDATE teklifler
            SET maliyet_toplam = ?
            WHERE kod = ?
        """, (yeni_maliyet, teklif_kodu.strip().upper()))

        conn.commit()
        return yeni_maliyet


def update_kalem_satis(kalem_id: int, birim_satis: float, teklif_kodu: str):
    """Kalemin birim satış fiyatını günceller ve teklifin toplam satışını otomatik yeniden hesaplar."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT miktar FROM teklif_kalemleri WHERE id = ?", (kalem_id,))
        row = cursor.fetchone()
        mik = float(row["miktar"] or 1.0) if row else 1.0
        yeni_kalem_toplam = round(mik * birim_satis, 2)

        cursor.execute("""
            UPDATE teklif_kalemleri
            SET birim_satis = ?, toplam_tl = ?
            WHERE id = ?
        """, (birim_satis, yeni_kalem_toplam, kalem_id))

        cursor.execute("""
            SELECT SUM(toplam_tl) as yeni_toplam_satis
            FROM teklif_kalemleri
            WHERE teklif_kodu = ?
        """, (teklif_kodu.strip().upper(),))
        s_row = cursor.fetchone()
        yeni_satis = float(s_row["yeni_toplam_satis"] or 0.0) if s_row else 0.0

        cursor.execute("""
            UPDATE teklifler
            SET satis_toplam = ?
            WHERE kod = ?
        """, (yeni_satis, teklif_kodu.strip().upper()))

        conn.commit()
        return yeni_satis


def upsert_teklif_kalemi(
    teklif_kodu: str,
    malzeme_adi: str,
    miktar: float,
    birim: str,
    birim_satis: float,
    birim_maliyet: float,
    para_birimi: str = "TRY",
) -> Dict[str, float]:
    """Bir teklif kalemini ekler/günceller ve ana teklif toplamlarını yeniler.
    Verilen satış/maliyet değerlerinin TL olması gerekir."""
    init_db()
    kod = str(teklif_kodu).strip().upper()
    ad = str(malzeme_adi).strip()
    mik = float(miktar)
    b_satis = float(birim_satis)
    b_maliyet = float(birim_maliyet)

    if not kod:
        raise ValueError("Teklif kodu boş olamaz.")
    if not ad:
        raise ValueError("Kalem açıklaması boş olamaz.")
    if mik <= 0:
        raise ValueError("Kalem miktarı sıfırdan büyük olmalıdır.")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT durum, satis_toplam, maliyet_toplam FROM teklifler WHERE kod = ?", (kod,))
        teklif = cursor.fetchone()
        if not teklif:
            raise ValueError(f"'{kod}' kodlu teklif bulunamadı.")

        toplam_tl = round(mik * b_satis, 2)
        cursor.execute("""
            SELECT id, toplam_tl, miktar, birim_maliyet
            FROM teklif_kalemleri
            WHERE teklif_kodu = ? AND malzeme_adi = ? COLLATE NOCASE
        """, (kod, ad))
        mevcut = cursor.fetchone()

        if mevcut:
            cursor.execute("""
                UPDATE teklif_kalemleri
                SET miktar = ?, birim = ?, birim_satis = ?, toplam_tl = ?,
                    para_birimi = ?, birim_maliyet = ?
                WHERE id = ?
            """, (mik, birim, b_satis, toplam_tl, para_birimi, b_maliyet, mevcut["id"]))
        else:
            cursor.execute("""
                INSERT INTO teklif_kalemleri
                    (teklif_kodu, malzeme_adi, miktar, birim, birim_satis,
                     toplam_tl, para_birimi, birim_maliyet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (kod, ad, mik, birim, b_satis, toplam_tl, para_birimi, b_maliyet))

        eski_kalem_satis = float(mevcut["toplam_tl"] or 0.0) if mevcut else 0.0
        eski_kalem_maliyet = (
            float(mevcut["miktar"] or 0.0) * float(mevcut["birim_maliyet"] or 0.0)
            if mevcut
            else 0.0
        )
        yeni_satis = round(float(teklif["satis_toplam"] or 0.0) - eski_kalem_satis + toplam_tl, 2)
        yeni_maliyet = round(
            float(teklif["maliyet_toplam"] or 0.0) - eski_kalem_maliyet + (mik * b_maliyet), 2
        )

        cursor.execute("""
            UPDATE teklifler
            SET satis_toplam = ?, maliyet_toplam = ?
            WHERE kod = ?
        """, (yeni_satis, yeni_maliyet, kod))

        cursor.execute("""
            INSERT INTO teklif_tarihcesi
                (teklif_kodu, islem_tarihi, olay_durum, guncel_tutar, aciklama)
            VALUES (?, ?, ?, ?, ?)
        """, (
            kod,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(teklif["durum"] or "Musteride"),
            yeni_satis,
            f"Isçilik kalemi BOM'a eklendi/guncellendi: {ad}",
        ))
        conn.commit()

    return {"satis_toplam": yeni_satis, "maliyet_toplam": yeni_maliyet}


# ---------------------------------------------------------------------------
# Audit Log / Tarihçe
# ---------------------------------------------------------------------------
def add_audit_log(teklif_kodu: str, olay_durum: str, guncel_tutar: float, aciklama: str):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        tarih_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO teklif_tarihcesi (teklif_kodu, islem_tarihi, olay_durum, guncel_tutar, aciklama)
            VALUES (?, ?, ?, ?, ?)
        """, (teklif_kodu.strip().upper(), tarih_str, olay_durum, guncel_tutar, aciklama))
        conn.commit()


def get_audit_logs(teklif_kodu: str) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM teklif_tarihcesi
            WHERE teklif_kodu = ?
            ORDER BY id DESC
        """, (teklif_kodu.strip().upper(),))
        rows = cursor.fetchall()

        sonuclar = []
        for r in rows:
            d = dict(r)
            tutar_num = float(d.get("guncel_tutar", 0.0))
            d["tutar_formatli"] = f"{tutar_num:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
            sonuclar.append(d)
        return sonuclar


def update_teklif_meta(teklif_kodu: str, musteri: str, durum: str, satis: float, maliyet: float, konu: str, aciklama_notu: str = ""):
    init_db()
    kod = teklif_kodu.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE teklifler
            SET musteri = ?, durum = ?, satis_toplam = ?, maliyet_toplam = ?, konu = ?
            WHERE kod = ?
        """, (musteri, durum, satis, maliyet, konu, kod))
        conn.commit()

    log_aciklama = aciklama_notu if aciklama_notu else f"Müşteri: {musteri}, Durum: {durum} olarak güncellendi."
    add_audit_log(kod, durum, satis, log_aciklama)


def delete_teklif_permanently(teklif_kodu: str) -> bool:
    init_db()
    kod = teklif_kodu.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM teklif_tarihcesi WHERE teklif_kodu = ?", (kod,))
        cursor.execute("DELETE FROM tedarikci_maliyetleri WHERE teklif_kodu = ?", (kod,))
        cursor.execute("DELETE FROM teklif_kalemleri WHERE teklif_kodu = ?", (kod,))
        cursor.execute("DELETE FROM teklifler WHERE kod = ?", (kod,))
        conn.commit()
    return True


# ---------------------------------------------------------------------------
# Teklif Kaydetme ve Çekme
# ---------------------------------------------------------------------------
def save_teklif_full(teklif_data: Dict[str, Any], kalemler: List[Dict[str, Any]]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()

        # Hem "kod" hem "teklif_kodu" hem "tarih" hem "teklif_tarihi" desteklenir
        kod = str(teklif_data.get("kod") or teklif_data.get("teklif_kodu") or "").strip().upper()

        # satis_try / satis_toplam / satis hepsini dene
        satis_val = float(
            teklif_data.get("satis_toplam")
            or teklif_data.get("satis_try")
            or teklif_data.get("satis")
            or 0.0
        )
        maliyet_val = float(
            teklif_data.get("maliyet_toplam")
            or teklif_data.get("maliyet_try")
            or teklif_data.get("maliyet")
            or 0.0
        )

        tarih_val = (
            teklif_data.get("teklif_tarihi")
            or teklif_data.get("tarih")
            or "-"
        )

        cursor.execute("""
            INSERT INTO teklifler (kod, musteri, musteri_iletisim, konu, teklif_tarihi, sorumlu, satis_toplam, maliyet_toplam, durum, yaslanma_gun)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(kod) DO UPDATE SET
                musteri=excluded.musteri,
                musteri_iletisim=excluded.musteri_iletisim,
                konu=excluded.konu,
                teklif_tarihi=excluded.teklif_tarihi,
                sorumlu=excluded.sorumlu,
                satis_toplam=excluded.satis_toplam,
                maliyet_toplam=excluded.maliyet_toplam,
                durum=excluded.durum,
                yaslanma_gun=excluded.yaslanma_gun
        """, (
            kod,
            teklif_data.get("musteri", "-"),
            teklif_data.get("musteri_iletisim", ""),
            teklif_data.get("konu", "-"),
            tarih_val,
            teklif_data.get("sorumlu", "-"),
            satis_val,
            maliyet_val,
            teklif_data.get("durum", "Müşteride"),
            int(teklif_data.get("yaslanma_gun", 0)),
        ))

        cursor.execute("DELETE FROM teklif_kalemleri WHERE teklif_kodu = ?", (kod,))

        for k in (kalemler or []):
            ad = k.get("malzeme_adi") or k.get("tanim") or k.get("malzeme") or "Tanımsız Kalem"
            mik = float(k.get("miktar", 1.0))
            birim = str(k.get("birim", "Adet"))
            b_fiyat = float(k.get("birim_satis") or k.get("birim_fiyat") or 0.0)
            # Önemli: toplam TL değeri. Önce tutar_tl/toplam_tl, yoksa hesapla.
            tutar = float(k.get("tutar_tl") or k.get("toplam_tl") or (mik * b_fiyat))
            pb = str(k.get("para_birimi", "TRY"))
            b_maliyet = float(k.get("birim_maliyet") or 0.0)

            cursor.execute("""
                INSERT INTO teklif_kalemleri
                    (teklif_kodu, malzeme_adi, miktar, birim, birim_satis,
                     toplam_tl, para_birimi, birim_maliyet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (kod, ad, mik, birim, b_fiyat, tutar, pb, b_maliyet))

        conn.commit()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM teklif_tarihcesi WHERE teklif_kodu = ?", (kod,))
        if not cursor.fetchone():
            add_audit_log(kod, teklif_data.get("durum", "Müşteride"), satis_val, "Teklif portföye kaydedildi.")


def save_teklif_to_db(teklif_data=None, **kwargs):
    """
    İki farklı çağrı şeklini destekler:
      1) save_teklif_to_db({"kod": ..., "kalemler": [...]})
      2) save_teklif_to_db(kod=..., musteri=..., kalemler=[...])
    """
    if teklif_data is None:
        teklif_data = kwargs
    elif kwargs:
        teklif_data = {**teklif_data, **kwargs}

    if not isinstance(teklif_data, dict):
        return

    kalemler = teklif_data.get("kalemler", [])
    save_teklif_full(teklif_data, kalemler)


def get_all_teklifler_from_db() -> List[Dict[str, Any]]:
    """
    Tüm teklifleri getirir. Satış/maliyet toplamlarını,
    güvenilir kaynak olan kalemler üzerinden yeniden hesaplar.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teklifler ORDER BY olusturma_tarihi DESC")
        teklif_rows = cursor.fetchall()

        sonuc = []
        for t in teklif_rows:
            t_dict = dict(t)
            kod = t_dict["kod"]

            cursor.execute("SELECT * FROM teklif_kalemleri WHERE teklif_kodu = ?", (kod,))
            kalem_rows = cursor.fetchall()
            kalemler_list = [dict(k) for k in kalem_rows]
            t_dict["kalemler"] = kalemler_list

            # --- KRİTİK: Toplamları kalemlerden yeniden hesapla ---
            hesaplanan_satis = 0.0
            hesaplanan_maliyet = 0.0
            for k in kalemler_list:
                mik = float(k.get("miktar", 0.0) or 0.0)
                toplam_tl = float(k.get("toplam_tl", 0.0) or 0.0)
                b_maliyet = float(k.get("birim_maliyet", 0.0) or 0.0)
                hesaplanan_satis += toplam_tl
                hesaplanan_maliyet += mik * b_maliyet

            if kalemler_list:
                t_dict["satis_toplam"] = round(hesaplanan_satis, 2)
                t_dict["maliyet_toplam"] = round(hesaplanan_maliyet, 2)
            else:
                t_dict["satis_toplam"] = float(t_dict.get("satis_toplam") or 0.0)
                t_dict["maliyet_toplam"] = float(t_dict.get("maliyet_toplam") or 0.0)

            t_dict["satis_try"] = t_dict["satis_toplam"]
            t_dict["maliyet_try"] = t_dict["maliyet_toplam"]

            sonuc.append(t_dict)

        return sonuc


def get_teklif_by_kod(kod: str) -> Dict[str, Any]:
    teklifler = get_all_teklifler_from_db()
    for t in teklifler:
        if t.get("kod") == kod or t.get("teklif_kodu") == kod:
            return t
    return {}


# ---------------------------------------------------------------------------
# Mühendis Yönetimi
# ---------------------------------------------------------------------------
def init_muhendisler():
    """Mühendisler tablosunu kurar ve varsayılan ekibi yükler."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS muhendisler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad TEXT NOT NULL,
                unvan TEXT NOT NULL,
                olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cursor.execute("SELECT COUNT(*) as sayi FROM muhendisler")
        if cursor.fetchone()["sayi"] == 0:
            varsayilanlar = [
                ("Muhammed Güner", "Elektrik-Elektronik Mühendisi"),
                ("Cengiz Doğan", "Elektrik Elektronik Mühendisi"),
                ("Mert EDİS", "Elektrik-Elektronik Mühendisi"),
                ("Uğur Sakar", "Makine Mühendisi"),
                ("Serdar Kaan Gür", "Elektrik Elektronik Mühendisi"),
            ]
            cursor.executemany(
                "INSERT INTO muhendisler (ad_soyad, unvan) VALUES (?, ?)",
                varsayilanlar,
            )
            conn.commit()


def get_all_muhendisler() -> List[Dict[str, Any]]:
    init_muhendisler()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ad_soyad, unvan FROM muhendisler ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]


def add_muhendis(ad_soyad: str, unvan: str):
    init_muhendisler()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO muhendisler (ad_soyad, unvan) VALUES (?, ?)",
            (ad_soyad.strip(), unvan.strip()),
        )
        conn.commit()


def delete_muhendis(muhendis_id: int):
    init_muhendisler()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM muhendisler WHERE id = ?", (muhendis_id,))
        conn.commit()