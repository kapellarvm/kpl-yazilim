#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GA500 Test - Sürekli Okuma ile + Sensör Kartı Kontrolü"""

from rvm_sistemi.makine.modbus.modbus_istemci import GA500ModbusClient
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
import time
import threading

def sensor_callback(mesaj):
    """Sensör kartından gelen mesajları işle"""
    print(f"📡 [SENSOR] {mesaj}")

def input_handler(sensor_kart):
    """Terminal inputlarını işle"""
    print("\n� KOMUTLAR:")
    print("  ei = Ezici İleri")
    print("  eg = Ezici Geri") 
    print("  ed = Ezici Dur")
    print("  ki = Kırıcı İleri")
    print("  kg = Kırıcı Geri")
    print("  kd = Kırıcı Dur")
    print("  ping = Sensör Test")
    print("  quit = Çıkış")
    print("─" * 40)
    
    while True:
        try:
            komut = input("Komut girin: ").strip().lower()
            
            if komut == "quit":
                break
            elif komut == "ei":
                print("⚙️ Ezici İleri...")
                sensor_kart.ezici_ileri()
            elif komut == "eg":
                print("⚙️ Ezici Geri...")
                sensor_kart.ezici_geri()
            elif komut == "ed":
                print("⏹️ Ezici Dur...")
                sensor_kart.ezici_dur()
            elif komut == "ki":
                print("⚙️ Kırıcı İleri...")
                sensor_kart.kirici_ileri()
            elif komut == "kg":
                print("⚙️ Kırıcı Geri...")
                sensor_kart.kirici_geri()
            elif komut == "kd":
                print("⏹️ Kırıcı Dur...")
                sensor_kart.kirici_dur()
            elif komut == "ping":
                print("📡 Sensör Ping...")
                sensor_kart.ping()
            else:
                print("❌ Geçersiz komut!")
                
        except (EOFError, KeyboardInterrupt):
            break

def main():
    print("🎯 GA500 + Sensör Kartı Test")
    print("=============================")
    
    # GA500 Modbus Client
    client = GA500ModbusClient()
    
    # Sensör Kartı (USB port otomatik bulunacak)
    sensor_kart = None
    try:
        # İlk USB port'u dene
        sensor_kart = SensorKart("/dev/ttyUSB0", callback=sensor_callback, cihaz_adi="sensor")
        sensor_kart.dinlemeyi_baslat()
        print("✅ Sensör kartı bağlandı")
    except:
        try:
            # İkinci USB port'u dene
            sensor_kart = SensorKart("/dev/ttyUSB1", callback=sensor_callback, cihaz_adi="sensor")
            sensor_kart.dinlemeyi_baslat()
            print("✅ Sensör kartı bağlandı")
        except:
            print("⚠️ Sensör kartı bulunamadı, sadece GA500 testi yapılacak")
    
    if client.connect():
        print("✅ GA500 Modbus bağlantısı başarılı")
        print("📊 0.5 saniye periyodla sürekli okuma başlatıldı...")
        print("─" * 60)
        
        try:
            # Sürekli okuma thread'ini başlat
            client.start_continuous_reading()
            
            # Input handler thread'ini başlat
            if sensor_kart:
                input_thread = threading.Thread(target=input_handler, args=(sensor_kart,), daemon=True)
                input_thread.start()
            
            # Sürücü 1'i çalıştır
            print("\n🔧 Sürücü 1: 50 Hz çalıştırılıyor...")
            client.run_forward(1)
            
            # 10 saniye okuma yap
            time.sleep(10)
            
            # Sürücü 1'i durdur
            print("\n⏹️ Sürücü 1: Durduruluyor...")
            client.stop(1)
            
            # Sürücü 2'yi test et
            print("\n🔧 Sürücü 2: 50 Hz çalıştırılıyor...")
            client.run_forward(2)
            
            # 10 saniye daha okuma yap
            time.sleep(10)
            
            # Sürücü 2'yi durdur
            print("\n⏹️ Sürücü 2: Durduruluyor...")
            client.stop(2)
            
            # Sensör kartı varsa input bekle
            if sensor_kart:
                print("\n🎮 Sensör kartı komutları için input bekleniyor...")
                print("   (Çıkmak için 'quit' yazın)")
                input_thread.join()
            else:
                # Sensör kartı yoksa 5 saniye daha bekle
                time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n🛑 Test kullanıcı tarafından durduruldu")
            
        finally:
            client.stop(1)
            client.stop(2)
            client.disconnect()
            if sensor_kart:
                sensor_kart.dinlemeyi_durdur()
            print("\n✅ Test tamamlandı")
            
    else:
        print("❌ GA500 Modbus bağlantı hatası")

if __name__ == "__main__":
    main()