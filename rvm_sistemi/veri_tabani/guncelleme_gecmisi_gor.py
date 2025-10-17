#!/usr/bin/env python3
"""
Ürün güncelleme geçmişini görüntüler
"""

from rvm_sistemi.veri_tabani import veritabani_yoneticisi

def main():
    print("=" * 80)
    print("📊 ÜRÜN GÜNCELLEME GEÇMİŞİ")
    print("=" * 80)
    
    # İstatistikler
    print("\n📈 İSTATİSTİKLER:")
    print("-" * 80)
    istatistikler = veritabani_yoneticisi.guncelleme_istatistikleri()
    
    if istatistikler:
        print(f"  Toplam Güncelleme       : {istatistikler.get('toplam_guncelleme', 0)}")
        print(f"  Başarılı Güncelleme     : {istatistikler.get('basarili_guncelleme', 0)}")
        print(f"  Başarısız Güncelleme    : {istatistikler.get('basarisiz_guncelleme', 0)}")
        print(f"  Son Güncelleme Zamanı   : {istatistikler.get('son_guncelleme_zamani', 'Yok')}")
        print(f"  Mevcut Ürün Sayısı      : {istatistikler.get('mevcut_urun_sayisi', 0)}")
    else:
        print("  ⚠️  İstatistik bilgisi alınamadı")
    
    # Son güncelleme
    print("\n🕐 SON GÜNCELLEME:")
    print("-" * 80)
    son_guncelleme = veritabani_yoneticisi.son_guncelleme_bilgisi()
    
    if son_guncelleme:
        print(f"  ID                      : {son_guncelleme.get('id')}")
        print(f"  Tarih/Saat              : {son_guncelleme.get('update_timestamp')}")
        print(f"  Ürün Sayısı             : {son_guncelleme.get('product_count')}")
        print(f"  Kaynak                  : {son_guncelleme.get('source')}")
        print(f"  Durum                   : {son_guncelleme.get('status')}")
        print(f"  Notlar                  : {son_guncelleme.get('notes')}")
    else:
        print("  ⚠️  Henüz güncelleme yapılmadı")
    
    # Tüm geçmiş (son 20)
    print("\n📜 GÜNCELLEME GEÇMİŞİ (Son 20):")
    print("-" * 80)
    gecmis = veritabani_yoneticisi.guncelleme_gecmisini_getir(limit=20)
    
    if gecmis:
        print(f"{'ID':<5} {'Tarih/Saat':<20} {'Ürün':<8} {'Kaynak':<10} {'Durum':<10} {'Notlar'}")
        print("-" * 80)
        for kayit in gecmis:
            durum_icon = "✅" if kayit.get('status') == 'success' else "❌"
            print(f"{kayit.get('id'):<5} "
                  f"{kayit.get('update_timestamp'):<20} "
                  f"{kayit.get('product_count'):<8} "
                  f"{kayit.get('source'):<10} "
                  f"{durum_icon} {kayit.get('status'):<8} "
                  f"{kayit.get('notes', '')[:40]}")
    else:
        print("  ⚠️  Henüz güncelleme geçmişi yok")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

