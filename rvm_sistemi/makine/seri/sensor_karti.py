import threading
import queue
import time
import serial
import random
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis

class SensorKart:
    def __init__(self, port_adi, callback=None, cihaz_adi="sensor"):
        self.port_adi = port_adi  # örn: "/dev/ttyUSB0" (string)
        self.seri_nesnesi = None  # serial.Serial nesnesi burada tutulacak
        
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        self.port_yoneticisi = KartHaberlesmeServis()
        
        self.running = False
        self.listen_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        self.saglikli = True  # Başlangıçta sağlıklı olarak başlat

        # DOĞRUDAN BAĞLANTIYI BAŞLAT
        self.portu_ac()

    def loadcell_olc(self): self.write_queue.put(("loadcell_olc", None))
    def teach(self): self.write_queue.put(("teach", None))
    def led_ac(self): self.write_queue.put(("led_ac", None))
    def led_kapat(self): self.write_queue.put(("led_kapat", None))
    def tare(self): self.write_queue.put(("tare", None))
    def reset(self): self.write_queue.put(("reset", None))
    def ezici_ileri(self): self.write_queue.put(("ezici_ileri", None))
    def ezici_geri(self): self.write_queue.put(("ezici_geri", None))
    def ezici_dur(self): self.write_queue.put(("ezici_dur", None))
    def kirici_ileri(self): self.write_queue.put(("kirici_ileri", None))
    def kirici_geri(self): self.write_queue.put(("kirici_geri", None))
    def kirici_dur(self): self.write_queue.put(("kirici_dur", None))
    def doluluk_oranı(self): self.write_queue.put(("doluluk_oranı", None))
    def ping(self):
        self.saglikli = False  # Sağlık durumunu her ping öncesi sıfırla
        self.write_queue.put(("ping", None))
        time.sleep(.1)  # Ping sonrası sağlık durumunu kontrol etmek için bekle
        if not self.saglikli:
            print(f"[LOG] {self.cihaz_adi} sağlıksız, bağlantı sıfırlanıyor...")
            self.dinlemeyi_durdur()  # Thread'leri durdur
            if self.port and self.port.is_open:
                try:
                    self.port.close()
                    time.sleep(1)  # Portun serbest bırakılması için bekleme süresi
                except Exception as e:
                    print(f"[LOG] Port kapatma hatası: {e}")
            self._baglanti_kontrol()  # Yeniden bağlanmayı dene

            # Yeniden bağlandıktan sonra sağlık durumunu tekrar kontrol et
            self.saglikli = False  # Sağlık durumunu tekrar sıfırla
            self.write_queue.put(("ping", None))
            time.sleep(.1)  # Sağlık durumunu kontrol etmek için bekle

        if self.saglikli:
            print(f"[LOG] {self.cihaz_adi} sağlıklı.")
        else:
            print(f"[LOG] {self.cihaz_adi} hala sağlıksız.")
    def getir_saglik_durumu(self): return self.saglikli

    def portu_ac(self):
        """Verilen port adına seri bağlantı açar."""
        try:
            print(f"[{self.cihaz_adi}] {self.port_adi} portu açılıyor...")
            # Kendi seri nesnesini oluştur
            self.seri_nesnesi = serial.Serial(self.port_adi, baudrate=115200, timeout=1)
            print(f"✅ [{self.cihaz_adi}] {self.port_adi} portuna başarıyla bağlandı.")
            return True
        except serial.SerialException as e:
            print(f"❌ [{self.cihaz_adi}] {self.port_adi} portu AÇILAMADI: {e}")
            self.seri_nesnesi = None
            return False

    def dinlemeyi_baslat(self):
        if not self.running:
            self.running = True
            self.listen_thread = threading.Thread(target=self._dinle, daemon=True)
            self.listen_thread.start()
            self.write_thread = threading.Thread(target=self._yaz, daemon=True)
            self.write_thread.start()

    def dinlemeyi_durdur(self):
        self.running = False
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=1)
        if self.write_thread and self.write_thread.is_alive():
             self.write_queue.put(("exit", None)) # Yazma thread'ini güvenli kapat
             self.write_thread.join(timeout=1)

    def _yaz(self):
        while self.running:
            try:
                # self.seri_nesnesi'ni kontrol et
                if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                    time.sleep(0.5)
                    continue

                command, data = self.write_queue.get(timeout=1)
                if command == "exit": break

                komutlar = {
                    "loadcell_olc": b"lo\n", "teach": b"gst\n", "led_ac": b"as\n", "ezici_ileri": b"ei\n",
                    "ezici_geri": b"eg\n", "ezici_dur": b"ed\n", "kirici_ileri": b"ki\n", "kirici_geri": b"kg\n",
                    "kirici_dur": b"kd\n", "led_kapat": b"ad\n", "tare": b"tare\n",
                    "doluluk_oranı": b"do\n", "reset": b"reset\n", "ping": b"ping\n"
                }
                if command in komutlar:
                    self.seri_nesnesi.write(komutlar[command])
            except queue.Empty:
                continue
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] YAZMA HATASI: {e}")
                self._baglanti_kontrol()
                break # Döngüyü kır, yeni thread başlayacak

    def _dinle(self):
        while self.running:
            try:
                # self.seri_nesnesi'ni kontrol et
                if self.seri_nesnesi and self.seri_nesnesi.is_open and self.seri_nesnesi.in_waiting > 0:
                    data = self.seri_nesnesi.readline().decode(errors='ignore').strip()
                    if data:
                        self._mesaj_isle(data)
                else:
                    time.sleep(0.05)
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] OKUMA HATASI: {e}")
                self._baglanti_kontrol()
                break # Döngüyü kır, yeni thread başlayacak

    def _baglanti_kontrol(self):
        print(f"[{self.cihaz_adi}] Yeniden bağlanma süreci başlatıldı...")
        self.dinlemeyi_durdur()
        
        # Eski portu güvenle kapat
        if self.seri_nesnesi and self.seri_nesnesi.is_open:
            try: self.seri_nesnesi.close()
            except: pass
        self.seri_nesnesi = None

        while True:
            print(f"[{self.cihaz_adi}] Yeni port aranıyor...")
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)

            if basarili and self.cihaz_adi in portlar:
                yeni_port_adi = portlar[self.cihaz_adi]
                self.port_adi = yeni_port_adi # Yeni port adını kaydet
                
                if self.portu_ac(): # Yeni porta bağlanmayı dene
                    self.dinlemeyi_baslat()
                    return # Başarılı oldu, fonksiyondan çık
            
            print(f"[{self.cihaz_adi}] Port bulunamadı, 5 saniye sonra tekrar denenecek.")
            time.sleep(5)

    def agirlik_olc(self):
        """Loadcell'den ağırlık ölçümü yapar"""
        try:
            if not self.seri_port or not self.seri_port.is_open:
                return 0.0
            
            # Ağırlık ölçüm komutu gönder
            self.seri_port.write(b"agirlik_olc\n")
            time.sleep(0.1)  # Kısa bekleme
            
            # Cevap bekle (basit implementasyon)
            return round(random.uniform(0, 50), 1)  # Şimdilik rastgele değer
        except Exception as e:
            print(f"[SENSOR] Ağırlık ölçüm hatası: {e}")
            return 0.0

    def reset(self):
        """Sensör kartını resetler"""
        try:
            if self.seri_port and self.seri_port.is_open:
                self.seri_port.write(b"reset\n")
                time.sleep(0.1)
        except Exception as e:
            print(f"[SENSOR] Reset hatası: {e}")

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():  # Mesajın yazdırılabilir olup olmadığını kontrol edin
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        if mesaj.lower() == "pong":
            self.saglikli = True
        if self.callback:
            self.callback(mesaj)
