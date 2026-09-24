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


# Mevcut veritabanında 'birim_maliyet' sütunu henüz yoksa güvenle ekler
    try:
        cursor.execute("ALTER TABLE teklif_kalemleri ADD COLUMN birim_maliyet REAL DEFAULT 0.0")
        conn.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# shared_quotes.py tarafından çağrılan kritik tedarikçi maliyet ekleme fonksiyonu
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
        
        # 1. Kalemin birim maliyetini güncelle
        cursor.execute("""
            UPDATE teklif_kalemleri
            SET birim_maliyet = ?
            WHERE id = ?
        """, (birim_maliyet, kalem_id))
        
        # 2. Teklifin toplam maliyetini kalemler üzerinden hesapla: SUM(miktar * birim_maliyet)
        cursor.execute("""
            SELECT SUM(miktar * birim_maliyet) as yeni_toplam_maliyet
            FROM teklif_kalemleri
            WHERE teklif_kodu = ?
        """, (teklif_kodu.strip().upper(),))
        row = cursor.fetchone()
        yeni_maliyet = float(row["yeni_toplam_maliyet"] or 0.0) if row else 0.0
        
        # 3. Ana teklif tablosunu güncelle
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
        
        # 1. Kalemin birim satışını ve toplam tutarını güncelle
        cursor.execute("SELECT miktar FROM teklif_kalemleri WHERE id = ?", (kalem_id,))
        row = cursor.fetchone()
        mik = float(row["miktar"] or 1.0) if row else 1.0
        yeni_kalem_toplam = round(mik * birim_satis, 2)

        cursor.execute("""
            UPDATE teklif_kalemleri
            SET birim_satis = ?, toplam_tl = ?
            WHERE id = ?
        """, (birim_satis, yeni_kalem_toplam, kalem_id))
        
        # 2. Teklifin toplam satışını tüm kalemler üzerinden hesapla: SUM(toplam_tl)
        cursor.execute("""
            SELECT SUM(toplam_tl) as yeni_toplam_satis
            FROM teklif_kalemleri
            WHERE teklif_kodu = ?
        """, (teklif_kodu.strip().upper(),))
        s_row = cursor.fetchone()
        yeni_satis = float(s_row["yeni_toplam_satis"] or 0.0) if s_row else 0.0
        
        # 3. Ana teklif tablosunu güncelle
        cursor.execute("""
            UPDATE teklifler
            SET satis_toplam = ?
            WHERE kod = ?
        """, (yeni_satis, teklif_kodu.strip().upper()))
        
        conn.commit()
        return yeni_satis


# ---------------------------------------------------------------------------
# Audit Log / Tarihçe Fonksiyonları
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
# Teklif Kaydetme ve Çekme Fonksiyonları
# ---------------------------------------------------------------------------
def save_teklif_full(teklif_data: Dict[str, Any], kalemler: List[Dict[str, Any]]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        kod = str(teklif_data.get("kod") or teklif_data.get("teklif_kodu") or "").strip().upper()

        satis_val = float(teklif_data.get("satis_toplam") or teklif_data.get("satis_try") or teklif_data.get("satis") or 0.0)
        maliyet_val = float(teklif_data.get("maliyet_toplam") or teklif_data.get("maliyet_try") or teklif_data.get("maliyet") or 0.0)

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
            teklif_data.get("teklif_tarihi", "-"),
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
            tutar = float(k.get("tutar_tl") or k.get("toplam_tl") or (mik * b_fiyat))
            pb = str(k.get("para_birimi", "TRY"))

            cursor.execute("""
                INSERT INTO teklif_kalemleri (teklif_kodu, malzeme_adi, miktar, birim, birim_satis, toplam_tl, para_birimi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (kod, ad, mik, birim, b_fiyat, tutar, pb))

        conn.commit()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM teklif_tarihcesi WHERE teklif_kodu = ?", (kod,))
        if not cursor.fetchone():
            add_audit_log(kod, teklif_data.get("durum", "Müşteride"), satis_val, "Teklif portföye kaydedildi.")


def save_teklif_to_db(teklif_data: Dict[str, Any]):
    kalemler = teklif_data.get("kalemler", [])
    save_teklif_full(teklif_data, kalemler)


def get_all_teklifler_from_db() -> List[Dict[str, Any]]:
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
            t_dict["kalemler"] = [dict(k) for k in kalem_rows]

            s_val = float(t_dict.get("satis_toplam") or 0.0)
            m_val = float(t_dict.get("maliyet_toplam") or 0.0)

            t_dict["satis_try"] = s_val
            t_dict["maliyet_try"] = m_val

            sonuc.append(t_dict)
            
        return sonuc


def get_teklif_by_kod(kod: str) -> Dict[str, Any]:
    teklifler = get_all_teklifler_from_db()
    for t in teklifler:
        if t.get("kod") == kod or t.get("teklif_kodu") == kod:
            return t
    return {}

#---------------------------------------------------#
#        Mühendis Ekleme ve Çıkarma Fonk.           #
#---------------------------------------------------#


def init_muhendisler():
  """Mühendisler tablosunu kurar ve görseldeki varsayılan ekibi yükler."""
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

    # Tablo boşsa görseldeki 5 mühendisi başlangıç olarak ekle
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