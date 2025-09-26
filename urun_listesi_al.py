import sys
import os

from rvm_sistemi.dimdb import istemci
from rvm_sistemi.veri_tabani import veritabani_yoneticisi

def main():
    """
    Veritabanını başlatan, DİM-DB'den ürün listesini alan ve veritabanına
    kaydeden ana test fonksiyonu.
    """
    print("-" * 50)
    print("ÜRÜN LİSTESİ ALMA VE KAYDETME TEST ARACI")
    print("-" * 50)

    try:
        # 1. Adım: Veritabanını ve 'products' tablosunu oluştur/kontrol et
        print("1. Adım: Veritabanı kontrol ediliyor...")
        veritabani_yoneticisi.init_db()
        print("   Veritabanı ve 'products' tablosu hazır.")

        # 2. Adım: DİM-DB'den ürün listesini iste ve veritabanına kaydet
        print("\n2. Adım: Ürün listesi DİM-DB'den isteniyor...")
        istemci.get_all_products_and_save()

        # 3. Adım: Veritabanındaki kaydı doğrula
        print("\n3. Adım: Veritabanındaki kayıt sayısı doğrulanıyor...")
        kayit_sayisi = veritabani_yoneticisi.urun_sayisini_getir()
        if kayit_sayisi > 0:
            print(f"   Doğrulama başarılı: Veritabanında {kayit_sayisi} adet ürün bulundu.")
            print("\nTEST BAŞARILI!")
        else:
            print("   Doğrulama BAŞARISIZ: Veritabanına hiçbir ürün kaydedilmedi.")

    except Exception as e:
        print(f"\nTEST SIRASINDA BİR HATA OLUŞTU: {e}")

if __name__ == '__main__':
    main()

