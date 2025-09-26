# manuel_barkod_gonder.py

from rvm_sistemi.dimdb import istemci
import time

def run_test():
    """
    Kullanıcıdan barkod alıp getBarcode metodunu test eden ana fonksiyon.
    """
    print("-" * 50)
    print("MANUEL BARKOD GÖNDERME TEST ARACI")
    print("-" * 50)
    
    # Oturumun aktif olduğundan emin olmak için kullanıcıyı uyar
    input("Lütfen RVM ekranından bir oturum başlattığınızdan emin olun, ardından Enter'a basın...")
    
    print("\nTest başlıyor. Çıkmak için CTRL+C'ye basın.")
    
    try:
        while True:
            # Kullanıcıdan test edilecek barkodu al
            barcode_to_test = input("\nGönderilecek test barkodunu girin: ")
            
            if not barcode_to_test:
                print("Geçersiz barkod. Lütfen tekrar deneyin.")
                continue
            
            # istemci.py'deki fonksiyonu çağır
            istemci.send_get_barcode(barcode_to_test)
            
            # İsteklerin birbirine karışmaması için kısa bir bekleme
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTest sonlandırıldı.")
    except Exception as e:
        print(f"\nBir hata oluştu: {e}")

if __name__ == "__main__":
    run_test()

