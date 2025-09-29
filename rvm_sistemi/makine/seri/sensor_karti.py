import threading
import queue
import time
import serial
from .port_yonetici import KartHaberlesmeServis
from .mesaj_kanali import mesaj_kuyrugu
import asyncio

class SensorKart:
    def __init__(self, port, callback=None, cihaz_adi="Bilinmeyen Kart", vid=None, pid=None):
        self.port = port
        self.callback = callback
        self.running = False
        self.listen_thread = None
        self.write_queue = queue.Queue()
        self.write_thread = None
        self.saglikli = False
        self.cihaz_adi = cihaz_adi
        self.vid = vid
        self.pid = pid
        self.port_yoneticisi = KartHaberlesmeServis()
        self.thread_lock = threading.Lock()

    def loadcell_olc(self): self.write_queue.put(("loadcell_olc", None))
    def teach(self): self.write_queue.put(("teach", None))
    def led_ac(self): self.write_queue.put(("led_ac", None))
    def led_kapat(self): self.write_queue.put(("led_kapat", None))
    def tare(self): self.write_queue.put(("tare", None))
    def reset(self): self.write_queue.put(("reset", None))
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

    def dinlemeyi_baslat(self):
        with self.thread_lock:
            print("[LOG] Dinleme başlatılıyor...")

            self.dinlemeyi_durdur()  # Eski thread'leri durdur

            self.running = True
            self.listen_thread = threading.Thread(target=self._dinle, daemon=True)
            self.listen_thread.start()

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
        while self.running:
            try:
                command, data = self.write_queue.get(timeout=0.1)

                if not self.port or not self.port.is_open:
                    print(f"[LOG] Port kapalı. Komut iletilemedi: {command}")
                    continue

                komutlar = {
                    "loadcell_olc": b"lao\n",
                    "teach": b"gst\n",
                    "led_ac": b"as\n",
                    "led_kapat": b"ad\n",
                    "tare": b"tare\n",
                    "reset": b"reset\n",
                    "ping": b"ping\n"
                }

                if command in komutlar:
                    self.port.write(komutlar[command])
                    print(f"[LOG] Komut gönderildi: {command}")

                time.sleep(0.1)

            except queue.Empty:
                continue
            except serial.SerialException as e:
                print(f"[LOG] Yazma hatası: {e}")
                self._baglanti_kontrol()
            except Exception as e:
                print(f"[LOG] Beklenmeyen yazma hatası: {e}")

    def _dinle(self):
        while self.running:
            try:
                if self.port and self.port.in_waiting > 0:
                    data = self.port.readline().decode(errors='ignore').strip()
                    if data:
                        print(f"[LOG] Gelen veri: {data}")
                        self._mesaj_isle(data)
                        loop = asyncio.get_running_loop()  # Py3.7+: aktif loop varsa
                        loop.call_soon_threadsafe(mesaj_kuyrugu.put_nowait, data)
            except serial.SerialException as e:
                print(f"[LOG] Dinleme kesildi: {e}")
                self._baglanti_kontrol()  # Port bağlantısı kesildiğinde yeniden bağlanmayı dene
                break
            except Exception as e:
                print(f"[LOG] Okuma hatası: {e}")

    def _baglanti_kontrol(self):
        print(f"[LOG] {self.cihaz_adi} yeniden bağlanıyor...")
        self.dinlemeyi_durdur()  # Tüm thread'leri durdur
        retry_count = 0
        max_retries = 10  # Maksimum yeniden deneme sayısı
        while retry_count < max_retries:
            try:
                basarili, mesaj, yeni_port = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
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
                        print(f"[LOG] {self.cihaz_adi} bağlantı kuruldu.")
                        return
                    elif isinstance(yeni_port, dict) and self.cihaz_adi in yeni_port:
                        if self.port and self.port.is_open:
                            try:
                                self.port.close()
                                time.sleep(1)  # Portun serbest bırakılması için bekleme süresi
                            except Exception as e:
                                print(f"[LOG] Port kapatma hatası: {e}")
                        self.port = yeni_port[self.cihaz_adi]
                        self.dinlemeyi_baslat()  # Thread'leri yeniden başlat
                        print(f"[LOG] {self.cihaz_adi} bağlantı kuruldu.")
                        return
                print("[LOG] Port bulunamadı. Yeniden deneniyor...")
                retry_count += 1
                time.sleep(5)
            except serial.SerialException as e:
                print(f"[LOG] Seri bağlantı hatası: {e}")
                retry_count += 1
                time.sleep(5)
            except Exception as e:
                print(f"[LOG] Bağlantı hatası: {e}")
                retry_count += 1
                time.sleep(5)
        print(f"[LOG] {self.cihaz_adi} bağlantı kurulamadı. Maksimum deneme sayısına ulaşıldı.")

    def _mesaj_isle(self, mesaj):
        if not mesaj.isprintable():  # Mesajın yazdırılabilir olup olmadığını kontrol edin
            print("[LOG] Geçersiz mesaj alındı, atlanıyor.")
            return

        if mesaj.lower() == "pong":
            self.saglikli = True
        if self.callback:
            self.callback(mesaj)
