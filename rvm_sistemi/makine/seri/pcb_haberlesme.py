from port_yonetici import KartHaberlesmeServis
from sensor_karti import SensorKart
from motor_karti import MotorKart
import time

motor = None  # Global variable to hold the motor instance

def sensor_callback(mesaj):
    global motor
    print(f"📥 SENSOR mesajı: {mesaj}")
    if mesaj.strip().lower() == "gsi":
        if motor:
            motor.konveyor_ileri()
        else:
            print("⚠️ Motor instance is not initialized.")
    elif mesaj.strip().lower() == "gso":
        if motor:
            motor.konveyor_dur()
    elif mesaj.strip().lower().startswith("a:"):
        agirlik = float(mesaj.split("a:")[1])
        print(agirlik)


def motor_callback(mesaj):
    print(f"📥 MOTOR mesajı: {mesaj}")

def main():
    global motor
    yonetici = KartHaberlesmeServis()
    basarili, mesaj, portlar = yonetici.baglan()
    print("🛈", mesaj)
    print("🛈 Bulunan portlar:", portlar)

    if "sensor" not in portlar:
        print("❌ Sensör kartı bulunamadı.")
        return

    sensor = SensorKart(portlar["sensor"], callback=sensor_callback, cihaz_adi="sensor")
    sensor.dinlemeyi_baslat()
    print("✅ Sensör kartı dinleniyor...")

    if "motor" not in portlar:
        print("❌ Motor kartı bulunamadı.")
        return

    motor = MotorKart(portlar["motor"], callback=motor_callback)
    motor.dinlemeyi_baslat()
    print("✅ Motor kartı dinleniyor...")

    while True:
        komut = input("\nKomut girin (t = teach, h = sağlık kontrolü, q = çıkış): ").strip().lower()

        if komut == "t":
            sensor.teach()
        if komut == "z":
            sensor.led_kapat()
        elif komut == "h":
            sensor.ping()
            time.sleep(1)
            durum = sensor.getir_saglik_durumu()
            print(f"🩺 Sensör sağlık durumu: {'🟢 SAĞLIKLI' if durum else '🔴 SAĞLIKSIZ'}")
        elif komut == "j":
            motor.ping()
            time.sleep(1)
            durum = motor.getir_saglik_durumu()
            print(f"🩺 Motor sağlık durumu: {'🟢 SAĞLIKLI' if durum else '🔴 SAĞLIKSIZ'}")
        elif komut == "q":
            print("⏹ Program sonlandırılıyor...")
            break
        elif komut == "i":
            motor.konveyor_ileri()
        elif komut == "g":
            motor.konveyor_geri()
        elif komut == "d":
            motor.konveyor_dur()
        elif komut == "a":
            motor.motorlari_aktif_et()
        elif komut == "p":
            motor.yonlendirici_plastik()
        elif komut == "c":
            motor.yonlendirici_cam()
        else:
            print("⚠️ Geçersiz komut.")

    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()

if __name__ == "__main__":
    main()
