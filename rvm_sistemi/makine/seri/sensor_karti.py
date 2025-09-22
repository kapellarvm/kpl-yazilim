# sensor_kart.py

import threading
import queue
import time

class SensorKart:
    def __init__(self, port, callback=None):
        self.port = port
        self.callback = callback  # Ana koddan gelecek işleyici fonksiyon

        self.running = False
        self.listen_thread = None
        
        # Yazma kuyruğu ve thread'i
        self.write_queue = queue.Queue()
        self.write_thread = None

    def loadcell_olc(self):
        self.write_queue.put(("loadcell_olc", None))

    def teach(self):
        self.write_queue.put(("teach", None))

    def tare(self):
        self.write_queue.put(("tare", None))

    def reset(self):
        self.write_queue.put(("reset", None))

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
                
                if command == "loadcell_olc":
                    self.port.write(b"lao\n")
                    time.sleep(0.1)  # Sensör komutları için bekleme
                    
                elif command == "teach":
                    self.port.write(b"gst\n")
                    time.sleep(0.1)
                    
                elif command == "tare":
                    self.port.write(b"tare\n")
                    time.sleep(0.1)
                    
                elif command == "reset":
                    self.port.write(b"reset\n")
                    time.sleep(0.1)
                    
                print(f"[SensorKart] Komut gönderildi: {command}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[SensorKart] Yazma hatası: {e}")

    def _dinle(self):
        while self.running:
            if self.port.in_waiting > 0:
                try:
                    data = self.port.readline().decode(errors='ignore').strip()
                    if data:
                        self._mesaj_isle(data)
                except Exception as e:
                    print(f"[SensorKart] Okuma hatası: {e}")

    def _mesaj_isle(self, mesaj):
        if self.callback:
            self.callback(mesaj) 