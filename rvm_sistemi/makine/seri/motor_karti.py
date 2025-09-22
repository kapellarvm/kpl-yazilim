# motor_kart.py

import threading
import queue
import time

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
        self.running = False
        if self.listen_thread:
            self.listen_thread.join()
        if self.write_thread:
            self.write_thread.join()

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
                    
                print(f"[MotorKart] Komut gönderildi: {command}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MotorKart] Yazma hatası: {e}")

    def _dinle(self):
        while self.running:
            if self.port.in_waiting > 0:
                try:
                    data = self.port.readline().decode(errors='ignore').strip()
                    if data:
                        if self.callback:
                            self.callback(data)
                        else:
                            print(f"[MotorKart] Gelen mesaj: {data}")
                except Exception as e:
                    print(f"[MotorKart] Okuma hatası: {e}") 