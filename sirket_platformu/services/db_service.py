import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = "teklifler.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Tabloları ve ilişkileri oluşturur."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Teklifler Tablosu
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

        # 2. Teklif Kalemleri Tablosu
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

        # 3. Tedarikçi Maliyet / Fiyat Teklifleri Tablosu
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
        conn.commit()

# --- VERİ YAZMA / OKUMA METOTLARI ---

def save_teklif_full(teklif_data: Dict[str, Any], kalemler: List[Dict[str, Any]]):
    """Teklifi ve tüm kalemlerini atomik (transaction) olarak kaydeder."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        kod = teklif_data["kod"].strip().upper()

        # Teklif varsa güncelle, yoksa ekle
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
            teklif_data.get("musteri", ""),
            teklif_data.get("musteri_iletisim", ""),
            teklif_data.get("konu", ""),
            teklif_data.get("teklif_tarihi", ""),
            teklif_data.get("sorumlu", ""),
            float(teklif_data.get("satis_try", 0.0)),
            float(teklif_data.get("maliyet_try", 0.0)),
            teklif_data.get("durum", "Müşteride"),
            int(teklif_data.get("yaslanma_gun", 0)),
        ))

        # Önceki kalemleri temizle (güncelleme senaryosu)
        cursor.execute("DELETE FROM teklif_kalemleri WHERE teklif_kodu = ?", (kod,))

        # Kalemleri ekle
        for k in kalemler:
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

def add_tedarikci_maliyet(teklif_kodu: str, malzeme_adi: str, tedarikci: str, birim_maliyet: float, para_birimi: str = "TRY"):
    """İlgili malzemenin altına tedarikçi fiyatını kaydeder."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        kod = teklif_kodu.strip().upper()

        # İlgili kalemin ID'sini bul
        cursor.execute("SELECT id FROM teklif_kalemleri WHERE teklif_kodu = ? AND malzeme_adi = ?", (kod, malzeme_adi))
        row = cursor.fetchone()
        if row:
            kalem_id = row["id"]
            cursor.execute("""
                INSERT INTO tedarikci_maliyetleri (kalem_id, teklif_kodu, tedarikci_adi, birim_maliyet, para_birimi)
                VALUES (?, ?, ?, ?, ?)
            """, (kalem_id, kod, tedarikci, birim_maliyet, para_birimi))
            conn.commit()

def get_all_teklifler_from_db() -> List[Dict[str, Any]]:
    """Dashboard ve listeleme ekranları için tüm teklifleri ve kalemlerini çeker."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teklifler ORDER BY olusturma_tarihi DESC")
        teklif_rows = cursor.fetchall()
        
        sonuc = []
        for t in teklif_rows:
            t_dict = dict(t)
            kod = t_dict["kod"]

            # Kalemleri ve tedarikçi fiyatlarını çek
            cursor.execute("SELECT * FROM teklif_kalemleri WHERE teklif_kodu = ?", (kod,))
            kalem_rows = cursor.fetchall()
            
            kalem_listesi = []
            for k in kalem_rows:
                k_dict = dict(k)
                
                # Bu kaleme ait tedarikçi fiyatları
                cursor.execute("SELECT tedarikci_adi, birim_maliyet FROM tedarikci_maliyetleri WHERE kalem_id = ?", (k_dict["id"],))
                ted_rows = cursor.fetchall()
                fiyatlar = {r["tedarikci_adi"]: r["birim_maliyet"] for r in ted_rows}
                k_dict["fiyatlar"] = fiyatlar
                kalem_listesi.append(k_dict)

            t_dict["kalemler"] = kalem_listesi
            sonuc.append(t_dict)
            
        return sonuc
    
    
def get_teklif_by_kod(kod: str) -> Dict[str, Any]:
    """Belirtilen koda ait teklif kaydını döndürür."""
    teklifler = get_all_teklifler_from_db()
    for t in teklifler:
        if t.get("kod") == kod or t.get("teklif_kodu") == kod:
            return t
    return {}


def save_teklif_to_db(teklif_data: Dict[str, Any]):
    """Teklifi veritabanında günceller veya yoksa yeni kayıt olarak ekler."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    kod = teklif_data.get("kod") or teklif_data.get("teklif_kodu")
    musteri = teklif_data.get("musteri", "")
    konu = teklif_data.get("konu", "")
    sorumlu = teklif_data.get("sorumlu", "")
    tarih = teklif_data.get("teklif_tarihi", "")
    durum = teklif_data.get("durum", "Müşteride")
    yaslanma = int(teklif_data.get("yaslanma_gun", 0))
    satis_try = float(teklif_data.get("satis_try", 0.0) or teklif_data.get("satis_toplam", 0.0))
    maliyet_try = float(teklif_data.get("maliyet_try", 0.0) or teklif_data.get("maliyet_toplam", 0.0))
    kalemler_json = json.dumps(teklif_data.get("kalemler", []), ensure_ascii=False)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teklifler (
            kod TEXT PRIMARY KEY,
            musteri TEXT,
            konu TEXT,
            sorumlu TEXT,
            teklif_tarihi TEXT,
            durum TEXT,
            yaslanma_gun INTEGER,
            satis_try REAL,
            maliyet_try REAL,
            kalemler TEXT
        )
    """)

    cursor.execute("""
        INSERT INTO teklifler (kod, musteri, konu, sorumlu, teklif_tarihi, durum, yaslanma_gun, satis_try, maliyet_try, kalemler)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kod) DO UPDATE SET
            musteri=excluded.musteri,
            konu=excluded.konu,
            sorumlu=excluded.sorumlu,
            teklif_tarihi=excluded.teklif_tarihi,
            durum=excluded.durum,
            yaslanma_gun=excluded.yaslanma_gun,
            satis_try=excluded.satis_try,
            maliyet_try=excluded.maliyet_try,
            kalemler=excluded.kalemler
    """, (kod, musteri, konu, sorumlu, tarih, durum, yaslanma, satis_try, maliyet_try, kalemler_json))

    conn.commit()
    conn.close()