#!/usr/bin/env python3
"""
Zamanlı Görevler Test Scripti
Ürün güncelleme zamanlayıcısını test eder
"""

import asyncio
import time
from rvm_sistemi.zamanli_gorevler.urun_guncelleyici import urun_guncelleyici, UrunGuncelleyici

async def test_urun_guncelleyici():
    """Ürün güncelleme zamanlayıcısını test eder"""
    print("=" * 60)
    print("🔄 ZAMANLI GÖREVLER TEST ARACI")
    print("=" * 60)
    
    # Durum bilgisini göster
    print("\n📊 Başlangıç Durumu:")
    durum = urun_guncelleyici.durum_bilgisi()
    for key, value in durum.items():
        print(f"  {key}: {value}")
    
    # Manuel güncelleme testi
    print("\n🔄 Manuel güncelleme testi...")
    urun_guncelleyici.manuel_guncelle()
    await asyncio.sleep(2)  # Güncellemenin tamamlanmasını bekle
    
    # Zamanlayıcıyı başlat (her 30 saniyede bir - test için)
    print("\n⏰ Zamanlayıcı başlatılıyor (her 30 saniyede bir)...")
    test_guncelleyici = UrunGuncelleyici(
        guncelleme_sikligi_saat=0.5/60,  # 30 saniye
        ilk_guncelleme_yap=False
    )
    
    # 2 dakika çalıştır (4 güncelleme)
    print("📊 2 dakika boyunca her 30 saniyede güncelleme yapılacak...")
    print("⏱️  Başlangıç zamanı:", time.strftime('%H:%M:%S'))
    
    start_time = time.time()
    guncelleme_task = asyncio.create_task(test_guncelleyici.baslat())
    
    # 2 dakika bekle
    await asyncio.sleep(120)
    
    # Durdur
    test_guncelleyici.durdur()
    guncelleme_task.cancel()
    
    print("⏱️  Bitiş zamanı:", time.strftime('%H:%M:%S'))
    print("✅ Test tamamlandı")

async def show_update_history():
    """Güncelleme geçmişini göster"""
    print("\n📊 GÜNCELLEME GEÇMİŞİ:")
    print("-" * 50)
    
    from rvm_sistemi.veri_tabani import veritabani_yoneticisi
    gecmis = veritabani_yoneticisi.guncelleme_gecmisini_getir(5)
    if gecmis:
        for kayit in gecmis:
            print(f"ID {kayit['id']}: {kayit['update_timestamp']} - {kayit['product_count']} ürün")
    else:
        print("Henüz güncelleme yok")

async def main():
    # Veritabanını başlat
    from rvm_sistemi.veri_tabani import veritabani_yoneticisi
    veritabani_yoneticisi.init_db()
    
    # Mevcut durumu göster
    await show_update_history()
    
    # Test çalıştır
    await test_urun_guncelleyici()
    
    # Son durumu göster
    await show_update_history()
    
    print("\n" + "=" * 60)
    print("✅ TEST TAMAMLANDI")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
