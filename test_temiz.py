#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GA500 Test - Temiz Terminal Output + Sensör Kartı Kontrolü + Motor Kontrol"""

from rvm_sistemi.makine.modbus.modbus_istemci import GA500ModbusClient
from rvm_sistemi.makine.modbus.modbus_kontrol import init_motor_kontrol
from rvm_sistemi.makine.seri.sensor_karti import SensorKart
import time
import threading
import sys

def sensor_callback(mesaj):
    """Sensör kartından gelen mesajları işle"""
    print(f"\n📡 [SENSOR] {mesaj}")

def input_handler(sensor_kart, ga500_client=None, motor_kontrol=None):
    """Terminal inputlarını işle - Temiz Format"""
    print("\n🎮 DIJITAL KONTROLLER:")
    print("┌─────────────────┬─────────────────┐")
    print("│ ei = Ezici İleri│ ki = Kırıcı İleri│")
    print("│ eg = Ezici Geri │ kg = Kırıcı Geri │") 
    print("│ ed = Ezici Dur  │ kd = Kırıcı Dur │")
    print("├─────────────────┼─────────────────┤")
    print("│ ei10= Ezici İ10s│ ki10= Kırıcı İ10s│")
    print("│ eg10= Ezici G10s│ kg10= Kırıcı G10s│")
    print("├─────────────────┼─────────────────┤")
    print("│ sikisma= Koruma │ durum= S.Durum  │")
    print("│ ariza1 = Arıza1 │ ariza2 = Arıza2 │")
    print("│ ping = Test     │ quit = Çıkış    │")
    print("└─────────────────┴─────────────────┘")
    print("\nGA500 Status: Sürekli güncelleniyor...")
    print("Komut yazın:")
    
    while True:
        try:
            komut = input().strip().lower()
            
            if komut == "quit" or komut == "q":
                print("🛑 Çıkış...")
                break
            elif komut == "ei":
                print("⚙️ Ezici İleri ✓")
                if motor_kontrol:
                    print("🔧 Motor kontrol kullanılıyor")
                    result = motor_kontrol.ezici_ileri()
                    print(f"📊 Ezici ileri sonucu: {result}")
                else:
                    print("📡 Sensör kartı kullanılıyor") 
                    sensor_kart.ezici_ileri()
            elif komut == "eg":
                print("⚙️ Ezici Geri ✓")
                if motor_kontrol:
                    print("🔧 Motor kontrol kullanılıyor")
                    result = motor_kontrol.ezici_geri()
                    print(f"📊 Ezici geri sonucu: {result}")
                else:
                    print("📡 Sensör kartı kullanılıyor")
                    sensor_kart.ezici_geri()
            elif komut == "ed":
                print("⏹️ Ezici Dur ✓")
                if motor_kontrol:
                    print("🔧 Motor kontrol kullanılıyor")
                    result = motor_kontrol.ezici_dur()
                    print(f"📊 Ezici dur sonucu: {result}")
                else:
                    print("📡 Sensör kartı kullanılıyor")
                    sensor_kart.ezici_dur()
            elif komut == "ei10":
                print("⏱️ Ezici İleri 10 Saniye ✓")
                if motor_kontrol:
                    motor_kontrol.ezici_ileri_10sn()
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "eg10":
                print("⏱️ Ezici Geri 10 Saniye ✓")
                if motor_kontrol:
                    motor_kontrol.ezici_geri_10sn()
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "ki":
                print("⚙️ Kırıcı İleri ✓")
                if motor_kontrol:
                    print("🔧 Motor kontrol kullanılıyor")
                    result = motor_kontrol.kirici_ileri()
                    print(f"📊 Kırıcı ileri sonucu: {result}")
                else:
                    print("📡 Sensör kartı kullanılıyor")
                    sensor_kart.kirici_ileri()
            elif komut == "kg":
                print("⚙️ Kırıcı Geri ✓")
                if motor_kontrol:
                    motor_kontrol.kirici_geri()
                else:
                    sensor_kart.kirici_geri()
            elif komut == "kd":
                print("⏹️ Kırıcı Dur ✓")
                if motor_kontrol:
                    motor_kontrol.kirici_dur()
                else:
                    sensor_kart.kirici_dur()
            elif komut == "ki10":
                print("⏱️ Kırıcı İleri 10 Saniye ✓")
                if motor_kontrol:
                    motor_kontrol.kirici_ileri_10sn()
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "kg10":
                print("⏱️ Kırıcı Geri 10 Saniye ✓")
                if motor_kontrol:
                    motor_kontrol.kirici_geri_10sn()
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "sikisma":
                if motor_kontrol:
                    current_status = motor_kontrol.get_sikisma_durumu()
                    if current_status['monitoring_aktif']:
                        print("🛡️ Sıkışma koruması durduruluyor...")
                        motor_kontrol.stop_sikisma_monitoring()
                    else:
                        print("🛡️ Sıkışma koruması başlatılıyor...")
                        motor_kontrol.start_sikisma_monitoring()
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "durum":
                if motor_kontrol:
                    sikisma_durumu = motor_kontrol.get_sikisma_durumu()
                    print("📊 SIKIŞMA DURUMU:")
                    print(f"├─ Monitoring: {'✅ Aktif' if sikisma_durumu['monitoring_aktif'] else '❌ Pasif'}")
                    print(f"├─ Ezici: {sikisma_durumu['ezici']['son_akim']:.1f}A / {sikisma_durumu['ezici']['akim_limiti']}A | Deneme: {sikisma_durumu['ezici']['kurtarma_denemesi']}/3")
                    print(f"└─ Kırıcı: {sikisma_durumu['kirici']['son_akim']:.1f}A / {sikisma_durumu['kirici']['akim_limiti']}A | Deneme: {sikisma_durumu['kirici']['kurtarma_denemesi']}/3")
                else:
                    print("❌ Motor kontrol mevcut değil")
            elif komut == "ariza1" and ga500_client:
                print("🔧 Sürücü 1 Arıza Temizleniyor...")
                if ga500_client.clear_fault(1):
                    print("✅ Sürücü 1 arızası temizlendi")
                else:
                    print("❌ Sürücü 1 arıza temizleme başarısız")
            elif komut == "ariza2" and ga500_client:
                print("🔧 Sürücü 2 Arıza Temizleniyor...")
                if ga500_client.clear_fault(2):
                    print("✅ Sürücü 2 arızası temizlendi")
                else:
                    print("❌ Sürücü 2 arıza temizleme başarısız")
            elif komut == "ping":
                print("📡 Sensör Ping ✓")
                sensor_kart.ping()
            elif komut:  # Boş değilse
                print("❌ Geçersiz! Komutlar: ei,eg,ed,ei10,eg10,ki,kg,kd,ki10,kg10,sikisma,durum,ariza1,ariza2,ping,quit")
                
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Input durduruldu")
            break

