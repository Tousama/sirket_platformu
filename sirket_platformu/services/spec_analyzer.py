import io
import re
from typing import Any, Dict
import pdfplumber


def extract_text_from_file(file_obj) -> str:
  """PDF veya text tabanlı dosyalardan ham metni çıkarır."""
  if isinstance(file_obj, bytes):
    stream = io.BytesIO(file_obj)
  else:
    stream = file_obj

  text = ""
  try:
    with pdfplumber.open(stream) as pdf:
      for page in pdf.pages:
        t = page.extract_text(layout=False) or ""
        text += t + "\n"
  except Exception:
    pass
  return text


def analyze_technical_specification(file_obj, filename: str = "") -> Dict[str, Any]:
  raw_text = extract_text_from_file(file_obj)
  if not raw_text:
    return {}

  lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

  # 1. Kurum / İdare Tespiti
  kurum = "Sayın Yetkili"
  for line in lines[:20]:
    if any(k in line.upper() for k in ["GENEL MÜDÜRLÜĞÜ", "İŞLETME MÜDÜRLÜĞÜ", "A.Ş.", "DAİRESİ"]):
      kurum = line.title()
      break

  # 2. Şartname Konusu / Referans No
  konu = ""
  for i, line in enumerate(lines[:30]):
    if any(k in line.upper() for k in ["TEKNİK ŞARTNAMESİ", "BAKIM HİZMETİ", "HİZMETİ ALIMI"]):
      konu = line
      break
    if line.upper().startswith("1. KONU") or line.upper().startswith("KONU"):
      if i + 1 < len(lines):
        konu = lines[i + 1]
      break

  if not konu:
    konu = filename.replace(".pdf", "").replace("_", " ").title()

  # 3. İş Türü Tespiti (Servis/Bakım mı yoksa Malzeme Temini mi?)
  is_bakim_servis = any(
      k in raw_text.lower()
      for k in ["bakım", "dcs", "arıza", "servis", "scada", "periyodik", "uzaktan bağlantı", "onarım"]
  )

  # 4. Kapsam Maddelerini Şartnameden Cımbızlama
  is_kapsami_maddeleri = []
  haricler = []
  isveren_sorumluluklari = []

  # Bakım işi ise şartnamedeki gerçek maddeleri çek:
  if is_bakim_servis:
    # GE&Nexus / DCS Donanımları tespiti
    if "ge&nexus" in raw_text.lower() or "kontrol panel" in raw_text.lower():
      is_kapsami_maddeleri.append(
          "GE&NEXUS DCS Kontrol Paneli (MPU, MDI, MDO, MAI modülleri) ve endüstriyel haberleşme altyapısının periyodik genel bakımı."
      )

    # 5 gün yerinde bakım kuralı
    m_gun = re.search(r"(\d+)\s*(?:iş\s*)?günü\s*içerisinde\s*tamamlanacak", raw_text, re.IGNORECASE)
    if m_gun or "5 (beş) iş günü" in raw_text or "ulaşım süresi (1 gün) de dahil" in raw_text:
      is_kapsami_maddeleri.append(
          "Yılda 1 defa tesiste yerinde genel bakım; sunucu, iş istasyonu ve PLC/DCS program yedeklerinin alınması (Ulaşım dahil 5 iş günü)."
      )

    # Uzaktan bağlantı desteği
    if "uzaktan" in raw_text.lower():
      m_saat = re.search(r"(\d+)\s*saatlik\s*süreyi\s*aşmamak", raw_text)
      saat_str = f"toplam {m_saat.group(1)} saat" if m_saat else "10 saat"
      is_kapsami_maddeleri.append(
          f"Yıl boyunca arıza müdahale ve yazılım revizyonları için {saat_str} uzaktan servis desteği verilmesi (En geç 8 saatte bağlantı)."
      )

    # Acil yerinde servis
    if "48 (kırk sekiz) saat" in raw_text or "48 saat" in raw_text:
      is_kapsami_maddeleri.append(
          "Uzaktan giderilemeyen kritik arızalarda yazılı çağrıya istinaden en geç 48 saat içerisinde sahada yerinde müdahale sağlanması."
      )

    # Scada ve revizyon
    if "revizyon" in raw_text.lower() or "scada" in raw_text.lower():
      is_kapsami_maddeleri.append(
          "İdarenin talebi doğrultusunda DCS lojik program ve SCADA ekranlarında gerekli ilave, çıkarma ve optimizasyon revizyonlarının yapılması."
      )

    # 10. Madde: Kapsam Dışı Hususlar
    if "10. sözleşme kapsamına girmeyen" in raw_text.lower() or "kapsamaz" in raw_text.lower():
      haricler.append("DCS sistemi haricindeki harici elektrik tesisatı, şebeke ve saha besleme arızaları.")
      haricler.append("Saha enstrümanları (transmitter, kontrol vanası, seviye şalteri vb.) mekanik ve kalibrasyon bakımları.")
      haricler.append("DCS sistemi çalışması için gerekli harici sarf malzemeleri (yazıcı şeridi, sürekli form vb.) temini.")
      haricler.append("İdarenin temin etmesi gereken arızalı kart, modül, gateway ve switch donanımlarının malzeme bedelleri.")

    # İşveren Sorumlulukları
    isveren_sorumluluklari.append("DCS program yedeklerinin alınabilmesi için gerekli lisanslı yazılımların ve harici disklerin temini.")
    isveren_sorumluluklari.append("Uzaktan erişim oturumları için güvenli internet ve VPN/uzaktan bağlantı altyapısının hazır edilmesi.")
    isveren_sorumluluklari.append("Değişmesi gereken arızalı kart ve donanımların idare tarafından temin edilmesi.")
    isveren_sorumluluklari.append("Genel bakım çalışması için en az 3 (üç) hafta öncesinden yükleniciye yazılı bildirim yapılması.")

  else:
    # Malzeme Temini İşi İse
    is_kapsami_maddeleri = [
        "Şartname teknik kriterlerine ve talep edilen ATEX/IECEx koruma sınıflarına haiz cihaz temini.",
        "EN 10204 3.1 Malzeme İzlenebilirlik ve Fabrika Kalibrasyon Test Sertifikalarının teslimi.",
        "Ekipmanların nakliye sigortalı (DAP/CIP) olarak tesis sahasına güvenli teslimatı.",
    ]
    isveren_sorumluluklari = [
        "Malzemelerin şantiye sahasında teslim alınması, uygun kapalı depolama koşullarının sağlanması.",
        "Malzeme muayene ve kabul protokollerinin şartname takvimine uygun imzalanması.",
    ]
    haricler = [
        "Sahada mekanik ve elektriksel montaj, kablolama ve sonlandırma işçilikleri.",
        "Saha loop testleri, enerji verme ve devreye alma hizmetleri.",
    ]

  # Giriş Yazısı
  giris_yazisi = (
      f"İşbu teknik teklif dokümanı; {kurum} bünyesinde bulunan 30 t/h Buhar Kazanına ait GE&NEXUS DCS Kontrol Sisteminin "
      "1 (bir) yıllık periyodik bakım, uzaktan destek ve acil servis hizmetlerinin teknik şartnameye tam uygun olarak yürütülmesini kapsamaktadır."
      if is_bakim_servis
      else f"İşbu teknik teklif dokümanı; {kurum} tarafından talep edilen şartname föylerine uygun enstrümanların temin ve teslimini kapsamaktadır."
  )

  return {
      "kurum": kurum,
      "konu": konu,
      "giris_yazisi": giris_yazisi,
      "is_kapsami": "\n• ".join([""] + is_kapsami_maddeleri).strip(),
      "isveren_sorumluluklari": "\n• ".join([""] + isveren_sorumluluklari).strip(),
      "haric_tutulanlar": "\n• ".join([""] + haricler).strip(),
      "is_turu": "DCS & Otomasyon Yıllık Bakım Hizmeti" if is_bakim_servis else "Endüstriyel Enstrüman & Malzeme Temini",
  }