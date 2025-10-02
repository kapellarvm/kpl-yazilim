import serial
import time
from serial.tools import list_ports

class KartHaberlesmeServis:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate

    def baglan(self, cihaz_adi=None):
        print("[LOG] port_yonetici.py -> Kart arama başlatıldı.")
        ports = list(list_ports.comports())
        bulunan_kartlar = {}

        if not ports:
            return False, "Hiçbir seri port bulunamadı!", {}

        for p in ports:
            # Sadece USB portlarını (Arduino'lar gibi) dene
            if "USB" not in p.device and "acm" not in p.device.lower():
                continue

            ser = None
            try:
                print(f"[LOG] {p.device} portu deneniyor...")
                ser = serial.Serial(p.device, self.baudrate, timeout=2)
                # Donanımsal reset için bekle
                time.sleep(2)

                # === ORİJİNAL HABERLEŞME PROTOKOLÜ ===
                cevap = ""
                # Yazılımsal RESET komutu gönder
                print("    -> 'reset' komutu gönderiliyor...")
                ser.write(b'reset\n')
                time.sleep(1.5) # Reset sonrası için bekle

                ser.reset_input_buffer()

                # Kimlik sorgusunu 2 kere gönder (kaçırılmaması için)
                print("    -> 's' kimlik sorgusu gönderiliyor...")
                ser.write(b's\n')
                time.sleep(0.2)
                ser.write(b's\n')
                
                # Cevabı bekle
                cevap = ser.readline().decode(errors='ignore').strip().lower()
                # ============================================

                if cevap in ['sensor', 'motor', 'guvenlik']:
                    print(f"✅ {cevap.upper()} kartı {p.device} portunda bulundu.")
                    
                    # BAĞLANTI ONAY komutunu ('b') gönder
                    print(f"    -> '{cevap}' kartına 'b' onay komutu gönderiliyor.")
                    ser.write(b'b\n')
                    time.sleep(0.1) # Onayın işlenmesi için kısa bir bekleme
                    
                    bulunan_kartlar[cevap] = p.device
                    
                    if cihaz_adi and cihaz_adi == cevap:
                         # Portu kapatmadan önce döngüden çık
                        break 
                else:
                    print(f"    -> Bu porttan geçerli bir kimlik alınamadı. Cevap: '{cevap}'")
                
            except Exception as e:
                print(f"❌ {p.device} portunda hata: {e}")
            finally:
                if ser and ser.is_open:
                    ser.close()

            # Eğer tek bir cihaz aranıyorsa ve bulunduysa, diğer portlara bakmaya gerek yok.
            if cihaz_adi and cihaz_adi in bulunan_kartlar:
                return True, "Cihaz başarıyla bulundu.", {cihaz_adi: bulunan_kartlar[cihaz_adi]}

        if bulunan_kartlar:
            return True, "Kartlar başarıyla bulundu.", bulunan_kartlar
        else:
            return False, "Tanımlı hiçbir kart bulunamadı!", {}