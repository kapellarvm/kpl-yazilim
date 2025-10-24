#!/usr/bin/env python3
"""
Uyku Modu Test Scripti
Uyku modu servisini test etmek için basit script
"""

import time
import requests
import json
from datetime import datetime

# API base URL
API_BASE = "http://localhost:4321"

def test_uyku_durumu():
    """Uyku durumunu test et"""
    try:
        response = requests.get(f"{API_BASE}/api/v1/uyku/durum")
        if response.status_code == 200:
            data = response.json()
            print("🌙 Uyku Modu Durumu:")
            print(f"   Aktif: {data['uyku_modu_aktif']}")
            print(f"   Son Aktivite: {data['son_aktivite']}")
            print(f"   Kalan Süre: {data['kalan_sure_dakika']} dakika")
            print(f"   Uyku Sayısı: {data['uyku_modu_sayisi']}")
            print(f"   Enerji Tasarrufu: {data['enerji_tasarrufu_kwh']} kWh")
            return data
        else:
            print(f"❌ Hata: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return None

def test_uyku_istatistikleri():
    """Uyku istatistiklerini test et"""
    try:
        response = requests.get(f"{API_BASE}/api/v1/uyku/istatistikler")
        if response.status_code == 200:
            data = response.json()
            print("📊 Uyku Modu İstatistikleri:")
            print(f"   Toplam Uyku: {data['toplam_uyku_modu']} kez")
            print(f"   Toplam Süre: {data['toplam_uyku_suresi_saat']} saat")
            print(f"   Toplam Tasarruf: {data['toplam_enerji_tasarrufu_kwh']} kWh")
            print(f"   Ortalama Süre: {data['ortalama_uyku_suresi_dakika']} dakika")
            print(f"   Tasarruf Oranı: %{data['enerji_tasarrufu_yuzde']}")
            return data
        else:
            print(f"❌ Hata: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return None

def test_aktivite_kaydet():
    """Aktivite kaydetme testi"""
    try:
        response = requests.post(f"{API_BASE}/api/v1/uyku/aktivite")
        if response.status_code == 200:
            data = response.json()
            print("✅ Aktivite kaydedildi")
            return True
        else:
            print(f"❌ Hata: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def test_zorla_uyku():
    """Zorla uyku modu testi"""
    try:
        response = requests.post(f"{API_BASE}/api/v1/uyku/zorla-uyku")
        if response.status_code == 200:
            data = response.json()
            print(f"💤 {data['message']}")
            return True
        else:
            print(f"❌ Hata: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def test_uyku_cik():
    """Uyku modundan çıkma testi"""
    try:
        response = requests.post(f"{API_BASE}/api/v1/uyku/uyku-cik")
        if response.status_code == 200:
            data = response.json()
            print(f"🌅 {data['message']}")
            return True
        else:
            print(f"❌ Hata: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def test_uyku_ayarlari():
    """Uyku ayarları testi"""
    try:
        # 10 dakikaya ayarla
        data = {"uyku_suresi_dakika": 10}
        response = requests.post(f"{API_BASE}/api/v1/uyku/ayarlar", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"⚙️ {result['message']}")
            return True
        else:
            print(f"❌ Hata: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def test_uyku_test_endpoint():
    """Uyku test endpoint'i"""
    try:
        response = requests.get(f"{API_BASE}/api/v1/uyku/test")
        if response.status_code == 200:
            data = response.json()
            print("🧪 Uyku Test Sonuçları:")
            print(f"   Durum: {json.dumps(data['data']['durum'], indent=2)}")
            print(f"   İstatistikler: {json.dumps(data['data']['istatistikler'], indent=2)}")
            print(f"   Thread Aktif: {data['data']['thread_aktif']}")
            print(f"   Sistem Referans: {data['data']['sistem_referans']}")
            return True
        else:
            print(f"❌ Hata: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("=" * 60)
    print("🌙 RVM UYKU MODU TEST SCRIPTI")
    print("=" * 60)
    print(f"⏰ Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API Base URL: {API_BASE}")
    print()
    
    # Test sırası
    tests = [
        ("Uyku Durumu", test_uyku_durumu),
        ("Uyku İstatistikleri", test_uyku_istatistikleri),
        ("Aktivite Kaydet", test_aktivite_kaydet),
        ("Uyku Ayarları (10dk)", test_uyku_ayarlari),
        ("Zorla Uyku Modu", test_zorla_uyku),
        ("Uyku Modundan Çık", test_uyku_cik),
        ("Test Endpoint", test_uyku_test_endpoint),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name} Testi:")
        print("-" * 40)
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test hatası: {e}")
        
        time.sleep(1)  # Testler arası bekleme
    
    print("\n" + "=" * 60)
    print("✅ Tüm testler tamamlandı!")
    print("=" * 60)

if __name__ == "__main__":
    main()
