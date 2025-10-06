#!/usr/bin/env python3
"""
GSI/GSO Basit Timing Test
Ultralytics bağımlılığı olmadan test
"""

import time
import threading
import sys
import os

# Mock GoruntuIslemeServisi
class MockGoruntuIslemeServisi:
    def __init__(self):
        self.call_count = 0
        self.son_cagri = None
    
    def goruntu_yakala_ve_isle(self):
        self.call_count += 1
        self.son_cagri = time.time()
        print(f"📷 [GÖRÜNTÜ] İşleme başladı #{self.call_count} - {time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # Mock sonuç döndür
        from types import SimpleNamespace
        sonuc = SimpleNamespace()
        sonuc.tur = SimpleNamespace()
        sonuc.tur.value = 1  # PET
        sonuc.genislik_mm = 65.0
        sonuc.yukseklik_mm = 180.0
        sonuc.mesaj = "basarili"
        
        time.sleep(0.01)  # 10ms simülasyon - gerçek YOLO daha hızlı
        print(f"✅ [GÖRÜNTÜ] İşleme tamamlandı #{self.call_count}")
        return sonuc

# Mock Motor sınıfı
class MockMotor:
    def __init__(self):
        self.son_komut = None
        self.komut_zamani = None
        self.commands = []
    
    def konveyor_ileri(self):
        self.son_komut = "konveyor_ileri"
        self.komut_zamani = time.time()
        self.commands.append(("konveyor_ileri", self.komut_zamani))
        print(f"🔄 [MOTOR] Konveyör ileri - {time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def konveyor_dur(self):
        self.son_komut = "konveyor_dur"
        self.komut_zamani = time.time()
        self.commands.append(("konveyor_dur", self.komut_zamani))
        print(f"⏹️ [MOTOR] Konveyör dur - {time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def konveyor_geri(self):
        self.son_komut = "konveyor_geri"
        self.komut_zamani = time.time()
        self.commands.append(("konveyor_geri", self.komut_zamani))
        print(f"⏪ [MOTOR] Konveyör geri - {time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def motorlari_aktif_et(self):
        print("✅ [MOTOR] Motorlar aktif edildi")
    
    def klape_plastik(self):
        print("🟢 [MOTOR] Klape plastik konumu")
    
    def klape_metal(self):
        print("🔵 [MOTOR] Klape metal konumu")
    
    def yonlendirici_sensor_teach(self):
        print("📍 [MOTOR] Yönlendirici sensor öğretildi")

class MockSensor:
    def __init__(self):
        self.agirlik = 0
    
    def teach(self):
        print("📍 [SENSOR] Sensor öğretildi")
    
    def tare(self):
        print("⚖️ [SENSOR] Tare yapıldı")
    
    def led_ac(self):
        print("💡 [SENSOR] LED açıldı")
    
    def doluluk_oranı(self):
        print("📊 [SENSOR] Doluluk oranı ölçüldü")

# Basit sistem durumu 
class SistemDurumu:
    def __init__(self):
        self.motor_ref = None
        self.sensor_ref = None
        self.agirlik = None
        self.veri_senkronizasyon_listesi = []
        self.kabul_edilen_urunler = []
        self.onaylanan_urunler = []
        self.iade_sebep = None
        self.iade_etildi = False
        self.lojik_thread_basladi = False
        self.konveyor_durum_kontrol = False
        self.iade_lojik = False
        self.barkod_lojik = False
        self.gsi_lojik = False
        self.gsi_gecis_lojik = False
        self.gso_lojik = False
        self.ysi_lojik = False
        self.yso_lojik = False
        self.aktif_oturum = {"aktif": False, "sessionId": None, "userId": None, "paket_uuid_map": {}}
        self.son_islenen_urun = None

# Global sistem
sistem = SistemDurumu()
goruntu_isleme_servisi = MockGoruntuIslemeServisi()

# Basit lojik yöneticisi
def lojik_yoneticisi():
    global sistem, goruntu_isleme_servisi
    
    while True:
        try:
            # GSI lojik
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False
                sistem.gsi_gecis_lojik = True
                
                if sistem.iade_lojik:
                    print("🚫 [İADE AKTIF] Şişeyi Alınız.")
                    time.sleep(0.25)
                    sistem.motor_ref.konveyor_dur()
                else:
                    print("🔄 [LOJİK] GSI lojik işlemleri başlatıldı")
                    sistem.motor_ref.konveyor_ileri()
            
            # GSO lojik
            if sistem.gso_lojik:
                sistem.gso_lojik = False
                if sistem.iade_lojik:
                    print("🚫 [İADE AKTIF] Görüntü işleme atlanıyor")
                else:
                    if sistem.barkod_lojik:
                        if sistem.iade_lojik==False:
                            print("[GSO] Sistem Normal Çalışıyor. Görüntü İşleme Başlatılıyor.")
                            goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                            sistem.gsi_gecis_lojik = False
                        else:
                            print("🚫 [İADE AKTIF] Görüntü İşleme Başlatılamıyor.")
                    else:
                        print("🚫 [GSO] Barkod okunmadı, ürünü iade et.")
                        sistem.iade_lojik = True
            
            time.sleep(0.001)  # 1ms döngü - gerçeğe yakın
            
        except Exception as e:
            print(f"❌ Lojik hatası: {e}")
            time.sleep(0.1)

def mesaj_isle(mesaj):
    global sistem
    
    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        if not sistem.lojik_thread_basladi:
            print("🟢 [OTURUM] Aktif oturum başlatıldı")
            t1 = threading.Thread(target=lojik_yoneticisi, daemon=True)
            t1.start()
            sistem.lojik_thread_basladi = True
        
        sistem.iade_lojik = False
        sistem.barkod_lojik = False
        sistem.veri_senkronizasyon_listesi.clear()
        sistem.kabul_edilen_urunler.clear()
        sistem.onaylanan_urunler.clear()
        
        if sistem.motor_ref:
            sistem.motor_ref.motorlari_aktif_et()
        if sistem.sensor_ref:
            sistem.sensor_ref.tare()
            sistem.sensor_ref.led_ac()

    if mesaj == "gsi":
        sistem.gsi_lojik = True
    if mesaj == "gso":
        sistem.gso_lojik = True

def barkod_verisi_al(barcode):
    global sistem
    if sistem.iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    if sistem.barkod_lojik:
        print(f"⚠️ [BARKOD] Önceki barkod işlemesi tamamlanmadı: {barcode}")
        return

    sistem.barkod_lojik = True
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}")

def test_timing():
    """Ana timing testi"""
    global sistem, goruntu_isleme_servisi
    
    print("🚀 GSI/GSO TİMİNG TEST BAŞLADI")
    print("="*60)
    
    # Mock nesneleri oluştur
    mock_motor = MockMotor()
    mock_sensor = MockSensor()
    
    # Referansları ayarla
    sistem.motor_ref = mock_motor
    sistem.sensor_ref = mock_sensor
    
    # Oturumu başlat
    print("\n📋 [1] Oturum başlatılıyor...")
    mesaj_isle("oturum_var")
    time.sleep(0.1)  # Thread'in başlaması için bekle
    
    # Barkod simülasyonu
    print("\n📋 [2] Barkod simülasyonu...")
    barkod_verisi_al("1923026353360")
    time.sleep(0.05)
    
    # GSI timing testi
    print("\n🔄 [3] GSI Timing Testi...")
    gsi_times = []
    
    for i in range(3):
        print(f"\n   Test {i+1}/3:")
        
        gsi_start = time.time()
        print(f"   📡 GSI mesajı - {time.strftime('%H:%M:%S.%f')[:-3]}")
        mesaj_isle("gsi")
        
        # Motor komutunu bekle
        start_wait = time.time()
        while len(mock_motor.commands) <= i and (time.time() - start_wait) < 0.01:  # 10ms timeout
            time.sleep(0.0001)
        
        if len(mock_motor.commands) > i:
            gecikme = (mock_motor.commands[i][1] - gsi_start) * 1000
            gsi_times.append(gecikme)
            print(f"   ⚡ GSI gecikme: {gecikme:.3f}ms")
        else:
            print("   ❌ GSI timeout!")
        
        time.sleep(0.05)
    
    # GSO timing testi
    print("\n📷 [4] GSO Timing Testi...")
    gso_times = []
    
    for i in range(3):
        print(f"\n   Test {i+1}/3:")
        
        # Mock'u sıfırla
        goruntu_isleme_servisi = MockGoruntuIslemeServisi()
        
        gso_start = time.time()
        print(f"   📡 GSO mesajı - {time.strftime('%H:%M:%S.%f')[:-3]}")
        mesaj_isle("gso")
        
        # Görüntü işleme çağrısını bekle
        start_wait = time.time()
        while goruntu_isleme_servisi.son_cagri is None and (time.time() - start_wait) < 0.01:  # 10ms timeout
            time.sleep(0.0001)
        
        if goruntu_isleme_servisi.son_cagri:
            gecikme = (goruntu_isleme_servisi.son_cagri - gso_start) * 1000
            gso_times.append(gecikme)
            print(f"   ⚡ GSO gecikme: {gecikme:.3f}ms")
        else:
            print("   ❌ GSO timeout!")
        
        time.sleep(0.05)
    
    # Sonuçları göster
    print("\n📊 TEST SONUÇLARI")
    print("="*40)
    
    if gsi_times:
        gsi_ort = sum(gsi_times) / len(gsi_times)
        gsi_min = min(gsi_times)
        gsi_max = max(gsi_times)
        print(f"🔄 GSI Gecikme - Ort: {gsi_ort:.3f}ms, Min: {gsi_min:.3f}ms, Max: {gsi_max:.3f}ms")
    
    if gso_times:
        gso_ort = sum(gso_times) / len(gso_times)
        gso_min = min(gso_times)
        gso_max = max(gso_times)
        print(f"📷 GSO Gecikme - Ort: {gso_ort:.3f}ms, Min: {gso_min:.3f}ms, Max: {gso_max:.3f}ms")
    
    # Performans değerlendirmesi
    print("\n💡 PERFORMANS DEĞERLENDİRMESİ")
    print("="*50)
    
    if gso_times:
        avg_gso = sum(gso_times) / len(gso_times)
        
        if avg_gso < 1.0:
            print(f"✅ GSO performansı MÜKEMMEL ({avg_gso:.3f}ms)")
        elif avg_gso < 2.0:
            print(f"✅ GSO performansı İYİ ({avg_gso:.3f}ms)")
        else:
            print(f"⚠️ GSO performansı ORTA ({avg_gso:.3f}ms)")
        
        print(f"\n🎯 Global shutter kamera analizi:")
        print(f"   💨 Şişe hızı: 50mm/s varsayımı")
        print(f"   📏 Konum hatası: {avg_gso * 0.05:.4f}mm")
        print(f"   🎯 Hedef: <1ms (<0.05mm hata)")
        
        if avg_gso * 0.05 < 0.1:
            print("   ✅ Konum hassasiyeti mükemmel!")
        else:
            print("   ⚠️ Konum hassasiyeti geliştirilmeli")

if __name__ == "__main__":
    try:
        test_timing()
        print("\n✅ Test tamamlandı!")
    except KeyboardInterrupt:
        print("\n⏹️ Test kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()