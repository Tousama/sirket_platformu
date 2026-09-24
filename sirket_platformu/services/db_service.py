import sqlite3
import os
from typing import List, Dict, Any

# Mutlak yol: Proje kök dizinindeki teklifler.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "teklifler.db")

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
        conn.commit()

        # shared_quotes içerisindeki mevcut portföyü veritabanına otomatik taşı
        try:
            from ..shared_quotes import SHARED_QUOTES
            for k, q_data in SHARED_QUOTES.items():
                if isinstance(q_data, dict):
                    kod = str(q_data.get("kod") or q_data.get("teklif_kodu") or k).strip().upper()
                    cursor.execute("SELECT kod FROM teklifler WHERE kod = ?", (kod,))
                    if not cursor.fetchone():
                        s_val = float(q_data.get("satis_toplam") or q_data.get("satis_try") or q_data.get("satis") or 0.0)
                        m_val = float(q_data.get("maliyet_toplam") or q_data.get("maliyet_try") or q_data.get("maliyet") or 0.0)
                        cursor.execute("""
                            INSERT INTO teklifler (kod, musteri, musteri_iletisim, konu, teklif_tarihi, sorumlu, satis_toplam, maliyet_toplam, durum, yaslanma_gun)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            kod,
                            str(q_data.get("musteri", "-")),
                            str(q_data.get("musteri_iletisim", "")),
                            str(q_data.get("konu", "-")),
                            str(q_data.get("teklif_tarihi") or q_data.get("tarih") or "-"),
                            str(q_data.get("sorumlu", "Muhammed GÜNER")),
                            s_val,
                            m_val,
                            str(q_data.get("durum", "Müşteride")),
                            int(q_data.get("yaslanma_gun", 0))
                        ))
            conn.commit()
        except Exception:
            pass


def save_teklif_full(teklif_data: Dict[str, Any], kalemler: List[Dict[str, Any]]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        kod = str(teklif_data.get("kod") or teklif_data.get("teklif_kodu") or "").strip().upper()

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


def add_tedarikci_maliyet(teklif_kodu: str, malzeme_adi: str, tedarikci: str, birim_maliyet: float, para_birimi: str = "TRY"):
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