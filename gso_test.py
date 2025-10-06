#!/usr/bin/env python3
"""
GSI/GSO Test Kodu - Gerçek Sensor Kartı Entegrasyonu
Global shutter kamera için hassas timing testi
"""

import time
import threading
from unittest.mock import Mock
import sys
import os

# Sensor kartı importu için path ekle
sys.path.append('/home/sshuser/projects/kpl-yazilim')

try:
    from rvm_sistemi.makine.seri.sensor_karti import SensorKart
    from rvm_sistemi.makine.seri.motor_karti import MotorKart
    from rvm_sistemi.makine.goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi
    GERCEK_KARTLAR_VAR = True
    GERCEK_GORUNTU_VAR = True
    print("✅ Gerçek sensor/motor kartları ve görüntü işleme import edildi")
except ImportError as e:
    print(f"⚠️ Gerçek kartlar import edilemedi: {e}")
    GERCEK_KARTLAR_VAR = False
    GERCEK_GORUNTU_VAR = False

# Mock motor ve sensor sınıfları
class MockMotor:
    def __init__(self):
        self.son_komut = None
        self.komut_zamani = None
    
    def konveyor_ileri(self):
        self.son_komut = "konveyor_ileri"
        self.komut_zamani = time.time()
        print(f"🔄 [MOTOR] Konveyör ileri - {time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def konveyor_dur(self):
        self.son_komut = "konveyor_dur"
        self.komut_zamani = time.time()
        print(f"⏹️ [MOTOR] Konveyör dur - {time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def konveyor_geri(self):
        self.son_komut = "konveyor_geri"
        self.komut_zamani = time.time()
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

class MockGoruntuIsleme:
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
        
        time.sleep(0.1)  # YOLO işleme simülasyonu
        print(f"✅ [GÖRÜNTÜ] İşleme tamamlandı #{self.call_count}")
        return sonuc

# Test sistemi
class GercekKartTestSistemi:
    """Gerçek sensor ve motor kartları ile test sistemi"""
    
    def __init__(self):
        self.motor_cart = None
        self.sensor_cart = None
        self.goruntu_servisi = None
        self.gsi_zamanlar = []
        self.gso_zamanlar = []
        self.test_aktif = False
        
    def sensor_callback(self, mesaj):
        """Sensor kartından gelen mesajları işler"""
        zaman = time.time()
        print(f"📡 [SENSOR] Mesaj alındı: {mesaj} - {time.strftime('%H:%M:%S.%f')[:-3]}")
        
        if self.test_aktif:
            if mesaj.strip().lower() == "gsi":
                self.gsi_zamanlar.append(('gsi_alindi', zaman))
                print(f"🔄 [TEST] GSI tetiklendi, konveyör ileri başlatılıyor...")
                if self.motor_cart:
                    self.motor_cart.konveyor_ileri()
                    self.gsi_zamanlar.append(('konveyor_komutu', time.time()))
                    
            elif mesaj.strip().lower() == "gso":
                self.gso_zamanlar.append(('gso_alindi', zaman))
                print(f"📷 [TEST] GSO tetiklendi, görüntü işleme başlatılıyor...")
                # Gerçek görüntü işleme
                if GERCEK_GORUNTU_VAR and self.goruntu_servisi:
                    threading.Thread(target=self._gercek_goruntu_isleme, daemon=True).start()
                else:
                    # Fallback simülasyon
                    threading.Thread(target=self._goruntu_isleme_simule, daemon=True).start()
    
    def _gercek_goruntu_isleme(self):
        """Gerçek görüntü işleme servisi"""
        baslangic = time.time()
        self.gso_zamanlar.append(('goruntu_basladi', baslangic))
        print(f"📷 [GERÇEK GÖRÜNTÜ] İşleme başladı - {time.strftime('%H:%M:%S.%f')[:-3]}")
        
        try:
            # Gerçek YOLO işleme
            sonuc = self.goruntu_servisi.goruntu_yakala_ve_isle()
            
            bitis = time.time()
            self.gso_zamanlar.append(('goruntu_bitti', bitis))
            
            isleme_suresi = (bitis - baslangic) * 1000
            print(f"✅ [GERÇEK GÖRÜNTÜ] İşleme tamamlandı ({isleme_suresi:.1f}ms)")
            print(f"📊 [SONUÇ] Tür: {sonuc.tur.value}, Boyut: {sonuc.genislik_mm:.1f}x{sonuc.yukseklik_mm:.1f}mm")
            
        except Exception as e:
            bitis = time.time()
            self.gso_zamanlar.append(('goruntu_bitti', bitis))
            print(f"❌ [GERÇEK GÖRÜNTÜ] Hata: {e}")
            print(f"⏱️ [HATA] Süre: {(bitis-baslangic)*1000:.1f}ms")
    
    def _goruntu_isleme_simule(self):
        """Görüntü işleme simülasyonu"""
        baslangic = time.time()
        self.gso_zamanlar.append(('goruntu_basladi', baslangic))
        print(f"📷 [GÖRÜNTÜ] İşleme başladı - {time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # Gerçek YOLO işleme süresi simülasyonu (50-100ms)
        time.sleep(0.075)  # 75ms simülasyon
        
        bitis = time.time()
        self.gso_zamanlar.append(('goruntu_bitti', bitis))
        print(f"✅ [GÖRÜNTÜ] İşleme tamamlandı ({(bitis-baslangic)*1000:.1f}ms)")
    
    def kartlari_baslat(self):
        """Sensor ve motor kartlarını başlat"""
        print("🚀 Gerçek kartlar başlatılıyor...")
        
        try:
            # Sensor kartını başlat
            print("📡 Sensor kartı bağlanıyor...")
            self.sensor_cart = SensorKart("/dev/ttyUSB0", callback=self.sensor_callback)
            self.sensor_cart.dinlemeyi_baslat()
            time.sleep(1)
            
            # Motor kartını başlat  
            print("🔧 Motor kartı bağlanıyor...")
            self.motor_cart = MotorKart("/dev/ttyUSB1")
            self.motor_cart.dinlemeyi_baslat()
            time.sleep(1)
            
            # Görüntü işleme servisini başlat
            if GERCEK_GORUNTU_VAR:
                print("📷 Görüntü işleme servisi başlatılıyor...")
                self.goruntu_servisi = GoruntuIslemeServisi()
                print("✅ Görüntü işleme servisi hazır!")
            
            # Motorları aktif et
            self.motor_cart.motorlari_aktif_et()
            time.sleep(0.5)
            
            print("✅ Kartlar başarıyla bağlandı!")
            return True
            
        except Exception as e:
            print(f"❌ Kart bağlantı hatası: {e}")
            return False
    
    def kartlari_durdur(self):
        """Kartları güvenli şekilde durdur"""
        print("⏹️ Kartlar durduruluyor...")
        
        if self.motor_cart:
            self.motor_cart.konveyor_dur()
            self.motor_cart.motorlari_iptal_et()
            self.motor_cart.dinlemeyi_durdur()
            
        if self.sensor_cart:
            self.sensor_cart.dinlemeyi_durdur()
    
    def test_baslat(self):
        """Test modunu başlat"""
        self.test_aktif = True
        self.gsi_zamanlar.clear()
        self.gso_zamanlar.clear()
        print("🧪 Test modu aktif!")
        
    def test_durdur(self):
        """Test modunu durdur"""
        self.test_aktif = False
        print("⏹️ Test modu durduruldu")
    
    def sonuclari_goster(self):
        """Test sonuçlarını analiz et ve göster"""
        print("\n📊 GERÇEK KART + GÖRÜNTÜ İŞLEME TEST SONUÇLARI")
        print("="*60)
        
        # GSI analizi
        if len(self.gsi_zamanlar) >= 2:
            gsi_gecikmeler = []
            for i in range(0, len(self.gsi_zamanlar)-1, 2):
                if i+1 < len(self.gsi_zamanlar):
                    gecikme = (self.gsi_zamanlar[i+1][1] - self.gsi_zamanlar[i][1]) * 1000
                    gsi_gecikmeler.append(gecikme)
            
            if gsi_gecikmeler:
                gsi_ort = sum(gsi_gecikmeler) / len(gsi_gecikmeler)
                gsi_min = min(gsi_gecikmeler)
                gsi_max = max(gsi_gecikmeler)
                print(f"🔄 GSI → Konveyör: Ort={gsi_ort:.3f}ms, Min={gsi_min:.3f}ms, Max={gsi_max:.3f}ms")
        
        # GSO analizi
        if len(self.gso_zamanlar) >= 2:
            gso_gecikmeler = []
            for i in range(0, len(self.gso_zamanlar)-1, 2):
                if i+1 < len(self.gso_zamanlar):
                    gecikme = (self.gso_zamanlar[i+1][1] - self.gso_zamanlar[i][1]) * 1000
                    gso_gecikmeler.append(gecikme)
            
            if gso_gecikmeler:
                gso_ort = sum(gso_gecikmeler) / len(gso_gecikmeler)
                gso_min = min(gso_gecikmeler)
                gso_max = max(gso_gecikmeler)
                print(f"📷 GSO → Görüntü: Ort={gso_ort:.1f}ms, Min={gso_min:.1f}ms, Max={gso_max:.1f}ms")
                
                if GERCEK_GORUNTU_VAR:
                    print(f"🎯 Gerçek YOLO işleme performansı!")
                else:
                    print(f"⚠️ Simülasyon modunda (75ms sabit)")
        
        # Performans değerlendirmesi
        print("\n💡 PERFORMANS DEĞERLENDİRMESİ")
        print("="*50)
        if GERCEK_GORUNTU_VAR:
            print("✅ Gerçek YOLO görüntü işleme aktif")
            print("🎯 Global shutter kamera + asenkron işleme")
            print("📏 Ultra hassas konum kontrolü")
        else:
            print("⚠️ Simülasyon modunda çalışıyor")

def test_gercek_kartlar():
    """Gerçek kartlarla test"""
    if not GERCEK_KARTLAR_VAR:
        print("❌ Gerçek kartlar kullanılamıyor, mock test yapılacak")
        return test_gsi_gso_timing()
    
    test_sistemi = GercekKartTestSistemi()
    
    try:
        # Kartları başlat
        if not test_sistemi.kartlari_baslat():
            print("❌ Kartlar başlatılamadı, mock test yapılacak")
            return test_gsi_gso_timing()
        
        print("\n🧪 GERÇEK KART + GÖRÜNTÜ İŞLEME TESTİ")
        print("="*60)
        if GERCEK_GORUNTU_VAR:
            print("🎯 Gerçek YOLO görüntü işleme aktif!")
        else:
            print("⚠️ Görüntü işleme simülasyon modunda")
        print()
        print("📍 Test talimatları:")
        print("   1. GSI sensörünü tetikleyin (giriş sensörü)")
        print("   2. GSO sensörünü tetikleyin (çıkış sensörü)")
        print("   3. Kameranın önüne şişe/obje koyun (YOLO testi)")
        print("   4. 'q' basın ve Enter'a tıklayın (çıkış için)")
        print("   5. Test 60 saniye otomatik kapanır")
        print()
        
        # Test başlat
        test_sistemi.test_baslat()
        
        # Kullanıcı girişini bekle
        baslangic = time.time()
        while time.time() - baslangic < 60:  # 60 saniye timeout
            try:
                # Non-blocking input için timeout kullan
                import select
                import sys
                
                if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                    girdi = input().strip().lower()
                    if girdi == 'q':
                        break
                        
            except (KeyboardInterrupt, EOFError):
                break
            except ImportError:
                # Windows için alternatif
                time.sleep(0.1)
        
        print("\n⏹️ Test sona eriyor...")
        test_sistemi.test_durdur()
        test_sistemi.sonuclari_goster()
        
    except KeyboardInterrupt:
        print("\n⏹️ Test kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_sistemi.kartlari_durdur()

# Test sistemi
def test_gsi_gso_timing():
    """GSI/GSO timing testini çalıştırır"""
    
    # Mock nesneleri oluştur
    mock_motor = MockMotor()
    mock_sensor = MockSensor()
    mock_goruntu = MockGoruntuIsleme()
    
    # oturum_var modülünü import et ve mock'ları bağla
    from rvm_sistemi.makine.senaryolar import oturum_var
    
    # Mock görüntü işleme servisini değiştir
    oturum_var.goruntu_isleme_servisi = mock_goruntu
    
    # Motor ve sensor referanslarını ayarla
    oturum_var.motor_referansini_ayarla(mock_motor)
    oturum_var.sensor_referansini_ayarla(mock_sensor)
    
    print("🚀 GSI/GSO TİMİNG TEST BAŞLADI")
    print("="*60)
    
    # Oturumu başlat
    print("\n📋 [1] Oturum başlatılıyor...")
    oturum_var.mesaj_isle("oturum_var")
    time.sleep(0.5)  # Lojik thread'in başlaması için bekle
    
    # Barkod simülasyonu
    print("\n📋 [2] Barkod simülasyonu...")
    test_barkod = "1923026353360"  # Erikli
    start_time = time.time()
    oturum_var.barkod_verisi_al(test_barkod)
    print(f"⏱️ Barkod işleme süresi: {(time.time() - start_time)*1000:.2f}ms")
    
    time.sleep(0.2)
    
    # GSI tetikleme testi
    print("\n🔄 [3] GSI tetikleme testi...")
    gsi_start = time.time()
    print(f"📡 GSI mesajı gönderiliyor - {time.strftime('%H:%M:%S.%f')[:-3]}")
    oturum_var.mesaj_isle("gsi")
    
    # Konveyör ileri komutunun ne kadar sürede geldiğini ölç
    timeout = 0
    while mock_motor.son_komut != "konveyor_ileri" and timeout < 50:  # 5ms timeout
        time.sleep(0.0001)  # 0.1ms bekle
        timeout += 1
    
    if mock_motor.son_komut == "konveyor_ileri":
        gsi_gecikme = (mock_motor.komut_zamani - gsi_start) * 1000
        print(f"⚡ GSI → Konveyör İleri gecikme: {gsi_gecikme:.3f}ms")
    else:
        print("❌ GSI komutu timeout!")
    
    time.sleep(0.5)
    
    # GSO tetikleme testi
    print("\n📷 [4] GSO tetikleme testi...")
    gso_start = time.time()
    print(f"📡 GSO mesajı gönderiliyor - {time.strftime('%H:%M:%S.%f')[:-3]}")
    oturum_var.mesaj_isle("gso")
    
    # Görüntü işleme fonksiyonunun ne kadar sürede çağrıldığını ölç
    timeout = 0
    while mock_goruntu.son_cagri is None and timeout < 50:  # 5ms timeout
        time.sleep(0.0001)  # 0.1ms bekle
        timeout += 1
    
    if mock_goruntu.son_cagri:
        gso_gecikme = (mock_goruntu.son_cagri - gso_start) * 1000
        print(f"⚡ GSO → Görüntü İşleme gecikme: {gso_gecikme:.3f}ms")
    else:
        print("❌ GSO komutu timeout!")
    
    time.sleep(1.0)  # Görüntü işlemenin tamamlanması için bekle
    
    # Sonuçları göster
    print("\n📊 TEST SONUÇLARI")
    print("="*40)
    print(f"🔄 GSI Gecikme: {gsi_gecikme:.3f}ms")
    print(f"📷 GSO Gecikme: {gso_gecikme:.3f}ms")
    print(f"📸 Görüntü işleme sayısı: {mock_goruntu.call_count}")
    print(f"🎯 Son motor komutu: {mock_motor.son_komut}")
    
    # Performans değerlendirmesi
    print("\n💡 PERFORMANS DEĞERLENDİRMESİ")
    print("="*50)
    if gsi_gecikme < 1.0:
        print(f"✅ GSI performansı MÜKEMMEL ({gsi_gecikme:.3f}ms)")
    elif gsi_gecikme < 2.0:
        print(f"✅ GSI performansı İYİ ({gsi_gecikme:.3f}ms)")
    else:
        print(f"⚠️ GSI performansı ORTA ({gsi_gecikme:.3f}ms)")
    
    if gso_gecikme < 1.0:
        print(f"✅ GSO performansı MÜKEMMEL ({gso_gecikme:.3f}ms)")
    elif gso_gecikme < 2.0:
        print(f"✅ GSO performansı İYİ ({gso_gecikme:.3f}ms)")
    else:
        print(f"⚠️ GSO performansı ORTA ({gso_gecikme:.3f}ms)")
    
    print(f"\n🎯 Global shutter kamera için ideal gecikme: <1ms")
    print(f"📏 Şişe hızı 50mm/s varsayımıyla:")
    print(f"   - 1ms gecikme = {gso_gecikme * 0.05:.3f}mm konum hatası")
    print(f"   - Mevcut sistem = {gso_gecikme * 0.05:.3f}mm konum hatası")

def test_multiple_cycles():
    """Birden fazla döngü testi"""
    print("\n🔄 ÇOK DÖNGÜ TESİ")
    print("="*30)
    
    gecikme_listesi = []
    
    for i in range(5):
        print(f"\n🔄 Döngü {i+1}/5")
        
        # Mock reset
        mock_goruntu = MockGoruntuIsleme()
        from rvm_sistemi.makine.senaryolar import oturum_var
        oturum_var.goruntu_isleme_servisi = mock_goruntu
        
        # GSO testi
        gso_start = time.time()
        oturum_var.mesaj_isle("gso")
        
        timeout = 0
        while mock_goruntu.son_cagri is None and timeout < 50:
            time.sleep(0.0001)
            timeout += 1
        
        if mock_goruntu.son_cagri:
            gecikme = (mock_goruntu.son_cagri - gso_start) * 1000
            gecikme_listesi.append(gecikme)
            print(f"   ⚡ Gecikme: {gecikme:.3f}ms")
        
        time.sleep(0.2)
    
    if gecikme_listesi:
        ortalama = sum(gecikme_listesi) / len(gecikme_listesi)
        minimum = min(gecikme_listesi)
        maksimum = max(gecikme_listesi)
        
        print(f"\n📊 İSTATİSTİKLER:")
        print(f"   ⚡ Ortalama: {ortalama:.3f}ms")
        print(f"   🏃 En hızlı: {minimum:.3f}ms")
        print(f"   🐌 En yavaş: {maksimum:.3f}ms")
        print(f"   📏 Standart sapma: {(sum([(x-ortalama)**2 for x in gecikme_listesi])/len(gecikme_listesi))**0.5:.3f}ms")

if __name__ == "__main__":
    print("🚀 GSI/GSO + GÖRÜNTÜ İŞLEME TEST SİSTEMİ")
    print("="*50)
    print("1. Gerçek kartlar + YOLO görüntü işleme")
    print("2. Mock test (simülasyon)")
    print()
    
    try:
        secim = input("Seçiminizi yapın (1/2): ").strip()
        
        if secim == "1":
            print("\n🔧 Gerçek sistem testi başlatılıyor...")
            print(f"📷 YOLO görüntü işleme: {'✅ Aktif' if GERCEK_GORUNTU_VAR else '❌ Simülasyon'}")
            test_gercek_kartlar()
        else:
            print("\n🤖 Mock test başlatılıyor...")
            test_gsi_gso_timing()
            test_multiple_cycles()
        
        print("\n✅ Test tamamlandı!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()