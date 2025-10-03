#!/usr/bin/env python3
"""
Cron Job Test Scripti
Ürün güncelleme zamanlayıcısını test eder
"""

import asyncio
import schedule
import time
from rvm_sistemi.dimdb import istemci
from rvm_sistemi.veri_tabani import veritabani_yoneticisi

async def test_product_update():
    """Test ürün güncellemesi"""
    print("🔄 Test ürün güncellemesi başlatılıyor...")
    await istemci.get_all_products_and_save()
    print("✅ Test ürün güncellemesi tamamlandı")

async def run_test_scheduler():
    """Test zamanlayıcısı - her 30 saniyede bir güncelle"""
    print("⏰ Test zamanlayıcı başlatıldı (her 30 saniye)")
    
    # İlk güncellemeyi hemen yap
    await test_product_update()
    
    # Her 30 saniyede bir güncelle (test için)
    schedule.every(30).seconds.do(lambda: asyncio.create_task(test_product_update()))
    
    # 5 dakika çalıştır (10 güncelleme)
    print("📊 5 dakika boyunca her 30 saniyede güncelleme yapılacak...")
    print("⏱️  Başlangıç zamanı:", time.strftime('%H:%M:%S'))
    
    start_time = time.time()
    while time.time() - start_time < 300:  # 5 dakika = 300 saniye
        schedule.run_pending()
        await asyncio.sleep(1)
    
    print("⏱️  Bitiş zamanı:", time.strftime('%H:%M:%S'))
    print("✅ Test tamamlandı")

async def show_update_history():
    """Güncelleme geçmişini göster"""
    print("\n📊 GÜNCELLEME GEÇMİŞİ:")
    print("-" * 50)
    
    gecmis = veritabani_yoneticisi.guncelleme_gecmisini_getir(5)
    if gecmis:
        for kayit in gecmis:
            print(f"ID {kayit['id']}: {kayit['update_timestamp']} - {kayit['product_count']} ürün")
    else:
        print("Henüz güncelleme yok")

async def main():
    print("=" * 60)
    print("🔄 CRON JOB TEST ARACI")
    print("=" * 60)
    
    # Veritabanını başlat
    veritabani_yoneticisi.init_db()
    
    # Mevcut durumu göster
    await show_update_history()
    
    # Test zamanlayıcısını çalıştır
    await run_test_scheduler()
    
    # Son durumu göster
    await show_update_history()
    
    print("\n" + "=" * 60)
    print("✅ TEST TAMAMLANDI")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
