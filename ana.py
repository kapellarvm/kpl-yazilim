import uvicorn
import asyncio
import schedule
import time

# Projenin diğer modüllerini doğru paket yolundan import et
#from rvm_sistemi.dimdb.sunucu import baglanti_sensor
#baglanti_sensor()
from rvm_sistemi.dimdb import istemci

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
from rvm_sistemi.makine.seri.motor_karti import MotorKart
from rvm_sistemi.makine.senaryolar import oturum_yok, oturum_var
from rvm_sistemi.makine.durum_degistirici import durum_makinesi
from rvm_sistemi.makine.dogrulama import DogrulamaServisi

dogrulama_servisi = DogrulamaServisi()

#baglanti_sensor()

motor = None 
sensor = None

# Test ve hızlı durum kontrolü için fonksiyonlar
def test_durumu():
    """Sistemin durumunu rapor eder"""
    return oturum_var.test_sistem_durumu()

def sistemi_resetle():
    """Sistemin durumunu tamamen sıfırlar"""
    return oturum_var.sistem_durumunu_sifirla()

def kuyruk_durumu():
    """Kuyruktaki ürünleri gösterir"""
    kuyruk = oturum_var.kabul_edilen_urunler
    print(f"Kuyrukta {len(kuyruk)} ürün var:")
    for i, urun in enumerate(kuyruk):
        print(f"  {i+1}. {urun}")

print("\n🔧 Hızlı Erişim Komutları:")
print("test_durumu()   - Sistem durum raporu")
print("sistemi_resetle() - Tüm durumları sıfırla")
print("kuyruk_durumu() - Kuyruktaki ürünleri listele")

async def run_heartbeat_scheduler():
    """Heartbeat'i periyodik olarak gönderen asenkron görev."""
    print("Heartbeat zamanlayıcı başlatıldı...")

    await istemci.send_heartbeat()

    # schedule kütüphanesi asenkron görevleri doğrudan desteklemediği için
    # her tetiklendiğinde yeni bir asyncio task'ı oluşturuyoruz.
    schedule.every(60).seconds.do(lambda: asyncio.create_task(istemci.send_heartbeat()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


def sensor_callback(mesaj):
    global motor,sensor
    # Mesajı DurumMakinesi'ne ilet
    durum_makinesi.olayi_isle(mesaj)

def motor_callback(mesaj):
    global motor,sensor
    # Mesajı DurumMakinesi'ne ilet
    durum_makinesi.olayi_isle(mesaj)

async def main():
    """
    Ana fonksiyon, Uvicorn sunucusunu ve heartbeat görevini başlatır.
    """
    global motor,sensor
    yonetici = KartHaberlesmeServis()
    basarili, mesaj, portlar = yonetici.baglan()
    print("🛈", mesaj)
    print("🛈 Bulunan portlar:", portlar)

    if "sensor" not in portlar:
        print("❌ Sensör kartı bulunamadı.")
        return

    sensor = SensorKart(portlar["sensor"], callback=sensor_callback, cihaz_adi="sensor")
    sensor.dinlemeyi_baslat()

    motor = MotorKart(portlar["motor"], callback=motor_callback, cihaz_adi="motor")
    motor.dinlemeyi_baslat()

    oturum_yok.motor_referansini_ayarla(motor)
    oturum_yok.sensor_referansini_ayarla(sensor)
    oturum_var.motor_referansini_ayarla(motor)
    oturum_var.sensor_referansini_ayarla(sensor)
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

    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    print("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    
    # Sunucuyu çalıştır (bu satır programı burada bekletir)
    await server.serve()

    # Sunucu kapandığında heartbeat görevini de durdur
    heartbeat_task.cancel()
    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")

