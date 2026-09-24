import re
from typing import Dict, Any, List

class SpecAnalyzerEngine:
    """
    Teknik şartname metinlerini ayrıştıran ve cihaz özellikleri ile
    kural tabanlı karşılaştıran analiz motoru.
    """

    @staticmethod
    def extract_spec_parameters(raw_text: str) -> Dict[str, Any]:
        params = {
            "ip_rating": None,
            "is_atex_required": False,
            "atex_zone": None,
            "gas_group": None,
            "temp_class": None,
            "max_ambient_temp": None,
            "min_ambient_temp": None,
            "voltage": None,
            "protocol": None,
            "body_material": None,
        }

        if not raw_text:
            return params

        # IP Koruma Seviyesi Tespiti (Örn: IP65, IP 66, IP67, IP68)
        ip_match = re.search(r"\bIP\s?([0-9]{2})\b", raw_text, re.IGNORECASE)
        if ip_match:
            params["ip_rating"] = int(ip_match.group(1))

        # ATEX / Ex-Proof Gereksinimi
        if re.search(r"\b(atex|ex-proof|ex\s?proof|patlayıcı\s?ortam|ex\s?ia|ex\s?d)\b", raw_text, re.IGNORECASE):
            params["is_atex_required"] = True
            
            zone_match = re.search(r"\b(zone\s?[0-2]|zon\s?[0-2])\b", raw_text, re.IGNORECASE)
            params["atex_zone"] = zone_match.group(0).upper() if zone_match else "Zone 1"

            gas_match = re.search(r"\b(IIC|IIB|IIA)\b", raw_text, re.IGNORECASE)
            params["gas_group"] = gas_match.group(1).upper() if gas_match else "IIC"

            temp_cls = re.search(r"\b(T[1-6])\b", raw_text)
            params["temp_class"] = temp_cls.group(1).upper() if temp_cls else "T4"

        # Çalışma Sıcaklıkları
        temp_range_match = re.search(r"(-?\d{1,2})\s*(?:\.\.|ila|-|\/)\s*\+?(\d{2,3})\s*°?C", raw_text, re.IGNORECASE)
        if temp_range_match:
            params["min_ambient_temp"] = int(temp_range_match.group(1))
            params["max_ambient_temp"] = int(temp_range_match.group(2))
        else:
            single_temp_match = re.search(r"(\+?\d{2})\s*(?:°?C|derece)", raw_text, re.IGNORECASE)
            if single_temp_match:
                params["max_ambient_temp"] = int(single_temp_match.group(1))

        # Besleme Gerilimi
        if re.search(r"\b24\s*V(?:DC)?\b", raw_text, re.IGNORECASE):
            params["voltage"] = "24VDC"
        elif re.search(r"\b(?:220|230)\s*V(?:AC)?\b", raw_text, re.IGNORECASE):
            params["voltage"] = "230VAC"
        elif re.search(r"\b(?:380|400)\s*V(?:AC)?\b", raw_text, re.IGNORECASE):
            params["voltage"] = "400VAC"

        # Haberleşme / Sinyal Protokolleri
        proto_map = {
            "4-20mA HART": r"4-20\s*mA\s*HART",
            "Modbus RTU": r"Modbus\s*RTU",
            "Modbus TCP": r"Modbus\s*TCP",
            "Profinet": r"Profinet",
            "Profibus": r"Profibus",
        }
        for proto_name, pattern in proto_map.items():
            if re.search(pattern, raw_text, re.IGNORECASE):
                params["protocol"] = proto_name
                break

        # Gövde Malzemesi
        if re.search(r"\b(316L|AISI\s?316|Paslanmaz)\b", raw_text, re.IGNORECASE):
            params["body_material"] = "AISI 316L SS"
        elif re.search(r"\b(Alüminyum|Aluminium)\b", raw_text, re.IGNORECASE):
            params["body_material"] = "Alüminyum"

        return params

    @classmethod
    def validate_equipment(cls, spec_params: Dict[str, Any], equipment: Dict[str, Any]) -> List[Dict[str, str]]:
        discrepancies: List[Dict[str, str]] = []

        if not spec_params:
            return discrepancies

        # 1. IP Koruma Kontrolü
        if spec_params.get("ip_rating"):
            equip_ip = equipment.get("ip_rating")
            if not equip_ip and "ip" in equipment:
                ip_val = re.search(r"(\d{2})", str(equipment["ip"]))
                equip_ip = int(ip_val.group(1)) if ip_val else None

            if not equip_ip:
                discrepancies.append({
                    "param": "IP Koruma",
                    "status": "Eksik Bilgi",
                    "detail": f"Şartname IP{spec_params['ip_rating']} istiyor, cihaz föyünde IP seviyesi bulunamadı.",
                    "level": "warning"
                })
            elif equip_ip < spec_params["ip_rating"]:
                discrepancies.append({
                    "param": "IP Koruma",
                    "status": "Uyumsuz",
                    "detail": f"Şartname IP{spec_params['ip_rating']} isterken, teklif edilen cihaz IP{equip_ip}.",
                    "level": "danger"
                })
            else:
                discrepancies.append({
                    "param": "IP Koruma",
                    "status": "Uyumlu",
                    "detail": f"Cihaz IP{equip_ip} koruma sınıfı ile şartnameyi karşılıyor.",
                    "level": "success"
                })

        # 2. ATEX / Ex-Proof Kontrolü
        if spec_params.get("is_atex_required"):
            equip_atex = equipment.get("is_atex", False)
            if not equip_atex and "ex" in equipment:
                equip_atex = "atex" in str(equipment["ex"]).lower() or "ex" in str(equipment["ex"]).lower()

            if not equip_atex:
                discrepancies.append({
                    "param": "ATEX / Ex-Proof",
                    "status": "Kritik Hata",
                    "detail": f"Şartname patlayıcı ortam sertifikası ({spec_params.get('atex_zone')}) istiyor, ürün Ex-proof değil.",
                    "level": "danger"
                })
            else:
                discrepancies.append({
                    "param": "ATEX / Ex-Proof",
                    "status": "Uyumlu",
                    "detail": f"Ürün {spec_params.get('atex_zone', 'Zone 1')} patlayıcı saha şartlarına uygundur.",
                    "level": "success"
                })

        # 3. Sıcaklık Dayanımı
        if spec_params.get("max_ambient_temp"):
            equip_max_t = equipment.get("max_temp")
            if equip_max_t is not None:
                if equip_max_t < spec_params["max_ambient_temp"]:
                    discrepancies.append({
                        "param": "Çalışma Sıcaklığı",
                        "status": "Sıcaklık Aşımı",
                        "detail": f"Şartname tepe ortam sıcaklığı {spec_params['max_ambient_temp']}°C, ürün sınırı {equip_max_t}°C.",
                        "level": "danger"
                    })
                else:
                    discrepancies.append({
                        "param": "Çalışma Sıcaklığı",
                        "status": "Uyumlu",
                        "detail": f"Cihaz termal sınırı ({equip_max_t}°C) ortam sıcaklığını karşılıyor.",
                        "level": "success"
                    })

        # 4. Besleme Gerilimi
        if spec_params.get("voltage"):
            equip_volt = str(equipment.get("voltage", "")).upper()
            if equip_volt and spec_params["voltage"] not in equip_volt:
                discrepancies.append({
                    "param": "Besleme Gerilimi",
                    "status": "Gerilim Uyuşmazlığı",
                    "detail": f"Şartname {spec_params['voltage']} talep ediyor, teklif edilen cihaz {equip_volt}.",
                    "level": "danger"
                })
            elif equip_volt:
                discrepancies.append({
                    "param": "Besleme Gerilimi",
                    "status": "Uyumlu",
                    "detail": f"Besleme gerilimi ({spec_params['voltage']}) doğrulanmıştır.",
                    "level": "success"
                })

        # 5. Protokol / Sinyal Tipi
        if spec_params.get("protocol"):
            equip_proto = str(equipment.get("protocol") or equipment.get("sinyal", "")).upper()
            if equip_proto and spec_params["protocol"].upper() not in equip_proto:
                discrepancies.append({
                    "param": "Sinyal / Protokol",
                    "status": "Arayüz Sapması",
                    "detail": f"Şartname {spec_params['protocol']} istiyor, cihaz {equip_proto} çıkışlı.",
                    "level": "warning"
                })
            elif equip_proto:
                discrepancies.append({
                    "param": "Sinyal / Protokol",
                    "status": "Uyumlu",
                    "detail": f"{spec_params['protocol']} haberleşme arayüzü tam uyumlu.",
                    "level": "success"
                })

        return discrepancies