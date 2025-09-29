import uvicorn
import asyncio
import schedule
import time

# Projenin diğer modüllerini doğru paket yolundan import et
#from rvm_sistemi.dimdb.sunucu import baglanti_sensor
#baglanti_sensor()
from rvm_sistemi.dimdb import istemci
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
from rvm_sistemi.makine.seri.motor_karti import MotorKart
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.makine.seri.mesaj_kanali import mesaj_kuyrugu
from rvm_sistemi.makine.durum_degistirici import durum_makinesi

sensor = None
motor = None

#baglanti_sensor()


async def run_heartbeat_scheduler():
    """Heartbeat'i periyodik olarak gönderen asenkron görev."""
    print("Heartbeat zamanlayıcı başlatıldı...")
    # schedule kütüphanesi asenkron görevleri doğrudan desteklemediği için
    # her tetiklendiğinde yeni bir asyncio task'ı oluşturuyoruz.
    schedule.every(60).seconds.do(lambda: asyncio.create_task(istemci.send_heartbeat()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

async def mesaj_kuyrugu_dinleyici():
    """Sensör mesaj kuyruğunu dinleyip durum makinesine ileten görev."""
    print("[LOG] Mesaj kuyruğu dinleyici başlatıldı...")
    while True:
        mesaj = await mesaj_kuyrugu.get()   # asyncio.Queue
        print("[ANA] dinleme:", mesaj, "| durum:", durum_makinesi.durum)
        durum_makinesi.olayi_isle(mesaj)


async def main():
    """
    Ana fonksiyon, Uvicorn sunucusunu ve heartbeat görevini başlatır.
    """
    global sensor, motor
    print("Uygulama başlatılıyor: Donanım bağlantıları kuruluyor...")



    yonetici = KartHaberlesmeServis()
    basarili, mesaj, portlar = yonetici.baglan()
    print(f"🛈 {mesaj}")
    print(f"🛈 Bulunan portlar: {portlar}")

    if "sensor" in portlar:
        sensor = SensorKart(portlar["sensor"])
        sensor.dinlemeyi_baslat()
        print("✅ Sensör kartı dinleniyor...")
    else:
        print("❌ Sensör kartı bulunamadı.")


    # FastAPI sunucusunu başlatmak için Uvicorn konfigürasyonu
    config = uvicorn.Config(
        "rvm_sistemi.dimdb.sunucu:app", 
        host="0.0.0.0", 
        port=4321, 
        log_level="info"
    )
    server = uvicorn.Server(config)

    # Heartbeat görevini başlat
    heartbeat_task = asyncio.create_task(run_heartbeat_scheduler())

    mesaj_task = asyncio.create_task(mesaj_kuyrugu_dinleyici())


    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    print("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    
    # Sunucuyu çalıştır (bu satır programı burada bekletir)
    await server.serve()

    # Sunucu kapandığında heartbeat görevini de durdur
    heartbeat_task.cancel()
    mesaj_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")