def main():
    print("🎯 GA500 + Sensör Kartı Test (Temiz Output)")
    print("=" * 50)
    
    # GA500 Modbus Client
    client = GA500ModbusClient()
    
    # Sensör Kartı
    sensor_kart = None
    try:
        sensor_kart = SensorKart("/dev/ttyUSB0", callback=sensor_callback, cihaz_adi="sensor")
        sensor_kart.dinlemeyi_baslat()
        print("✅ Sensör kartı bağlandı")
    except:
        try:
            sensor_kart = SensorKart("/dev/ttyUSB1", callback=sensor_callback, cihaz_adi="sensor")
            sensor_kart.dinlemeyi_baslat()
            print("✅ Sensör kartı bağlandı")
        except:
            print("⚠️ Sensör kartı bulunamadı")
    
    if client.connect():
        print("✅ GA500 Modbus bağlantısı başarılı")
        print("📊 Sürekli izleme başlatıldı (0.5s periyod)")
        print("─" * 50)
        
        # Motor kontrol sistemini başlat - Hibrit sistem (Modbus okuma + Dijital sürme)
        motor_kontrol = init_motor_kontrol(client, sensor_kart)
        print("🔧 Motor kontrol sistemi başlatıldı (Hibrit: Modbus okuma + Dijital sürme)")
        
        # Sıkışma korumasını başlat
        motor_kontrol.start_sikisma_monitoring()
        print("🛡️ Sıkışma koruması başlatıldı (Ezici: 5A, Kırıcı: 7A, 2s süre, 3 deneme)")
        
        try:
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
            
            # Input handler başlat
            if sensor_kart:
                input_handler(sensor_kart, client, motor_kontrol)
            else:
                print("\n⚠️ Sensör kartı yok, 10 saniye daha GA500 izleme...")
                time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n🛑 Test durduruldu (Ctrl+C)")
            
        finally:
            motor_kontrol.cleanup()  # Timer'ları temizle
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