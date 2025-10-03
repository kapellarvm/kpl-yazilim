#!/usr/bin/env python3
"""
Hızlı uyarı sistemi test scripti
Bu script uyarı sistemini test etmek için kullanılır
"""

import requests
import json
import time

def uyari_goster(mesaj="Lütfen şişeyi alınız", sure=2):
    """Uyarı gösterir"""
    try:
        url = "http://192.168.53.2:4321/api/uyari-goster"
        data = {
            "mesaj": mesaj,
            "sure": sure
        }
        
        print(f"Uyarı gönderiliyor: {mesaj} ({sure} saniye)")
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Başarılı: {result['message']}")
            return True
        else:
            print(f"❌ Hata: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def main():
    print("🚨 Hızlı Uyarı Sistemi Test Scripti")
    print("=" * 50)
    
    # Test mesajları
    test_mesajlari = [
        "Lütfen şişeyi alınız",
        "⚠️ Dikkat! Kapı açık",
        "🔔 Yeni ürün eklendi",
        "⏰ Zaman doldu, lütfen işleminizi tamamlayın",
        "✅ İşlem tamamlandı"
    ]
    
    while True:
        print("\nTest seçenekleri:")
        print("1. Varsayılan uyarı (2 saniye)")
        print("2. Özel mesaj (2 saniye)")
        print("3. Uzun uyarı (5 saniye)")
        print("4. Kısa uyarı (1 saniye)")
        print("5. Rastgele test mesajı")
        print("6. Çıkış")
        
        secim = input("\nSeçiminiz (1-6): ").strip()
        
        if secim == "1":
            uyari_goster()
        elif secim == "2":
            mesaj = input("Mesajı girin: ").strip()
            if mesaj:
                uyari_goster(mesaj)
        elif secim == "3":
            mesaj = input("Mesajı girin: ").strip()
            if mesaj:
                uyari_goster(mesaj, 5)
        elif secim == "4":
            mesaj = input("Mesajı girin: ").strip()
            if mesaj:
                uyari_goster(mesaj, 1)
        elif secim == "5":
            import random
            mesaj = random.choice(test_mesajlari)
            sure = random.randint(1, 4)
            uyari_goster(mesaj, sure)
        elif secim == "6":
            print("Çıkılıyor...")
            break
        else:
            print("Geçersiz seçim!")
        
        # Kısa bekleme
        time.sleep(0.5)

if __name__ == "__main__":
    main()
