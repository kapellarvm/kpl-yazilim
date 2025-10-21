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
from rvm_sistemi.api.servisler.uyku_modu_servisi import uyku_modu_servisi
from rvm_sistemi.makine.seri.port_saglik_servisi import PortSaglikServisi


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
        print(f"🔧 Elle tanımlanan portlar: sensor={ELLE_SENSOR_PORT}, motor={ELLE_MOTOR_PORT}")
    else:
        # İlk port arama - USB reset aktif ve max 2 deneme, kritik kartlar: motor ve sensor
        basarili, mesaj, portlar = yonetici.baglan(
            try_usb_reset=True, 
            max_retries=2, 
            kritik_kartlar=["motor", "sensor"]
        )
        print("🛈", mesaj)
        print("🛈 Bulunan portlar:", portlar)
        log_system(f"Port arama sonucu: {mesaj}")
        log_system(f"Bulunan portlar: {portlar}")

        # Kritik kartların varlığını kontrol et
        eksik_kartlar = []
        if "sensor" not in portlar:
            eksik_kartlar.append("sensor")
        if "motor" not in portlar:
            eksik_kartlar.append("motor")
        
        if eksik_kartlar:
            eksik_liste = ", ".join(eksik_kartlar)
            print(f"❌ Kritik kartlar bulunamadı: {eksik_liste}")
            print(f"🔍 Bulunan kartlar: {list(portlar.keys()) if portlar else 'Hiçbiri'}")
            log_error(f"Kritik kartlar bulunamadı: {eksik_liste}")
            log_error(f"Bulunan kartlar: {list(portlar.keys()) if portlar else 'Hiçbiri'}")
            

            print("\n⚠️  Not: USB reset otomatik olarak denendi ancak başarısız oldu.")
            return

    # Sensör ve motoru başlat
    print(f"🔧 Sensör kartı başlatılıyor: {portlar['sensor']}")
    sensor = SensorKart(portlar["sensor"], callback=sensor_callback, cihaz_adi="sensor")
    sensor.dinlemeyi_baslat()
    log_sensor(f"Sensör kartı başlatıldı: {portlar['sensor']}")

    print(f"🔧 Motor kartı başlatılıyor: {portlar['motor']}")
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
        
        # Sürekli okuma thread'ini başlat
        client.start_continuous_reading()
        
        # Reset sonrası frekansları ayarla - Sadece ezici motor (slave 1)
        print("\n🔧 Reset sonrası frekans ayarları:")
        print("  └─ Ezici Sürücü (Slave 1): 50 Hz ayarlanıyor...")
        client.set_frequency(1, 50.0)
        print("  ✅ Ezici sürücü 50 Hz'e ayarlandı")
        time.sleep(2)  # Ayarların oturması için bekle
        
        # Sıkışma korumasını başlat (Modbus bağlantısı başarılı olduktan sonra)
        motor_kontrol.start_sikisma_monitoring()
        print("🛡️ Sıkışma koruması başlatıldı (Ezici: 5A, 2s süre, 3 deneme)")
        
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
    
    # Voltage Power Monitoring sistemini başlat
    from rvm_sistemi.api.servisler.voltage_power_monitoring import voltage_power_monitoring_servis
    from rvm_sistemi.api.servisler.ups_power_handlers import handle_power_failure, handle_power_restored
    
    # Modbus client referansını voltage monitoring'e geçir
    voltage_power_monitoring_servis.set_modbus_client(client)
    
    # Callback'leri ayarla
    voltage_power_monitoring_servis.set_callbacks(
        power_failure_callback=handle_power_failure,
        power_restored_callback=handle_power_restored
    )
    
    # Voltage monitoring'i başlat
    await voltage_power_monitoring_servis.start_monitoring()
    
    if client and client.is_connected:
        print("🔌 Voltage Power Monitoring sistemi aktif (Bus voltage izleme)")
        log_system("Voltage Power Monitoring sistemi aktif (Bus voltage izleme)")
    else:
        print("⚠️ Voltage Power Monitoring sistemi test modunda (Modbus bağlantısı yok)")
        log_system("Voltage Power Monitoring sistemi test modunda (Modbus bağlantısı yok)")
    
    # Ürün güncelleme görevini başlat (zamanli_gorevler modülünden)
    product_update_task = asyncio.create_task(urun_guncelleyici.baslat())
    
    # Uyku modu servisini başlat
    uyku_modu_servisi.sistem_referans_ayarla(oturum_var.sistem)
    uyku_modu_servisi.uyku_kontrol_baslat()
    log_system("Uyku modu servisi başlatıldı - 15 dakika sonra otomatik uyku modu")
    
    # Port sağlık servisini başlat (AKTİF)
    port_saglik_servisi = PortSaglikServisi(motor, sensor)
    port_saglik_servisi.servisi_baslat()
    log_system("Port sağlık servisi başlatıldı - Arka planda ping/pong kontrolü aktif")
    '''
    log_system("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    log_system("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    log_system("Ürün güncelleme: Her 6 saatte bir otomatik")
    log_system("Ürün güncelleme zamanlayıcısı başlatıldı") '''

    await server.serve()

    # Sunucu kapandığında her şeyi durdur
    await heartbeat_servis.stop_heartbeat()
    await voltage_power_monitoring_servis.stop_monitoring()
    uyku_modu_servisi.uyku_kontrol_durdur()
    if port_saglik_servisi:
        port_saglik_servisi.servisi_durdur()
    log_system("Tüm servisler durduruldu")
    product_update_task.cancel()
    urun_guncelleyici.durdur()
    sensor.dinlemeyi_durdur()
    motor.dinlemeyi_durdur()
    
    # Motor kontrol sistemini temizle
    if motor_kontrol:
        motor_kontrol.cleanup()
        if client and client.is_connected:
            client.stop(1)  # Sadece ezici motor (slave 1)
            client.disconnect()


if __name__ == "__main__":
    # Exception handler'ı kur
    setup_exception_handler()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")
        log_system("Program sonlandırılıyor (KeyboardInterrupt)")
