import threading
import queue
import time
import serial

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_motor, log_error, log_success, log_warning, log_system

class MotorKart:
    def __init__(self, port, callback=None, cihaz_adi="motor"):
        self.port = port
        self.callback = callback
        self.cihaz_adi = cihaz_adi

        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200
        
        # self.seri_port'u try-except bloğu içine alarak başlangıç hatalarını yakala
        try:
            self.seri_port = serial.Serial(port, baudrate=115200, timeout=1)
        except serial.SerialException as e:
            print(f"[{self.cihaz_adi}] Başlangıçta port açılamadı: {e}")
            log_error(f"Başlangıçta port açılamadı: {e}")
            self.seri_port = None # Başlangıçta port yoksa None olarak ayarla

        self.klape_flag = False
        self.running = False
        self.listen_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        self.saglikli = True
        self.port_yoneticisi = KartHaberlesmeServis()

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
        """Motor kartını resetler"""
        try:
            if self.seri_port and self.seri_port.is_open:
                self.seri_port.write(b"reset\n")
                time.sleep(0.1)
        except Exception as e:
            print(f"[MOTOR] Reset hatası: {e}")

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

    def klape_metal(self):
        self.write_queue.put(("klape_metal", None))
        self.klape_flag = True

    def yonlendirici_sensor_teach(self):
        self.write_queue.put(("yonlendirici_sensor_teach", None))
        self.klape_flag = True

    

    def klape_plastik(self):
        if self.klape_flag:
            self.write_queue.put(("klape_plastik", None))
            self.klape_flag = False

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
                # Port kontrolü daha güvenli hale getir
                if not self.seri_port:
                    time.sleep(0.5)
                    continue
                
                # Port açık mı kontrol et - exception handle et
                try:
                    port_acik = self.seri_port.is_open
                except (AttributeError, OSError):
                    port_acik = False
                
                if not port_acik:
                    time.sleep(0.5)
                    continue

                # Queue'dan veri al - timeout ile
                try:
                    command, data = self.write_queue.get(timeout=1)
                except queue.Empty:
                    continue

                if command == "exit":
                    break

                # Komutları gönder - her biri için exception handle et
                try:
                    if command == "parametre_gonder":
                        self.seri_port.write(f"kh{self.konveyor_hizi}\n".encode())
                        time.sleep(0.05)
                        self.seri_port.write(f"yh{self.yonlendirici_hizi}\n".encode())
                        time.sleep(0.05)
                        self.seri_port.write(f"sh{self.klape_hizi}\n".encode())
                    elif command == "motorlari_aktif_et":
                        self.seri_port.write(b"aktif\n")
                    elif command == "motorlari_iptal_et":
                        self.seri_port.write(b"iptal\n")
                    elif command == "konveyor_ileri":
                        self.seri_port.write(b"kmi\n")
                    elif command == "konveyor_geri":
                        self.seri_port.write(b"kmg\n")
                    elif command == "konveyor_dur":
                        self.seri_port.write(b"kmd\n")
                    elif command == "konveyor_problem_var":
                        self.seri_port.write(b"pv\n")
                    elif command == "konveyor_problem_yok":
                        self.seri_port.write(b"py\n")
                    elif command == "yonlendirici_plastik":
                        self.seri_port.write(b"ymp\n")
                    elif command == "yonlendirici_cam":
                        self.seri_port.write(b"ymc\n")
                    elif command == "klape_metal":
                        self.seri_port.write(b"smm\n")
                    elif command == "klape_plastik":
                        self.seri_port.write(b"smp\n")
                    elif command == "yonlendirici_sensor_teach":
                        self.seri_port.write(b"yst\n")
                    elif command == "ping":
                        self.seri_port.write(b"ping\n")

                    print(f"[{self.cihaz_adi}] Komut gönderildi: {command}")
                    
                except (OSError, AttributeError) as e:
                    print(f"[{self.cihaz_adi}] Komut yazma hatası: {e}")
                    # Port problemi var, bağlantı kontrolünü tetikle
                    self._baglanti_kontrol()
                    break

            except serial.SerialException as e:
                print(f"[{self.cihaz_adi}] Yazma sırasında port hatası: {e}")
                self._baglanti_kontrol()
                break # Döngüyü kır, yeni thread başlayacak
            except (IndexError, ValueError) as e:
                # Deque pop hatası veya buffer problemi
                print(f"[{self.cihaz_adi}] Queue/Buffer hatası: {e}")
                time.sleep(0.1)
                continue
            except Exception as e:
                print(f"[{self.cihaz_adi}] Yazma hatası: {e}")
                time.sleep(0.5)

    def _dinle(self):
        while self.running:
            try:
                # Port kontrolü daha güvenli hale getir
                if not self.seri_port:
                    time.sleep(0.1)
                    continue
                    
                # Port açık mı kontrol et - exception handle et
                try:
                    port_acik = self.seri_port.is_open
                except (AttributeError, OSError):
                    port_acik = False
                
                if not port_acik:
                    time.sleep(0.1)
                    continue
                
                # Veri var mı kontrol et - exception handle et
                try:
                    veri_var = self.seri_port.in_waiting > 0
                except (AttributeError, OSError, serial.SerialException):
                    veri_var = False
                
                if veri_var:
                    try:
                        # Readline'ı timeout ile güvenli hale getir
                        data = self.seri_port.readline().decode(errors='ignore').strip()
                        if data:
                            self._mesaj_isle(data)
                    except (UnicodeDecodeError, AttributeError) as e:
                        print(f"[{self.cihaz_adi}] Decode hatası: {e}")
                        continue
                else:
                    # Port kapalıysa veya veri yoksa CPU'yu yormamak için kısa bir süre bekle
                    time.sleep(0.05)
                    
            except serial.SerialException as e:
                print(f"[{self.cihaz_adi}] Dinleme kesildi (port hatası): {e}")
                self._baglanti_kontrol()
                break # Döngüyü kır, çünkü _baglanti_kontrol yeni bir thread başlatacak
            except (IndexError, ValueError) as e:
                # Deque pop hatası veya buffer problemi
                print(f"[{self.cihaz_adi}] Buffer/Deque hatası: {e}")
                time.sleep(0.1)
                continue
            except Exception as e:
                print(f"[{self.cihaz_adi}] Okuma sırasında beklenmedik hata: {e}")
                time.sleep(1)

    # ... (ping, getir_saglik_durumu, _mesaj_isle metodları) ...

    def ping(self):
        self.saglikli = False
        self.write_queue.put(("ping", None))
        time.sleep(0.5) # Pong mesajının gelmesi için bekle

        if self.saglikli:
            print(f"[LOG] {self.cihaz_adi} sağlıklı.")
        else:
            print(f"[LOG] {self.cihaz_adi} sağlıksız, bağlantı sıfırlanıyor...")
            # Bağlantıyı sıfırlamak için doğrudan _baglanti_kontrol'ü çağırmak yerine
            # portu kapatarak _dinle ve _yaz thread'lerinin hata almasını sağlayabiliriz.
            # Bu, tek bir yerden yeniden bağlantı mantığını tetikler.
            if self.seri_port and self.seri_port.is_open:
                self.seri_port.close()

    def getir_saglik_durumu(self):
        return self.saglikli

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        #print(f"[{self.cihaz_adi}] Gelen mesaj: {mesaj}")
        if "pong" in mesaj.lower():
            self.saglikli = True
            print("[LOG] Sağlık durumu güncellendi: Sağlıklı")
        
        if self.callback:
            self.callback(mesaj)

    # === DÜZELTİLMİŞ YENİDEN BAĞLANTI FONKSİYONU ===
    def _baglanti_kontrol(self):
        # Bu fonksiyon başka bir thread tarafından çağrıldığında çakışmayı önle
        if hasattr(self, '_reconnecting') and self._reconnecting:
            return
        self._reconnecting = True

        try:
            print(f"[{self.cihaz_adi}] Yeniden bağlanma süreci başlatıldı...")
            self.dinlemeyi_durdur()

            # Eski seri port nesnesini güvenli bir şekilde kapat
            if self.seri_port:
                try:
                    if self.seri_port.is_open:
                        self.seri_port.close()
                except Exception as e:
                    print(f"[LOG] Eski portu kapatırken hata: {e}")
            
            self.seri_port = None

            # Bağlantı kurulana kadar döngüde kal
            while self.running: # ana.py'den program durdurulursa döngüden çıkabilmek için
                try:
                    print(f"[LOG] {self.cihaz_adi} için port aranıyor...")
                    basarili, mesaj, portlar = self.port_yoneticisi.baglan()

                    if basarili and self.cihaz_adi in portlar:
                        yeni_port_adi = portlar[self.cihaz_adi]
                        try:
                            # 1. Port adını (string) güncelle
                            self.port = yeni_port_adi
                            # 2. YENİ BİR serial.Serial NESNESİ OLUŞTUR
                            self.seri_port = serial.Serial(self.port, baudrate=115200, timeout=1)

                            print(f"[LOG] {self.cihaz_adi}, {self.port} portuna başarıyla yeniden bağlandı.")
                            self.dinlemeyi_baslat()  # Thread'leri yeniden başlat
                            return  # Başarılı olunca fonksiyondan çık

                        except serial.SerialException as e:
                            print(f"[LOG] Yeni port ({yeni_port_adi}) açılamadı: {e}")
                        except Exception as e:
                            print(f"[LOG] Yeniden bağlanma sırasında beklenmedik hata: {e}")
                    else:
                        print(f"[LOG] Port bulunamadı. Mesaj: {mesaj}")

                    print("[LOG] 5 saniye sonra tekrar denenecek.")
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"[LOG] Bağlantı kontrol döngüsünde hata: {e}")
                    time.sleep(5)
        
        finally:
            self._reconnecting = False