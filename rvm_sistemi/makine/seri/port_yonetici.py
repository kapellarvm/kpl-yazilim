import serial
import time
from serial.tools import list_ports

class KartHaberlesmeServis:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate
        self.bagli_kartlar = {}

    def baglan(self, cihaz_adi=None):
        print("[LOG] port_yonetici.py -> KartHaberlesmeServis.baglan: baglan fonksiyonu çağrıldı.")
        ports = list(list_ports.comports())
        print(f"[LOG] port_yonetici.py -> KartHaberlesmeServis.baglan: Bulunan portlar: {ports}")
        bulunan_kartlar = {}

        if not ports:
            print("[LOG] port_yonetici.py -> KartHaberlesmeServis.baglan: Hiçbir seri port bulunamadı!")
            return False, "Hiçbir seri port bulunamadı!", {}

        for p in ports:
            try:
                print(f"[LOG] port_yonetici.py -> KartHaberlesmeServis.baglan: {p.device} portu açılıyor...")

                if p.device in self.bagli_kartlar:
                    ser = self.bagli_kartlar[p.device]
                    if ser.is_open:
                        print(f"[LOG] {p.device} portu zaten açık, kapatılıyor.")
                        ser.close()
                        time.sleep(0.5)

                time.sleep(1)  # Portu serbest bırakmak için
                ser = serial.Serial(p.device, self.baudrate, timeout=2)
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                for _ in range(3):
                    ser.write(b'reset\n')
                    time.sleep(2)
                    ser.write(b's\n')
                    time.sleep(0.5)
                    ser.write(b's\n')
                    time.sleep(0.5)

                    start_time = time.time()
                    cevap = ""
                    while time.time() - start_time < 3:
                        if ser.in_waiting > 0:
                            try:
                                cevap = ser.readline().decode(errors='ignore').strip().lower()
                                print(f"[LOG] {p.device} cevabı: {cevap}")
                            except Exception as e:
                                print(f"[LOG] cevap okuma hatası: {e}")
                                cevap = ""
                            if cevap:
                                break
                        time.sleep(0.1)

                    if cevap in ['sensor', 'motor', 'guvenlik']:
                        print(f"[LOG] -> {cevap} kartı {p.device} portunda bulundu.")
                        ser.write(b'b\n')
                        bulunan_kartlar[cevap] = ser
                        self.bagli_kartlar[cevap] = ser
                        if cihaz_adi == cevap:
                            return True, "Cihaz başarıyla bulundu.", ser
                        break
                    else:
                        ser.reset_input_buffer()

                else:
                    ser.close()
                    print(f"[LOG] {p.device} portunda kart bulunamadı.")

            except Exception as e:
                print(f"[LOG] {p.device} portunda hata: {e}")
                continue

        if bulunan_kartlar:
            return True, "Kartlar başarıyla bulundu.", bulunan_kartlar
        else:
            return False, "Hiçbir kart bulunamadı!", {}
