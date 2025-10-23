"""
example_usage.py - Yeni Seri Haberleşme Sisteminin Örnek Kullanımı

Bu dosya yeni sistemin nasıl kullanılacağını gösterir.
"""

import time
from rvm_sistemi.makine.seri.motor_karti import MotorKart
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
from rvm_sistemi.makine.seri.simple_port_manager import SimplePortManager
from rvm_sistemi.makine.seri.simple_health_monitor import SimpleHealthMonitor


# ============ CALLBACK FONKSİYONLARI ============

def motor_callback(message: str):
    """Motor kartından gelen mesajları işle"""
    print(f"[MOTOR] {message}")

    # Örnek: Konveyör metraj pozisyonu
    if message == "kmp":
        print("[MOTOR] Konveyör metraj pozisyonuna ulaştı")

    # Örnek: Yönlendirici sensör giriş
    elif message == "ysi":
        print("[MOTOR] Nesne yönlendirici sensörüne girdi")

    # Örnek: Yönlendirici motor komple
    elif message == "ymk":
        print("[MOTOR] Yönlendirici hedefine ulaştı")


def sensor_callback(message: str):
    """Sensor kartından gelen mesajları işle"""
    print(f"[SENSOR] {message}")

    # Örnek: Giriş sensörü input
    if message == "gsi":
        print("[SENSOR] Nesne giriş sensörüne geldi")

    # Örnek: Ağırlık ölçümü
    elif message.startswith("a:"):
        agirlik = float(message.split(":")[1])
        print(f"[SENSOR] Ağırlık: {agirlik}g")

    # Örnek: Doluluk oranı
    elif message.startswith("do#"):
        print(f"[SENSOR] Doluluk: {message}")


# ============ ANA FONKSİYON ============

def main():
    """Ana fonksiyon"""

    print("\n" + "="*60)
    print("YENİ SERİ HABERLEŞME SİSTEMİ - ÖRNEK KULLANIM")
    print("="*60 + "\n")

    # ============ 1. PORT BULMA ============
    print("1️⃣ Port bulma...")

    port_manager = SimplePortManager()
    success, message, ports = port_manager.find_cards()

    if not success:
        print(f"❌ Hata: {message}")
        return

    print(f"✅ {message}")
    print(f"   Motor: {ports.get('motor', 'N/A')}")
    print(f"   Sensor: {ports.get('sensor', 'N/A')}")
    print()

    # ============ 2. KART OLUŞTURMA ============
    print("2️⃣ Kartları oluşturma...")

    motor = MotorKart(
        port_adi=ports.get("motor"),
        callback=motor_callback,
        cihaz_adi="motor"
    )

    sensor = SensorKart(
        port_adi=ports.get("sensor"),
        callback=sensor_callback,
        cihaz_adi="sensor"
    )

    print("✅ Kartlar oluşturuldu")
    print()

    # ============ 3. KARTLARI BAŞLATMA ============
    print("3️⃣ Kartları başlatma...")

    motor.start()
    sensor.start()

    print("✅ Kartlar başlatıldı")
    print("   Boot sequence otomatik olarak çalışacak...")
    print()

    # ============ 4. HAZIR OLMASINI BEKLEME ============
    print("4️⃣ Kartların hazır olmasını bekleme...")

    max_wait = 15  # saniye
    start_time = time.time()

    while time.time() - start_time < max_wait:
        motor_ready = motor.is_ready()
        sensor_ready = sensor.is_ready()

        print(f"   Motor: {motor.get_state().value:15} | Sensor: {sensor.get_state().value:15}", end="\r")

        if motor_ready and sensor_ready:
            print()
            print("✅ Kartlar hazır!")
            break

        time.sleep(0.5)
    else:
        print()
        print("⚠️ Timeout - Kartlar hazır olmadı")
        motor.stop()
        sensor.stop()
        return

    print()

    # ============ 5. HEALTH MONİTOR BAŞLATMA ============
    print("5️⃣ Health monitor başlatma...")

    health = SimpleHealthMonitor(cards={
        "motor": motor,
        "sensor": sensor
    })
    health.start()

    print("✅ Health monitor başlatıldı (5 saniyede bir ping)")
    print()

    # ============ 6. MOTOR PARAMETRELERİ ============
    print("6️⃣ Motor parametreleri ayarlama...")

    motor.parametre_degistir(
        konveyor=40,
        yonlendirici=100,
        klape=200
    )

    print("✅ Motor parametreleri ayarlandı")
    print()

    # ============ 7. MOTORLARI AKTİF ETME ============
    print("7️⃣ Motorları aktif etme...")

    motor.motorlari_aktif_et()
    time.sleep(0.5)

    print("✅ Motorlar aktif")
    print()

    # ============ 8. ÖRNEK KOMUTLAR ============
    print("8️⃣ Örnek komutlar...")

    # LED aç
    sensor.led_ac()
    time.sleep(1)

    # Konveyör ileri
    motor.konveyor_ileri()
    time.sleep(2)

    # Yönlendirici plastik
    motor.yonlendirici_plastik()
    time.sleep(2)

    # Klape metal
    motor.klape_metal()
    time.sleep(2)
    motor.klape_plastik()

    # Konveyör dur
    motor.konveyor_dur()

    print("✅ Örnek komutlar gönderildi")
    print()

    # ============ 9. SAĞLIK KONTROLÜ ============
    print("9️⃣ Sağlık kontrolü...")

    motor_health = motor.getir_saglik_durumu()
    sensor_health = sensor.getir_saglik_durumu()

    print(f"   Motor sağlıklı: {motor_health}")
    print(f"   Sensor sağlıklı: {sensor_health}")
    print()

    # ============ 10. BİR SÜRE ÇALIŞTIRMA ============
    print("🔟 30 saniye çalıştırma (health monitor aktif)...")

    try:
        for i in range(30):
            time.sleep(1)
            print(f"   {30-i} saniye kaldı...", end="\r")

        print()
        print("✅ Çalıştırma tamamlandı")
        print()

    except KeyboardInterrupt:
        print()
        print("⚠️ Kullanıcı tarafından durduruldu")
        print()

    # ============ 11. TEMIZLEME ============
    print("1️⃣1️⃣ Temizlik...")

    # Motorları iptal et
    motor.motorlari_iptal_et()
    time.sleep(0.5)

    # LED kapat
    sensor.led_kapat()
    time.sleep(0.5)

    # Health monitor durdur
    health.stop()

    # Kartları durdur
    motor.stop()
    sensor.stop()

    print("✅ Temizlik tamamlandı")
    print()

    print("="*60)
    print("ÖRNEK KULLANIM TAMAMLANDI! 🎉")
    print("="*60)


