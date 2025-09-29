
from seri.port_yonetici import KartHaberlesmeServis
from seri.sensor_karti import SensorKart
from seri.motor_karti import MotorKart
import time
from mod_degistirici import durum_makinesi
from senaryolar import oturum_yok, oturum_var

motor = None  # Global motor nesnesi

def sensor_callback(mesaj):
    global motor
    print(f"📥 SENSOR mesajı: {mesaj}")
    # Mesajı DurumMakinesi'ne ilet
    durum_makinesi.olayi_isle(mesaj)

    # Eski doğrudan motor kontrolü kaldırıldı, işlemler senaryolara taşınacak


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



    motor = MotorKart(portlar["motor"])
    motor.dinlemeyi_baslat()


    # Motor referansını senaryolara aktar
    oturum_yok.motor_referansini_ayarla(motor)

    while True:
        komut = input("\nKomut girin (t = teach, h = sağlık kontrolü, n = oturum aç, m = oturum kapat, q = çıkış): ").strip().lower()

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
        elif komut == "n":
            durum_makinesi.durum_degistir("oturum_var")
            print("[MOD] Oturum açıldı, oturum_var moduna geçildi.")
        elif komut == "m":
            durum_makinesi.durum_degistir("oturum_yok")
            print("[MOD] Oturum kapatıldı, oturum_yok moduna geçildi.")
        else:
            print("⚠️ Geçersiz komut.")

    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()

if __name__ == "__main__":
    main()
