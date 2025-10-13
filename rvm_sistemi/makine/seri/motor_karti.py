import threading
import queue
import time
import serial

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_motor, log_error, log_success, log_warning, log_system

class MotorKart:
    def __init__(self, port_adi, callback=None, cihaz_adi="motor"):
        self.port_adi = port_adi  # örn: "/dev/ttyUSB0" (string)
        self.seri_nesnesi = None  # serial.Serial nesnesi burada tutulacak
        
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        self.port_yoneticisi = KartHaberlesmeServis()
        
        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200
        self.klape_flag = False
        
        self.running = False
        self.listen_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        self.saglikli = True  # Başlangıçta sağlıklı olarak başlat

        # DOĞRUDAN BAĞLANTIYI BAŞLAT
        self.portu_ac()

    # ... (diğer metodlarınızda değişiklik yok) ...

    def parametre_gonder(self):
        self.write_queue.put(("parametre_gonder", None))

    def parametre_degistir(self, konveyor=None, yonlendirici=None, klape=None):
        if konveyor is not None:
            self.konveyor_hizi = konveyor
        if yonlendirici is not None:
            self.yonlendirici_hizi = yonlendirici
        if klape is not None:
            self.klape_hizi = klape

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
        self.write_queue.put(("reset", None))  # Write queue üzerinden gönder

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

    def dinlemeyi_baslat(self):
        if not self.running:
            self.running = True
            self.listen_thread = threading.Thread(target=self._dinle, daemon=True)
            self.listen_thread.start()
            
            self.write_thread = threading.Thread(target=self._yaz, daemon=True)
            self.write_thread.start()

    def dinlemeyi_durdur(self):
        print(f"[{self.cihaz_adi}] Dinleme durduruluyor.")
        self.running = False
        current_thread = threading.current_thread()
        if self.listen_thread and self.listen_thread.is_alive() and self.listen_thread != current_thread:
            self.listen_thread.join()
        if self.write_thread and self.write_thread.is_alive() and self.write_thread != current_thread:
            # Kuyruğa özel bir "bitir" komutu ekleyerek thread'in sonlanmasını sağla
            self.write_queue.put(("exit", None))
            self.write_thread.join()
        self.listen_thread = None
        self.write_thread = None


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
                    "parametre_gonder": lambda: [
                        self.seri_nesnesi.write(f"kh{self.konveyor_hizi}\n".encode()),
                        time.sleep(0.05),
                        self.seri_nesnesi.write(f"yh{self.yonlendirici_hizi}\n".encode()),
                        time.sleep(0.05),
                        self.seri_nesnesi.write(f"sh{self.klape_hizi}\n".encode())
                    ],
                    "motorlari_aktif_et": b"aktif\n",
                    "motorlari_iptal_et": b"iptal\n",
                    "konveyor_ileri": b"kmi\n",
                    "konveyor_geri": b"kmg\n",
                    "konveyor_dur": b"kmd\n",
                    "konveyor_problem_var": b"pv\n",
                    "konveyor_problem_yok": b"py\n",
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

                if command in komutlar:
                    if command == "parametre_gonder":
                        komutlar[command]()  # Lambda fonksiyonunu çalıştır
                    else:
                        self.seri_nesnesi.write(komutlar[command])

            except queue.Empty:
                continue
            except (serial.SerialException, OSError) as e:
                print(f"[{self.cihaz_adi}] YAZMA HATASI: {e}")
                self._baglanti_kontrol()
                break # Döngüyü kır, yeni thread başlayacak

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

    # ... (ping, getir_saglik_durumu, _mesaj_isle metodları) ...

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

    def getir_saglik_durumu(self):
        return self.saglikli

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():  # Mesajın yazdırılabilir olup olmadığını kontrol edin
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        if mesaj.lower() == "pong":
            self.saglikli = True
        if self.callback:
            self.callback(mesaj)

    # === DÜZELTİLMİŞ YENİDEN BAĞLANTI FONKSİYONU ===
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
        