# ============ ADVANCED ÖRNEK: OTURUM YÖNETİMİ ============

def advanced_session_example():
    """Oturum yönetimi örneği"""

    print("\n" + "="*60)
    print("ADVANCED ÖRNEK: OTURUM YÖNETİMİ")
    print("="*60 + "\n")

    # Port bulma ve başlatma (kısaltılmış)
    port_manager = SimplePortManager()
    success, _, ports = port_manager.find_cards()

    if not success:
        return

    motor = MotorKart(port_adi=ports.get("motor"))
    sensor = SensorKart(port_adi=ports.get("sensor"))

    motor.start()
    sensor.start()

    # Hazır olmasını bekle
    time.sleep(10)

    # Health monitor
    health = SimpleHealthMonitor(cards={"motor": motor, "sensor": sensor})
    health.start()

    print("✅ Sistem hazır\n")

    # ============ OTURUM BAŞLATMA ============
    print("🎯 Oturum başlatılıyor...")

    # Oturum aktif - health monitor duraklat
    health.set_session_active(True)

    # Sensor kartına oturum başlat sinyali
    sensor.makine_oturum_var()

    # Motorları aktif et
    motor.motorlari_aktif_et()

    print("✅ Oturum aktif\n")

    # ============ OTURUM İŞLEMLERİ ============
    print("⚙️ Oturum işlemleri...")

    # Konveyör başlat
    motor.konveyor_ileri()

    # LED aç
    sensor.led_ac()

    # 10 saniye işlem yap
    time.sleep(10)

    print("✅ Oturum işlemleri tamamlandı\n")

    # ============ OTURUM BİTİŞİ ============
    print("🏁 Oturum sonlandırılıyor...")

    # Konveyör dur
    motor.konveyor_dur()

    # LED kapat
    sensor.led_kapat()

    # Sensor kartına oturum bitti sinyali
    sensor.makine_oturum_yok()

    # Motorları iptal et
    motor.motorlari_iptal_et()

    # Oturum pasif - health monitor devam et
    health.set_session_active(False)

    print("✅ Oturum sonlandırıldı\n")

    # Temizlik
    health.stop()
    motor.stop()
    sensor.stop()

    print("="*60)
    print("ADVANCED ÖRNEK TAMAMLANDI! 🎉")
    print("="*60)


# ============ PROGRAM BAŞLATMA ============

if __name__ == "__main__":
    # Basit örnek
    main()

    # Advanced örnek (isteğe bağlı)
    # advanced_session_example()
