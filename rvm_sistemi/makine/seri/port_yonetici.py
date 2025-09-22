# kart_haberlesme_servis.py

import serial
import time
from serial.tools import list_ports

class KartHaberlesmeServis:
    def __init__(self, baudrate=5000000):
        self.baudrate = baudrate
        self.sensor_port = None
        self.motor_port = None

    def baglan(self, sadece_kart=None):
        ports = list(list_ports.comports())
        bulunan_kartlar = {}

        if not ports:
            print("Hiçbir seri port bulunamadı!")
            return False, "Hiçbir seri port bulunamadı!", (None, None)

        for p in ports:
            try:
                ser = serial.Serial(p.device, self.baudrate, timeout=2)
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                success = False
                for _ in range(3):  # Her port için 3 defa dene
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
                            except:
                                cevap = ""
                            if cevap:
                                break
                        time.sleep(0.1)

                    if cevap in ['sensor', 'motor', 'guvenlik']:
                        print(f"{cevap} kartı {p.device} portunda bulundu.")
                        bulunan_kartlar[cevap] = ser
                        success = True
                        break  # Bu portta doğru cevap alındıysa başka deneme yapma

                if not success:
                    print(f"{p.device} portunda hiçbir kart bulunamadı.")
                    ser.close()

            except Exception as e:
                print(f"{p.device} portunda hata: {e}")
                return False, f"{p.device} portunda hata: {e}", (None, None)

        if sadece_kart:
            if sadece_kart in bulunan_kartlar:
                if sadece_kart == 'sensor':
                    self.sensor_port = bulunan_kartlar['sensor']
                elif sadece_kart == 'motor':
                    self.motor_port = bulunan_kartlar['motor']

                try:
                    bulunan_kartlar[sadece_kart].write(b'b\n')
                    print(f"{sadece_kart} kartı başarıyla bağlandı ve aktif edildi.")
                except Exception as e:
                    print(f"{sadece_kart} kartı için b komutu gönderilirken hata: {e}")
                    return False, f"{sadece_kart} kartı için b komutu gönderilirken hata: {e}", (None, None)

                return True, f"{sadece_kart} kartı başarıyla bağlandı.", bulunan_kartlar[sadece_kart]
            else:
                print(f"{sadece_kart} kartı bulunamadı!")
                return False, f"{sadece_kart} kartı bulunamadı!", (None, None)

        if 'sensor' in bulunan_kartlar and 'motor' in bulunan_kartlar:
            self.sensor_port = bulunan_kartlar['sensor']
            self.motor_port = bulunan_kartlar['motor']

            try:
                self.sensor_port.write(b'b\n')
                self.motor_port.write(b'b\n')
                print("Tüm kartlara bağlanıldı ve aktif edildi.")
            except Exception as e:
                print(f"b komutu gönderilirken hata: {e}")
                return False, f"b komutu gönderilirken hata: {e}", (None, None)

            return True, "Tüm kartlara bağlanıldı ve aktif edildi.", (self.sensor_port, self.motor_port)
        else:
            print("Gerekli kartlar bulunamadı (sensor ve motor ikisi de bağlanmalı)!")
            return False, "Gerekli kartlar bulunamadı (sensor ve motor ikisi de bağlanmalı)!", (None, None)

    def saglik_kontrol(self):
        durumlar = {}

        try:
            # Sensor kartı kontrol et
            if self.sensor_port:
                self.sensor_port.write(b'ping\n')
                time.sleep(0.5)
                if self.sensor_port.in_waiting > 0:
                    durumlar['sensor'] = True
                    print("Sensor kartı sağlıklı.")
                else:
                    durumlar['sensor'] = False
                    print("Sensor kart bağlantısı koptu, yeniden bağlanılıyor...")
                    self.baglan()
            else:
                durumlar['sensor'] = False
                print("Sensor kartı bağlı değil.")

            # Motor kartı kontrol et
            if self.motor_port:
                self.motor_port.write(b'ping\n')
                time.sleep(0.5)
                if self.motor_port.in_waiting > 0:
                    durumlar['motor'] = True
                    print("Motor kartı sağlıklı.")
                else:
                    durumlar['motor'] = False
                    print("Motor kart bağlantısı koptu, yeniden bağlanılıyor...")
                    self.baglan()
            else:
                durumlar['motor'] = False
                print("Motor kartı bağlı değil.")

        except Exception as e:
            print(f"Sağlık kontrolü sırasında hata: {e}")
            self.baglan()

        return durumlar
