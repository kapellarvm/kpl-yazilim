# motor_kart.py

import threading
import queue
import time
import serial  # Eksik kütüphane eklendi

from port_yonetici import KartHaberlesmeServis  # Port yöneticisi için doğru import

class MotorKart:
    def __init__(self, port, callback=None):
        self.port = port
        self.callback = callback  # Ana koddan atanacak işleyici

        # Default parametreler
        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200

        self.klape_flag = False

        self.running = False
        self.listen_thread = None
        
        # Yazma kuyruğu ve thread'i
        self.write_queue = queue.Queue()
        self.write_thread = None

        self.saglikli = True  # Sağlık durumu başlangıçta sağlıklı

        self.port_yoneticisi = KartHaberlesmeServis()  # Port yöneticisi eklendi

    def parametre_gonder(self):
        self.write_queue.put(("parametre_gonder", None))

    def parametre_degistir(self, konveyor=None, yonlendirici=None, klape=None):
        if konveyor is not None:
            self.konveyor_hizi = konveyor
        if yonlendirici is not None:
            self.yonlendirici_hizi = yonlendirici
        if klape is not None:
            self.klape_hizi = klape

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

    def klape_plastik(self):
        if self.klape_flag:
            self.write_queue.put(("klape_plastik", None))
            self.klape_flag = False

    def dinlemeyi_baslat(self):
        if not self.running:
            self.running = True
            self.listen_thread = threading.Thread(target=self._dinle, daemon=True)
            self.listen_thread.start()
            
            # Yazma thread'ini başlat
            self.write_thread = threading.Thread(target=self._yaz, daemon=True)
            self.write_thread.start()

    def dinlemeyi_durdur(self):
        print("[LOG] Dinleme durduruluyor.")
        self.running = False
        current_thread = threading.current_thread()
        if self.listen_thread and self.listen_thread != current_thread:
            self.listen_thread.join()
            self.listen_thread = None
        if self.write_thread and self.write_thread != current_thread:
            self.write_thread.join()
            self.write_thread = None

    def _yaz(self):
        """Yazma komutlarını sırayla işle"""
        while self.running:
            try:
                command, data = self.write_queue.get(timeout=0.1)
                
                if command == "parametre_gonder":
                    self.port.write(f"kh{self.konveyor_hizi}\n".encode())
                    time.sleep(0.05)  # Komutlar arası kısa bekleme
                    self.port.write(f"yh{self.yonlendirici_hizi}\n".encode())
                    time.sleep(0.05)
                    self.port.write(f"sh{self.klape_hizi}\n".encode())
                    
                elif command == "motorlari_aktif_et":
                    self.port.write(b"aktif\n")
                    
                elif command == "motorlari_iptal_et":
                    self.port.write(b"iptal\n")
                    
                elif command == "konveyor_ileri":
                    self.port.write(b"kmi\n")
                    
                elif command == "konveyor_geri":
                    self.port.write(b"kmg\n")
                    
                elif command == "konveyor_dur":
                    self.port.write(b"kmd\n")
                    
                elif command == "yonlendirici_plastik":
                    self.port.write(b"ymp\n")
                    
                elif command == "yonlendirici_cam":
                    self.port.write(b"ymc\n")
                    
                elif command == "klape_metal":
                    self.port.write(b"smm\n")
                    
                elif command == "klape_plastik":
                    self.port.write(b"smp\n")
                
                elif command == "ping":
                    self.port.write(b"ping\n")
                    
                print(f"[MotorKart] Komut gönderildi: {command}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MotorKart] Yazma hatası: {e}")

    def _dinle(self):
        while self.running:
            try:
                if self.port and self.port.in_waiting > 0:
                    data = self.port.readline().decode(errors='ignore').strip()
                    if data:
                        if self.callback:
                            self.callback(data)
                        else:
                            print(f"[MotorKart] Gelen mesaj: {data}")
            except serial.SerialException as e:
                print(f"[MotorKart] Dinleme kesildi: {e}")
                self._baglanti_kontrol()  # Port bağlantısı kesildiğinde yeniden bağlanmayı dene
                break
            except Exception as e:
                print(f"[MotorKart] Okuma hatası: {e}")

    def ping(self):
        self.saglikli = False  # Sağlık durumunu her ping öncesi sıfırla
        self.write_queue.put(("ping", None))

        # Sağlık durumunu kontrol etmek için bir süre bekle
        for _ in range(10):  # Maksimum 1 saniye (10 x 0.1 saniye)
            time.sleep(0.1)
            if self.saglikli:
                break

        if self.saglikli:
            print(f"[LOG] MotorKart sağlıklı.")
        else:
            print(f"[LOG] MotorKart sağlıksız, bağlantı sıfırlanıyor...")
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

            for _ in range(10):  # Maksimum 1 saniye (10 x 0.1 saniye)
                time.sleep(0.1)
                if self.saglikli:
                    break

            if self.saglikli:
                print(f"[LOG] MotorKart sağlıklı.")
            else:
                print(f"[LOG] MotorKart hala sağlıksız.")

    def getir_saglik_durumu(self):
        return self.saglikli

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():  # Mesajın yazdırılabilir olup olmadığını kontrol edin
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        if mesaj.lower() == "pong":
            self.saglikli = True  # Sağlık durumu doğru şekilde güncelleniyor
            print("[LOG] Sağlık durumu güncellendi: Sağlıklı")
        if self.callback:
            self.callback(mesaj)

    def _baglanti_kontrol(self):
        print("[LOG] MotorKart yeniden bağlanıyor...")
        self.dinlemeyi_durdur()  # Tüm thread'leri durdur

        while True:  # Sonsuz döngü, bağlantı kurulana kadar devam eder
            try:
                basarili, mesaj, yeni_port = self.port_yoneticisi.baglan(cihaz_adi="motor")
                if basarili:
                    if isinstance(yeni_port, serial.Serial):
                        if self.port and self.port.is_open:
                            try:
                                self.port.close()
                                time.sleep(1)  # Portun serbest bırakılması için bekleme süresi
                            except Exception as e:
                                print(f"[LOG] Port kapatma hatası: {e}")
                        self.port = yeni_port
                        self.dinlemeyi_baslat()  # Thread'leri yeniden başlat
                        print("[LOG] MotorKart bağlantı kuruldu.")
                        return
                    elif isinstance(yeni_port, dict) and "motor" in yeni_port:
                        if self.port and self.port.is_open:
                            try:
                                self.port.close()
                                time.sleep(1)  # Portun serbest bırakılması için bekleme süresi
                            except Exception as e:
                                print(f"[LOG] Port kapatma hatası: {e}")
                        self.port = yeni_port["motor"]
                        self.dinlemeyi_baslat()  # Thread'leri yeniden başlat
                        print("[LOG] MotorKart bağlantı kuruldu.")
                        return
                print("[LOG] Port bulunamadı. Yeniden deneniyor...")
                time.sleep(5)  # 5 saniye bekle ve tekrar dene
            except serial.SerialException as e:
                print(f"[LOG] Seri bağlantı hatası: {e}")
                time.sleep(5)
            except Exception as e:
                print(f"[LOG] Bağlantı hatası: {e}")
                time.sleep(5)