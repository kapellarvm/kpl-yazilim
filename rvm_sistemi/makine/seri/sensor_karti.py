import threading
import queue
import time
import serial
import random
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_sensor, log_error, log_success, log_warning, log_system, log_exception, log_thread_error

class SensorKart:
    def __init__(self, port_adi=None, callback=None, cihaz_adi="sensor"):
        self.port_adi = port_adi  # örn: "/dev/ttyUSB0" (string) - opsiyonel
        self.seri_nesnesi = None  # serial.Serial nesnesi burada tutulacak
        
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        self.port_yoneticisi = KartHaberlesmeServis()
        
        self.running = False
        self.listen_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        self.saglikli = False  # Başlangıçta bağlantı yok, sağlıksız
        
        # İlk bağlantıyı kur
        self._ilk_baglanti()

    def _ilk_baglanti(self):
        """İlk bağlantıyı kurar - port_adi verilmemişse otomatik bulur"""
        print(f"[{self.cihaz_adi}] İlk bağlantı kuruluyor...")
        log_system(f"{self.cihaz_adi} ilk bağlantı kuruluyor...")
        
        if self.port_adi:
            # Port adı verilmişse direkt bağlanmayı dene
            if self.portu_ac():
                log_success(f"{self.cihaz_adi} verilen porta başarıyla bağlandı: {self.port_adi}")
                self.dinlemeyi_baslat()
                return True
            else:
                log_warning(f"{self.cihaz_adi} verilen porta bağlanamadı, otomatik arama başlatılıyor...")
        
        # Port adı verilmemişse veya bağlantı başarısızsa otomatik bul
        basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
        
        if basarili and self.cihaz_adi in portlar:
            self.port_adi = portlar[self.cihaz_adi]
            log_success(f"{self.cihaz_adi} port bulundu: {self.port_adi}")
            
            if self.portu_ac():
                log_success(f"{self.cihaz_adi} başarıyla bağlandı")
                self.dinlemeyi_baslat()
                return True
            else:
                log_error(f"{self.cihaz_adi} porta bağlanamadı")
                return False
        else:
            log_error(f"{self.cihaz_adi} kartı bulunamadı. Mesaj: {mesaj}")
            # İlk bağlantıda kart bulunamazsa, periyodik olarak aramaya devam et
            threading.Thread(target=self._periyodik_baglanti_deneme, daemon=True).start()
            return False

    def _periyodik_baglanti_deneme(self):
        """Port bulunamazsa periyodik olarak yeniden dener"""
        while not self.seri_nesnesi or not self.seri_nesnesi.is_open:
            time.sleep(5)  # 5 saniye bekle
            
            print(f"[{self.cihaz_adi}] Port tekrar aranıyor...")
            log_system(f"{self.cihaz_adi} port tekrar aranıyor...")
            
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
            
            if basarili and self.cihaz_adi in portlar:
                self.port_adi = portlar[self.cihaz_adi]
                log_success(f"{self.cihaz_adi} port bulundu: {self.port_adi}")
                
                if self.portu_ac():
                    log_success(f"{self.cihaz_adi} başarıyla bağlandı")
                    self.dinlemeyi_baslat()
                    break  # Bağlantı kuruldu, döngüden çık
                else:
                    log_error(f"{self.cihaz_adi} porta bağlanamadı, tekrar denenecek...")
            else:
                log_warning(f"{self.cihaz_adi} kartı hala bulunamadı, 5 saniye sonra tekrar denenecek...")

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
        """Kartın sağlık durumunu kontrol eder"""
        if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
            print(f"[{self.cihaz_adi}] Port açık değil, ping gönderilemedi")
            log_warning(f"{self.cihaz_adi} port açık değil, ping gönderilemedi")
            self._baglanti_kontrol()
            return False
            
        self.saglikli = False  # Sağlık durumunu sıfırla
        self.write_queue.put(("ping", None))
        time.sleep(0.2)  # Ping cevabı için bekle
        
        if not self.saglikli:
            print(f"[{self.cihaz_adi}] Ping cevabı alınamadı, sağlıksız")
            log_warning(f"{self.cihaz_adi} ping cevabı alınamadı, bağlantı kontrol ediliyor...")
            self._baglanti_kontrol()
            return False
        else:
            print(f"[{self.cihaz_adi}] Ping başarılı, sağlıklı")
            return True

    def getir_saglik_durumu(self): 
        return self.saglikli

    def portu_ac(self):
        """Verilen port adına seri bağlantı açar."""
        if not self.port_adi:
            print(f"[{self.cihaz_adi}] Port adı belirtilmemiş!")
            return False
            
        try:
            # Eski portu kapat eğer açıksa
            if self.seri_nesnesi and self.seri_nesnesi.is_open:
                self.seri_nesnesi.close()
                time.sleep(0.5)
                
            print(f"[{self.cihaz_adi}] {self.port_adi} portu açılıyor...")
            self.seri_nesnesi = serial.Serial(self.port_adi, baudrate=115200, timeout=1)
            print(f"✅ [{self.cihaz_adi}] {self.port_adi} portuna başarıyla bağlandı.")
            log_success(f"{self.cihaz_adi} {self.port_adi} portuna bağlandı")
            self.saglikli = True
            return True
        except serial.SerialException as e:
            print(f"❌ [{self.cihaz_adi}] {self.port_adi} portu AÇILAMADI: {e}")
            log_error(f"{self.cihaz_adi} {self.port_adi} portu açılamadı: {e}")
            self.seri_nesnesi = None
            self.saglikli = False
            return False

    def dinlemeyi_baslat(self):
        """Okuma ve yazma thread'lerini başlatır"""
        if not self.running:
            self.running = True
            
            # Eski thread'leri temizle
            if self.listen_thread and self.listen_thread.is_alive():
                self.listen_thread.join(timeout=0.1)
            if self.write_thread and self.write_thread.is_alive():
                self.write_thread.join(timeout=0.1)
            
            # Yeni thread'leri başlat
            self.listen_thread = threading.Thread(target=self._dinle, daemon=True)
            self.listen_thread.start()
            self.write_thread = threading.Thread(target=self._yaz, daemon=True)
            self.write_thread.start()
            
            print(f"[{self.cihaz_adi}] Dinleme ve yazma thread'leri başlatıldı")
            log_system(f"{self.cihaz_adi} dinleme ve yazma thread'leri başlatıldı")

    def dinlemeyi_durdur(self):
        """Thread'leri güvenli bir şekilde durdurur"""
        print(f"[{self.cihaz_adi}] Thread'ler durduruluyor...")
        self.running = False
        
        # Yazma thread'ini güvenli kapat
        self.write_queue.put(("exit", None))
        
        # Thread'lerin kapanmasını bekle
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=1)
        if self.write_thread and self.write_thread.is_alive():
            self.write_thread.join(timeout=1)
            
        print(f"[{self.cihaz_adi}] Thread'ler durduruldu")

    def _yaz(self):
        """Yazma thread'i - queue'dan komutları alıp seri porta yazar"""
        while self.running:
            try:
                # Komut al (1 saniye timeout ile)
                try:
                    command, data = self.write_queue.get(timeout=1)
                except queue.Empty:
                    continue
                    
                if command == "exit": 
                    break

                # Port kontrolü
                if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                    print(f"[{self.cihaz_adi}] Yazma: Port açık değil, komut atlanıyor: {command}")
                    time.sleep(0.5)
                    continue

                # Komut sözlüğü
                komutlar = {
                    "loadcell_olc": b"lo\n", "teach": b"gst\n", "led_ac": b"as\n", "ezici_ileri": b"ei\n",
                    "ezici_geri": b"eg\n", "ezici_dur": b"ed\n", "kirici_ileri": b"ki\n", "kirici_geri": b"kg\n",
                    "kirici_dur": b"kd\n", "led_kapat": b"ad\n", "tare": b"lst\n", "ledfull_ac": b"la\n", 
                    "led_pwm": f"l:{data}\n".encode() if data else b"l:0\n",
                    "ledfull_kapat": b"ls\n", "doluluk_oranı": b"do\n", "reset": b"reset\n", "ping": b"ping\n",
                    "makine_oturum_var": b"mov\n", "makine_oturum_yok": b"moy\n", "makine_bakim_modu": b"mb\n",
                    
                    # Güvenlik kartı komutları
                    "ust_kilit_ac": b"#uka\n", "ust_kilit_kapat": b"#ukk\n", "alt_kilit_ac": b"#aka\n", 
                    "alt_kilit_kapat": b"#akk\n", "ust_kilit_durum_sorgula": b"#msud\n", 
                    "alt_kilit_durum_sorgula": b"#msad\n", "bme_guvenlik": b"#bme\n",
                    "manyetik_saglik": b"#mesd\n", 
                    "fan_pwm": f"#f:{data}\n".encode() if data else b"#f:0\n", 
                    "bypass_modu_ac": b"#bypa\n", "bypass_modu_kapat": b"#bypp\n", 
                    "guvenlik_role_reset": b"#gr\n", "guvenlik_kart_reset": b"#reset\n"
                }
                
                if command in komutlar:
                    self.seri_nesnesi.write(komutlar[command])
                    print(f"[{self.cihaz_adi}] Komut gönderildi: {command}")
                else:
                    print(f"[{self.cihaz_adi}] Bilinmeyen komut: {command}")
                    
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] YAZMA HATASI: {e}")
                log_error(f"{self.cihaz_adi} yazma hatası: {e}")
                self.running = False  # Thread'i durdur
                self._baglanti_kontrol()  # Yeniden bağlan
                break
            except Exception as e:
                print(f"[{self.cihaz_adi}] Yazma thread'inde beklenmeyen hata: {e}")
                log_exception(f"{self.cihaz_adi} yazma hatası", exc_info=(type(e), e, e.__traceback__))

    def _dinle(self):
        """Dinleme thread'i - seri porttan gelen mesajları okur"""
        while self.running:
            try:
                # Port kontrolü
                if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                    print(f"[{self.cihaz_adi}] Dinleme: Port açık değil")
                    time.sleep(1)
                    continue
                    
                # Veri varsa oku
                if self.seri_nesnesi.in_waiting > 0:
                    data = self.seri_nesnesi.readline().decode(errors='ignore').strip()
                    if data:
                        # Reset mesajını kontrol et
                        if data.lower() == "resetlendi":
                            print(f"[{self.cihaz_adi}] Kart resetlendi bildirimi alındı")
                            log_warning(f"{self.cihaz_adi} kart resetlendi")
                            self.saglikli = False
                            # Reset sonrası yeniden bağlantı kur
                            time.sleep(2)  # Kartın tamamen başlaması için bekle
                            self._baglanti_kontrol()
                            break  # Thread'den çık, yenisi başlayacak
                        else:
                            self._mesaj_isle(data)
                else:
                    time.sleep(0.05)  # CPU kullanımını azalt
                    
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] OKUMA HATASI: {e}")
                log_error(f"{self.cihaz_adi} okuma hatası: {e}")
                self.running = False
                self._baglanti_kontrol()
                break
            except Exception as e:
                print(f"[{self.cihaz_adi}] Dinleme thread'inde beklenmeyen hata: {e}")
                log_exception(f"{self.cihaz_adi} dinleme hatası", exc_info=(type(e), e, e.__traceback__))
                time.sleep(1)  # Hata durumunda biraz bekle

    def _baglanti_kontrol(self):
        """Bağlantı koptuğunda yeniden bağlanmayı dener"""
        print(f"[{self.cihaz_adi}] Bağlantı kontrolü başlatıldı...")
        log_system(f"{self.cihaz_adi} bağlantı kontrolü başlatıldı")
        
        # Thread'leri durdur
        self.dinlemeyi_durdur()
        
        # Portu kapat
        if self.seri_nesnesi and self.seri_nesnesi.is_open:
            try:
                self.seri_nesnesi.close()
                log_system(f"{self.cihaz_adi} port kapatıldı")
            except Exception as e:
                log_error(f"{self.cihaz_adi} port kapatma hatası: {e}")
        self.seri_nesnesi = None
        self.saglikli = False
        
        # Yeniden bağlanmayı dene (arka plan thread'inde)
        threading.Thread(target=self._yeniden_baglan, daemon=True).start()

    def _yeniden_baglan(self):
        """Arka planda yeniden bağlanmayı dener"""
        deneme_sayisi = 0
        max_deneme = 10  # Maksimum deneme sayısı
        
        while deneme_sayisi < max_deneme:
            deneme_sayisi += 1
            print(f"[{self.cihaz_adi}] Yeniden bağlanma denemesi {deneme_sayisi}/{max_deneme}")
            log_system(f"{self.cihaz_adi} yeniden bağlanma denemesi {deneme_sayisi}/{max_deneme}")
            
            # Port ara
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
            
            if basarili and self.cihaz_adi in portlar:
                self.port_adi = portlar[self.cihaz_adi]
                log_success(f"{self.cihaz_adi} yeni port bulundu: {self.port_adi}")
                
                if self.portu_ac():
                    log_success(f"{self.cihaz_adi} yeniden bağlandı")
                    self.dinlemeyi_baslat()
                    return  # Başarılı, çık
                else:
                    log_error(f"{self.cihaz_adi} porta bağlanamadı")
            else:
                log_warning(f"{self.cihaz_adi} kartı bulunamadı: {mesaj}")
            
            # Bekleme süresi (her denemede artar)
            bekleme_suresi = min(5 * deneme_sayisi, 30)  # Max 30 saniye
            print(f"[{self.cihaz_adi}] {bekleme_suresi} saniye sonra tekrar denenecek...")
            time.sleep(bekleme_suresi)
        
        log_error(f"{self.cihaz_adi} maksimum deneme sayısına ulaşıldı, bağlantı kurulamadı!")
        print(f"[{self.cihaz_adi}] HATA: Maksimum deneme sayısına ulaşıldı!")

    def agirlik_olc(self):
        """Loadcell'den ağırlık ölçümü yapar"""
        if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
            print(f"[{self.cihaz_adi}] Port açık değil, ağırlık ölçülemedi")
            return False
        
        self.write_queue.put(("loadcell_olc", None))
        print(f"[{self.cihaz_adi}] Ağırlık ölçüm komutu gönderildi")
        return True

    def _mesaj_isle(self, mesaj):
        """Gelen mesajları işler"""
        if not mesaj or not mesaj.isprintable():
            return
        
        # Ping cevabını kontrol et
        if mesaj.lower() == "pong":
            self.saglikli = True
            print(f"[{self.cihaz_adi}] Pong alındı - sağlıklı")
        
        # Callback varsa çağır
        if self.callback:
            try:
                self.callback(mesaj)
            except Exception as e:
                print(f"[{self.cihaz_adi}] Callback hatası: {e}")
                log_error(f"{self.cihaz_adi} callback hatası: {e}")