import uvicorn
import asyncio
import time

from rvm_sistemi.dimdb import dimdb_istemcisi
from rvm_sistemi.utils.logger import rvm_logger, log_system, log_dimdb, log_motor, log_sensor, log_oturum, log_error, setup_exception_handler
from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
from rvm_sistemi.makine.seri.motor_karti import MotorKart
from rvm_sistemi.makine.senaryolar import oturum_yok, oturum_var
from rvm_sistemi.makine.durum_degistirici import durum_makinesi
from rvm_sistemi.makine import kart_referanslari
from rvm_sistemi.zamanli_gorevler import urun_guncelleyici
from rvm_sistemi.makine.modbus.modbus_istemci import GA500ModbusClient
from rvm_sistemi.makine.modbus.modbus_kontrol import init_motor_kontrol


motor = None
sensor = None


# Heartbeat sistemi artık heartbeat_servis.py modülünde yönetiliyor

# Ürün güncelleme zamanlayıcısı - zamanli_gorevler modülüne taşındı
# run_product_update_scheduler() fonksiyonu kaldırıldı - artık urun_guncelleyici kullanılıyor


def sensor_callback(mesaj):
    global motor, sensor
    print(f"🔔 [SENSOR] MESAJ: {mesaj}")
    durum_makinesi.olayi_isle(mesaj)
    
def motor_callback(mesaj):
    global motor, sensor
    log_motor(f"HAM MESAJ: {mesaj}")
    durum_makinesi.olayi_isle(mesaj)


def modbus_callback(mesaj):
    """GA500 Modbus verilerini işle"""
    global motor, sensor
    #log_motor(f"MODBUS MESAJ: {mesaj}")
    # Modbus verilerini durum makinesine gönder
    durum_makinesi.modbus_mesaj(mesaj)


async def main():
    global motor, sensor   # ✅ Sadece 1 tane global burada olmalı

    yonetici = KartHaberlesmeServis()
    motor_kontrol = None  # Motor kontrol referansı

    # Elle port girildiyse buraya yaz
    ELLE_SENSOR_PORT = "" # !!Arama istiyorsak tırnak içlerini boş bırak / ELLE_SENSOR_PORT = ""
    ELLE_MOTOR_PORT = ""  # !!Arama istiyorsak tırnak içlerini boş bırak / ELLE_MOTOR_PORT = ""

    if ELLE_SENSOR_PORT and ELLE_MOTOR_PORT:
        print("✅ Elle port tanımlandı, port arama atlandı.")
        log_system("Elle port tanımlandı, port arama atlandı.")
        portlar = {
            "sensor": ELLE_SENSOR_PORT,
            "motor": ELLE_MOTOR_PORT
        }
    else:
        basarili, mesaj, portlar = yonetici.baglan()
        print("🛈", mesaj)
        print("🛈 Bulunan portlar:", portlar)
        log_system(f"Port arama sonucu: {mesaj}")
        log_system(f"Bulunan portlar: {portlar}")

        if "sensor" not in portlar:
            #print("❌ Sensör kartı bulunamadı.")
            log_error("Sensör kartı bulunamadı.")
            return

    # Sensör ve motoru başlat
    sensor = SensorKart(portlar["sensor"], callback=sensor_callback, cihaz_adi="sensor")
    sensor.dinlemeyi_baslat()
    log_sensor(f"Sensör kartı başlatıldı: {portlar['sensor']}")

    motor = MotorKart(portlar["motor"], callback=motor_callback, cihaz_adi="motor")
    motor.dinlemeyi_baslat()
    log_motor(f"Motor kartı başlatıldı: {portlar['motor']}")

    # GA500 Modbus Client ve Motor Kontrol Sistemini Başlat
    client = GA500ModbusClient(callback=modbus_callback, cihaz_adi="ga500")
    if client.connect():
        print("✅ GA500 Modbus bağlantısı başarılı")
        print("📊 Sürekli izleme başlatıldı (0.5s periyod)")
        print("─" * 50)
        
        # Motor kontrol sistemini başlat - Hibrit sistem (Modbus okuma + Dijital sürme)
        motor_kontrol = init_motor_kontrol(client, sensor)
        print("🔧 Motor kontrol sistemi başlatıldı (Hibrit: Modbus okuma + Dijital sürme)")
        
        # Sıkışma korumasını başlat
        motor_kontrol.start_sikisma_monitoring()
        print("🛡️ Sıkışma koruması başlatıldı (Ezici: 5A, Kırıcı: 7A, 2s süre, 3 deneme)")
        
        # Sürekli okuma thread'ini başlat
        client.start_continuous_reading()
        
        # Reset sonrası frekansları ayarla
        print("\n🔧 Reset sonrası frekans ayarları:")
        print("  └─ Sürücü 1: 50 Hz ayarlanıyor...")
        client.set_frequency(1, 50.0)
        print("  └─ Sürücü 2: 50 Hz ayarlanıyor...")
        client.set_frequency(2, 50.0)
        print("  ✅ Her iki sürücü de 50 Hz'e ayarlandı")
        time.sleep(2)  # Ayarların oturması için bekle
        
    else:
        print("❌ GA500 Modbus bağlantı hatası - sadece dijital kontrol modu")
        motor_kontrol = None

    # Referansları ayarla
    oturum_yok.motor_referansini_ayarla(motor)
    oturum_yok.sensor_referansini_ayarla(sensor)
    oturum_var.motor_referansini_ayarla(motor)
    oturum_var.sensor_referansini_ayarla(sensor)
    
    # Merkezi referans sistemine de kaydet
    kart_referanslari.motor_referansini_ayarla(motor)
    kart_referanslari.sensor_referansini_ayarla(sensor)
    
    # Motor kontrol referansını da oturum_var'a ayarla (otomatik ezici için)
    if motor_kontrol:
        oturum_var.motor_kontrol_referansini_ayarla(motor_kontrol)
        # Merkezi referans sistemine de kaydet
        kart_referanslari.ac_motor_kontrol_referansini_ayarla(motor_kontrol)

    # FastAPI sunucusunu başlat
    config = uvicorn.Config(
        "rvm_sistemi.api.main:app",
        host="0.0.0.0",
        port=4321,
        log_level="error"
    )
    server = uvicorn.Server(config)

    # Heartbeat görevini başlat (heartbeat_servis modülünden)
    from rvm_sistemi.api.servisler.heartbeat_servis import heartbeat_servis
    await heartbeat_servis.start_heartbeat()
    
    # Ürün güncelleme görevini başlat (zamanli_gorevler modülünden)
    product_update_task = asyncio.create_task(urun_guncelleyici.baslat())

    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    print("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    print("🔄 Ürün güncelleme zamanlayıcısı başlatıldı")
    
    log_system("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    log_system("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    log_system("Ürün güncelleme: Her 6 saatte bir otomatik")
    log_system("Ürün güncelleme zamanlayıcısı başlatıldı")

    await server.serve()

    # Sunucu kapandığında her şeyi durdur
    await heartbeat_servis.stop_heartbeat()
    product_update_task.cancel()
    urun_guncelleyici.durdur()
    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()
    
    # Motor kontrol sistemini temizle
    if motor_kontrol:
        motor_kontrol.cleanup()
        if client and client.is_connected:
            client.stop(1)
            client.stop(2)
            client.disconnect()


if __name__ == "__main__":
    # Exception handler'ı kur
    setup_exception_handler()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")
        log_system("Program sonlandırılıyor (KeyboardInterrupt)")
