import threading
import queue
import time
import serial
import random
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_sensor, log_error, log_success, log_warning, log_system, log_exception, log_thread_error

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
    def led_full_ac(self): self.write_queue.put(("ledfull_ac", None))
    def led_full_kapat(self): self.write_queue.put(("ledfull_kapat", None))
    def led_kapat(self): self.write_queue.put(("led_kapat", None))
    def led_pwm(self, deger): self.write_queue.put(("led_pwm", deger))
    def tare(self): self.write_queue.put(("tare", None))
    def reset(self): self.write_queue.put(("reset", None))
    def ezici_ileri(self): self.write_queue.put(("ezici_ileri", None))
    def ezici_geri(self): self.write_queue.put(("ezici_geri", None))
    def ezici_dur(self): self.write_queue.put(("ezici_dur", None))
    def kirici_ileri(self): self.write_queue.put(("kirici_ileri", None))
    def kirici_geri(self): self.write_queue.put(("kirici_geri", None))
    def kirici_dur(self): self.write_queue.put(("kirici_dur", None))
    def doluluk_oranı(self): self.write_queue.put(("doluluk_oranı", None))
    def makine_oturum_var(self): self.write_queue.put(("makine_oturum_var", None))
    def makine_oturum_yok(self): self.write_queue.put(("makine_oturum_yok", None))
    def makine_bakim_modu(self): self.write_queue.put(("makine_bakim_modu", None))

    # ---------------------------------------------- Güvenlik Kartı Komutları ----------------------------------------------
    def ust_kilit_ac(self): self.write_queue.put(("ust_kilit_ac", None))
    def ust_kilit_kapat(self): self.write_queue.put(("ust_kilit_kapat", None))
    def alt_kilit_ac(self): self.write_queue.put(("alt_kilit_ac", None))
    def alt_kilit_kapat(self): self.write_queue.put(("alt_kilit_kapat", None))
    def ust_kilit_durum_sorgula(self): self.write_queue.put(("ust_kilit_durum_sorgula", None))
    def alt_kilit_durum_sorgula(self): self.write_queue.put(("alt_kilit_durum_sorgula", None))
    def bme_guvenlik(self): self.write_queue.put(("bme_guvenlik", None))
    def manyetik_saglik(self): self.write_queue.put(("manyetik_saglik", None))
    def fan_pwm(self, deger): self.write_queue.put(("fan_pwm", deger))
    def bypass_modu_ac(self): self.write_queue.put(("bypass_modu_ac", None))
    def bypass_modu_kapat(self): self.write_queue.put(("bypass_modu_kapat", None))
    def guvenlik_role_reset(self): self.write_queue.put(("guvenlik_role_reset", None))
    def guvenlik_kart_reset(self): self.write_queue.put(("guvenlik_kart_reset", None))

    def ping(self):
        self.saglikli = False  # Sağlık durumunu her ping öncesi sıfırla
        self.write_queue.put(("ping", None))
        time.sleep(.1)  # Ping sonrası sağlık durumunu kontrol etmek için bekle
        if not self.saglikli:
            print(f"[LOG] {self.cihaz_adi} sağlıksız, bağlantı sıfırlanıyor...")
            log_warning(f"{self.cihaz_adi} sağlıksız, bağlantı sıfırlanıyor...")
            # Sadece running flag'ini kapat, thread'i join etme
            self.running = False
            if self.seri_nesnesi and self.seri_nesnesi.is_open:
                try:
                    self.seri_nesnesi.close()
                    time.sleep(1)  # Portun serbest bırakılması için bekleme süresi
                    log_system(f"{self.cihaz_adi} port kapatıldı")
                except Exception as e:
                    print(f"[LOG] Port kapatma hatası: {e}")
                    log_error(f"{self.cihaz_adi} port kapatma hatası: {e}")
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
                    "kirici_dur": b"kd\n", "led_kapat": b"ad\n", "tare": b"lst\n", "ledfull_ac": b"la\n", "led_pwm": f"l:{data}\n".encode(),
                    "ledfull_kapat": b"ls\n", "doluluk_oranı": b"do\n", "reset": b"reset\n", "ping": b"ping\n",
                    "makine_oturum_var": b"mov\n", "makine_oturum_yok": b"moy\n", "makine_bakim_modu": b"mb\n",
                    
                    "ust_kilit_ac": b"#uka\n", "ust_kilit_kapat": b"#ukk\n", "alt_kilit_ac": b"#aka\n", "alt_kilit_kapat": b"#akk\n",
                    "ust_kilit_durum_sorgula": b"#msud\n", "alt_kilit_durum_sorgula": b"#msad\n", "bme_guvenlik": b"#bme\n",
                    "manyetik_saglik": b"#mesd\n", "fan_pwm": f"#f:{data}\n".encode(), "bypass_modu_ac": b"#bypa\n",
                    "bypass_modu_kapat": b"#bypp\n", "guvenlik_role_reset": b"#gr\n", "guvenlik_kart_reset": b"#reset\n"
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
                        if data.lower() == "resetlendi":  # Reset mesajını kontrol et
                            print(f"[{self.cihaz_adi}] Kart resetlendi, bağlantı yeniden başlatılıyor...")
                            log_warning(f"{self.cihaz_adi} kart resetlendi, bağlantı yeniden başlatılıyor...")
                            self.running = False  # Thread'i durdur
                            if self.seri_nesnesi and self.seri_nesnesi.is_open:
                                self.seri_nesnesi.close()
                            time.sleep(1)  # Portun kapanması için bekle
                            self._baglanti_kontrol()  # Yeniden bağlantı işlemini başlat
                            break  # Mevcut thread'den çık
                        else:
                            self._mesaj_isle(data)  # Normal mesaj işleme
                else:
                    time.sleep(0.05)
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] OKUMA HATASI: {e}")
                log_error(f"{self.cihaz_adi} okuma hatası: {e}")
                log_exception(f"{self.cihaz_adi} seri port okuma hatası", exc_info=(type(e), e, e.__traceback__))
                self._baglanti_kontrol()
                break # Döngüyü kır, yeni thread başlayacak
            except Exception as e:
                print(f"[{self.cihaz_adi}] BEKLENMEYEN HATA: {e}")
                log_thread_error(f"{self.cihaz_adi} beklenmeyen hata: {e}")
                log_exception(f"{self.cihaz_adi} thread hatası", exc_info=(type(e), e, e.__traceback__))
                self._baglanti_kontrol()
                break

    def _baglanti_kontrol(self):
        print(f"[{self.cihaz_adi}] Yeniden bağlanma süreci başlatıldı...")
        log_system(f"{self.cihaz_adi} yeniden bağlanma süreci başlatıldı...")
        
        # Sadece running flag'ini kapat, thread'i join etme
        self.running = False
        
        # Eski portu güvenle kapat
        if self.seri_nesnesi and self.seri_nesnesi.is_open:
            try: 
                self.seri_nesnesi.close()
                log_system(f"{self.cihaz_adi} eski port kapatıldı")
            except Exception as e:
                log_error(f"{self.cihaz_adi} port kapatma hatası: {e}")
        self.seri_nesnesi = None

        while True:
            print(f"[{self.cihaz_adi}] Yeni port aranıyor...")
            log_system(f"{self.cihaz_adi} yeni port aranıyor...")
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)

            if basarili and self.cihaz_adi in portlar:
                yeni_port_adi = portlar[self.cihaz_adi]
                self.port_adi = yeni_port_adi # Yeni port adını kaydet
                log_success(f"{self.cihaz_adi} yeni port bulundu: {yeni_port_adi}")
                
                if self.portu_ac(): # Yeni porta bağlanmayı dene
                    log_success(f"{self.cihaz_adi} yeni porta başarıyla bağlandı")
                    self.dinlemeyi_baslat()
                    return # Başarılı oldu, fonksiyondan çık
                else:
                    log_error(f"{self.cihaz_adi} yeni porta bağlanamadı")
            
            print(f"[{self.cihaz_adi}] Port bulunamadı, 5 saniye sonra tekrar denenecek.")
            log_warning(f"{self.cihaz_adi} port bulunamadı, 5 saniye sonra tekrar denenecek")
            time.sleep(5)

    def agirlik_olc(self):
        """Loadcell'den ağırlık ölçümü yapar - Yeni sistem: 'lo' komutu gönderir"""
        try:
            if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                print("[SENSOR] Seri port açık değil")
                return False
            
            # Yeni sistem: 'lo' komutunu queue'ya ekle
            self.write_queue.put(("loadcell_olc", None))
            print("[SENSOR] Ağırlık ölçüm komutu queue'ya eklendi: lo")
            return True
            
        except Exception as e:
            print(f"[SENSOR] Ağırlık ölçüm hatası: {e}")
            return False

    def reset(self):
        """Sensör kartını resetler"""
        try:
            if self.seri_nesnesi and self.seri_nesnesi.is_open:
                print(f"[{self.cihaz_adi}] Reset komutu gönderiliyor...")
                log_system(f"{self.cihaz_adi} reset komutu gönderiliyor...")
                self.write_queue.put(("reset", None))  # Write queue üzerinden gönder
        except Exception as e:
            print(f"[{self.cihaz_adi}] Reset hatası: {e}")
            log_error(f"{self.cihaz_adi} reset hatası: {e}")

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():  # Mesajın yazdırılabilir olup olmadığını kontrol edin
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        if mesaj.lower() == "pong":
            self.saglikli = True
        if self.callback:
            self.callback(mesaj)
