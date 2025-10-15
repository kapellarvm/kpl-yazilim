import threading
import queue
import time
import serial

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_motor, log_error, log_success, log_warning, log_system, log_exception, log_thread_error

class MotorKart:
    def __init__(self, port_adi=None, callback=None, cihaz_adi="motor"):
        self.port_adi = port_adi  # örn: "/dev/ttyUSB0" (string) - opsiyonel
        self.seri_nesnesi = None  # serial.Serial nesnesi burada tutulacak
        
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        self.port_yoneticisi = KartHaberlesmeServis()
        
        # Motor parametreleri
        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200
        self.klape_flag = False
        
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
                # İlk bağlantıda parametreleri gönder
                time.sleep(1)  # Kartın hazır olması için bekle
                self.parametre_gonder()
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
                # İlk bağlantıda parametreleri gönder
                time.sleep(1)
                self.parametre_gonder()
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
                    # Bağlantı kurulduktan sonra parametreleri gönder
                    time.sleep(1)
                    self.parametre_gonder()
                    break  # Bağlantı kuruldu, döngüden çık
                else:
                    log_error(f"{self.cihaz_adi} porta bağlanamadı, tekrar denenecek...")
            else:
                log_warning(f"{self.cihaz_adi} kartı hala bulunamadı, 5 saniye sonra tekrar denenecek...")

    # Motor komutları
    def parametre_gonder(self):
        self.write_queue.put(("parametre_gonder", None))

    def parametre_degistir(self, konveyor=None, yonlendirici=None, klape=None):
        if konveyor is not None:
            self.konveyor_hizi = konveyor
        if yonlendirici is not None:
            self.yonlendirici_hizi = yonlendirici
        if klape is not None:
            self.klape_hizi = klape
        self.parametre_gonder()  # Değişiklikleri karta gönder

    def konveyor_hiz_ayarla(self, hiz):
        self.konveyor_hizi = hiz
        self.parametre_gonder()

    def yonlendirici_hiz_ayarla(self, hiz):
        self.yonlendirici_hizi = hiz
        self.parametre_gonder()

    def klape_hiz_ayarla(self, hiz):
        self.klape_hizi = hiz
        self.parametre_gonder()

    def reset(self):
        self.write_queue.put(("reset", None))

    def motorlari_aktif_et(self):
        self.write_queue.put(("motorlari_aktif_et", None))

    def motorlari_iptal_et(self):
        self.write_queue.put(("motorlari_iptal_et", None))

    def konveyor_ileri(self):
        self.write_queue.put(("konveyor_ileri", None))

    def konveyor_geri(self):
        self.write_queue.put(("konveyor_geri", None))

    def konveyor_dur(self):
        self.write_queue.put(("konveyor_dur", None))
    
    def konveyor_problem_var(self):
        self.write_queue.put(("konveyor_problem_var", None))

    def konveyor_problem_yok(self):
        self.write_queue.put(("konveyor_problem_yok", None))

    def mesafe_baslat(self):
        self.write_queue.put(("mesafe_baslat", None))

    def mesafe_bitir(self):
        self.write_queue.put(("mesafe_bitir", None))

    def yonlendirici_plastik(self):
        self.write_queue.put(("yonlendirici_plastik", None))

    def yonlendirici_cam(self):
        self.write_queue.put(("yonlendirici_cam", None))

    def yonlendirici_dur(self):
        self.write_queue.put(("yonlendirici_dur", None))

    def klape_metal(self):
        self.write_queue.put(("klape_metal", None))
        self.klape_flag = True

    def klape_plastik(self):
        if self.klape_flag:
            self.write_queue.put(("klape_plastik", None))
            self.klape_flag = False

    def yonlendirici_sensor_teach(self):
        self.write_queue.put(("yonlendirici_sensor_teach", None))

    def bme_sensor_veri(self):
        self.write_queue.put(("bme_sensor_veri", None))
    
    def sensor_saglik_durumu(self):
        self.write_queue.put(("sensor_saglik_durumu", None))
    
    def atik_uzunluk(self):
        self.write_queue.put(("atik_uzunluk", None))

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
                    "motorlari_aktif_et": b"aktif\n",
                    "motorlari_iptal_et": b"iptal\n",
                    "konveyor_ileri": b"kmi\n",
                    "konveyor_geri": b"kmg\n",
                    "konveyor_dur": b"kmd\n",
                    "konveyor_problem_var": b"pv\n",
                    "konveyor_problem_yok": b"py\n",
                    "mesafe_baslat": b"mb\n",  # Mesafe komutları eklendi
                    "mesafe_bitir": b"ms\n",
                    "yonlendirici_plastik": b"ymp\n",
                    "yonlendirici_cam": b"ymc\n",
                    "yonlendirici_dur": b"ymd\n",
                    "klape_metal": b"smm\n",
                    "klape_plastik": b"smp\n",
                    "yonlendirici_sensor_teach": b"yst\n",
                    "ping": b"ping\n",
                    "bme_sensor_veri": b"bme\n",
                    "sensor_saglik_durumu": b"msd\n",
                    "atik_uzunluk": b"au\n",
                    "reset": b"reset\n"
                }

                # Özel parametre gönderme komutu
                if command == "parametre_gonder":
                    print(f"[{self.cihaz_adi}] Parametreler gönderiliyor: K:{self.konveyor_hizi} Y:{self.yonlendirici_hizi} S:{self.klape_hizi}")
                    self.seri_nesnesi.write(f"kh{self.konveyor_hizi}\n".encode())
                    time.sleep(0.05)
                    self.seri_nesnesi.write(f"yh{self.yonlendirici_hizi}\n".encode())
                    time.sleep(0.05)
                    self.seri_nesnesi.write(f"sh{self.klape_hizi}\n".encode())
                elif command in komutlar:
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
                            # Reset sonrası yeniden bağlantı kur ve parametreleri gönder
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
                    # Yeniden bağlandıktan sonra parametreleri tekrar gönder
                    time.sleep(1)  # Kart hazır olsun
                    self.parametre_gonder()
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