import uvicorn
import asyncio
import schedule
import time

from rvm_sistemi.dimdb import istemci
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
from rvm_sistemi.makine.seri.motor_karti import MotorKart
from rvm_sistemi.makine.senaryolar import oturum_yok, oturum_var
from rvm_sistemi.makine.durum_degistirici import durum_makinesi
from rvm_sistemi.makine.dogrulama import DogrulamaServisi
from rvm_sistemi.makine import kart_referanslari
from rvm_sistemi.zamanli_gorevler import urun_guncelleyici

dogrulama_servisi = DogrulamaServisi()

motor = None
sensor = None


async def run_heartbeat_scheduler():
    """Heartbeat'i periyodik olarak gönderen asenkron görev."""
    print("Heartbeat zamanlayıcı başlatıldı...")

    await istemci.send_heartbeat()

    schedule.every(60).seconds.do(lambda: asyncio.create_task(istemci.send_heartbeat()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

# Ürün güncelleme zamanlayıcısı - zamanli_gorevler modülüne taşındı
# run_product_update_scheduler() fonksiyonu kaldırıldı - artık urun_guncelleyici kullanılıyor


def sensor_callback(mesaj):
    global motor, sensor
    # Sensör mesajlarını hem durum makinesine hem de sunucuya gönder
    durum_makinesi.olayi_isle(mesaj)
    
    # Sunucudaki callback'i de çağır (eğer varsa)
    try:
        from rvm_sistemi.dimdb.sunucu import sensor_callback as sunucu_callback
        sunucu_callback(mesaj)
    except:
        pass


def motor_callback(mesaj):
    global motor, sensor
    print(f"\n📡 [MOTOR HAM MESAJ] {mesaj}")
    durum_makinesi.olayi_isle(mesaj)


async def main():
    global motor, sensor   # ✅ Sadece 1 tane global burada olmalı

    yonetici = KartHaberlesmeServis()

    # Elle port girildiyse buraya yaz
    ELLE_SENSOR_PORT = "" # !!Arama istiyorsak tırnak içlerini boş bırak / ELLE_SENSOR_PORT = ""
    ELLE_MOTOR_PORT = ""  # !!Arama istiyorsak tırnak içlerini boş bırak / ELLE_MOTOR_PORT = ""

    if ELLE_SENSOR_PORT and ELLE_MOTOR_PORT:
        print("✅ Elle port tanımlandı, port arama atlandı.")
        portlar = {
            "sensor": ELLE_SENSOR_PORT,
            "motor": ELLE_MOTOR_PORT
        }
    else:
        basarili, mesaj, portlar = yonetici.baglan()
        print("🛈", mesaj)
        print("🛈 Bulunan portlar:", portlar)

        if "sensor" not in portlar:
            print("❌ Sensör kartı bulunamadı.")
            return

    # Sensör ve motoru başlat
    sensor = SensorKart(portlar["sensor"], callback=sensor_callback, cihaz_adi="sensor")
    sensor.dinlemeyi_baslat()

    motor = MotorKart(portlar["motor"], callback=motor_callback, cihaz_adi="motor")
    motor.dinlemeyi_baslat()

    # Referansları ayarla
    oturum_yok.motor_referansini_ayarla(motor)
    oturum_yok.sensor_referansini_ayarla(sensor)
    oturum_var.motor_referansini_ayarla(motor)
    oturum_var.sensor_referansini_ayarla(sensor)
    
    # Merkezi referans sistemine de kaydet
    kart_referanslari.motor_referansini_ayarla(motor)
    kart_referanslari.sensor_referansini_ayarla(sensor)

    # FastAPI sunucusunu başlat
    config = uvicorn.Config(
        "rvm_sistemi.dimdb.sunucu:app",
        host="0.0.0.0",
        port=4321,
        log_level="info"
    )
    server = uvicorn.Server(config)

    # Heartbeat görevini başlat
    heartbeat_task = asyncio.create_task(run_heartbeat_scheduler())
    
    # Ürün güncelleme görevini başlat (zamanli_gorevler modülünden)
    #product_update_task = asyncio.create_task(urun_guncelleyici.baslat())

    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    print("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    print("🔄 Ürün güncelleme: Her 6 saatte bir otomatik")
    print("🔄 Ürün güncelleme zamanlayıcısı başlatıldı")

    await server.serve()

    # Sunucu kapandığında her şeyi durdur
    heartbeat_task.cancel()
    #product_update_task.cancel()
    urun_guncelleyici.durdur()
    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")
