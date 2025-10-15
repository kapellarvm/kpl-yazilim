import serial
import time
from serial.tools import list_ports
from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning

class KartHaberlesmeServis:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate

    def baglan(self, cihaz_adi=None):
        print("[LOG] port_yonetici.py -> Kart arama başlatıldı.")
        log_system("Kart arama başlatıldı.")
        ports = list(list_ports.comports())
        bulunan_kartlar = {}

        if not ports:
            log_error("Hiçbir seri port bulunamadı!")
            return False, "Hiçbir seri port bulunamadı!", {}

        for p in ports:
            # Sadece USB portlarını (Arduino'lar gibi) dene
            if "USB" not in p.device and "acm" not in p.device.lower():
                print(f"[LOG] {p.device} USB port değil, atlanıyor...")
                continue

            ser = None
            try:
                print(f"[LOG] {p.device} portu deneniyor...")
                log_system(f"{p.device} portu deneniyor...")
                ser = serial.Serial(p.device, self.baudrate, timeout=2)
                # Donanımsal reset için bekle
                time.sleep(2)

                # === ORİJİNAL HABERLEŞME PROTOKOLÜ ===
                cevap = ""
                # Yazılımsal RESET komutu gönder
                print("    -> 'reset' komutu gönderiliyor...")
                log_system("Reset komutu gönderiliyor...")
                ser.write(b'reset\n')
                time.sleep(1.5) # Reset sonrası için bekle

                ser.reset_input_buffer()

                # Kimlik sorgusunu 2 kere gönder (kaçırılmaması için)
                print("    -> 's' kimlik sorgusu gönderiliyor...")
                log_system("Kimlik sorgusu gönderiliyor...")
                ser.write(b's\n')
                time.sleep(0.2)
                ser.write(b's\n')
                
                # Cevabı bekle
                cevap = ser.readline().decode(errors='ignore').strip().lower()
                # ============================================

                if cevap in ['sensor', 'motor', 'guvenlik']:
                    print(f"✅ {cevap.upper()} kartı {p.device} portunda bulundu.")
                    log_success(f"{cevap.upper()} kartı {p.device} portunda bulundu.")
                    
                    # BAĞLANTI ONAY komutunu ('b') gönder
                    print(f"    -> '{cevap}' kartına 'b' onay komutu gönderiliyor.")
                    ser.write(b'b\n')
                    time.sleep(0.1) # Onayın işlenmesi için kısa bir bekleme
                    
                    bulunan_kartlar[cevap] = p.device
                    
                    # Eğer tek bir cihaz aranıyorsa ve bulunduysa
                    if cihaz_adi and cihaz_adi == cevap:
                        # Portu kapat ve döngüden çık
                        ser.close()
                        print(f"[LOG] Aranan cihaz '{cihaz_adi}' bulundu, arama sonlandırılıyor.")
                        log_success(f"Aranan cihaz '{cihaz_adi}' bulundu.")
                        return True, "Cihaz başarıyla bulundu.", {cihaz_adi: bulunan_kartlar[cihaz_adi]}
                else:
                    print(f"    -> Bu porttan geçerli bir kimlik alınamadı. Cevap: '{cevap}'")
                    log_warning(f"{p.device} portunda geçerli kimlik alınamadı: '{cevap}'")
                
            except serial.SerialException as e:
                print(f"❌ {p.device} portunda seri port hatası: {e}")
                log_error(f"{p.device} portunda seri port hatası: {e}")
            except Exception as e:
                print(f"❌ {p.device} portunda beklenmeyen hata: {e}")
                log_error(f"{p.device} portunda beklenmeyen hata: {e}")
            finally:
                # Portu sadece hala açıksa kapat
                if ser and ser.is_open:
                    try:
                        ser.close()
                        print(f"[LOG] {p.device} portu kapatıldı.")
                    except:
                        pass  # Port zaten kapalıysa veya hata varsa sessizce devam et

        # Döngü tamamlandıktan sonra sonuçları değerlendir
        if bulunan_kartlar:
            if cihaz_adi and cihaz_adi not in bulunan_kartlar:
                log_warning(f"'{cihaz_adi}' kartı bulunamadı. Bulunan kartlar: {list(bulunan_kartlar.keys())}")
                return False, f"'{cihaz_adi}' kartı bulunamadı.", bulunan_kartlar
            else:
                log_success(f"Toplam {len(bulunan_kartlar)} kart bulundu: {list(bulunan_kartlar.keys())}")
                return True, "Kartlar başarıyla bulundu.", bulunan_kartlar
        else:
            log_error("Tanımlı hiçbir kart bulunamadı!")
            return False, "Tanımlı hiçbir kart bulunamadı!", {}