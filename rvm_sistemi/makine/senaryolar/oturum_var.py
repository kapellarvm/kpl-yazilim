import time

from ...veri_tabani import veritabani_yoneticisi

# Global motor referansı (seri_deneme.py'den ayarlanacak)
motor_ref = None
sensor_ref = None

# Giriş mantık değişkenleri
agirlik_lojik = False
barkod_lojik = False

def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()

def sensor_referansini_ayarla(sensor):
    global sensor_ref
    sensor_ref = sensor
    
def agirlik_verisi_al(agirlik):
    global agirlik_lojik
    agirlik_lojik = True
    print(f"[Oturum Var] Alınan ağırlık verisi: {agirlik} gram")

def barkod_verisi_al(barcode):
    global barkod_lojik
    barkod_lojik = True
    print(f"[Oturum Var] Alınan barkod verisi: {barcode}")
    veri_tabani_dogrulama(barcode)


def veri_tabani_dogrulama(barcode):
    """
    Gelen barkod verisini veritabanında bulup ürün bilgilerini print eder.
    """
    print(f"[Veritabanı Doğrulama] Barkod sorgulanıyor: {barcode}")
    
    # Veritabanından barkod bilgilerini al
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(barcode)
    
    if urun_bilgisi:
        print(f"[Veritabanı Doğrulama] ✅ Ürün bulundu!")
        print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ ÜRÜN BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ ID: {urun_bilgisi.get('id', 'Bilinmiyor')}")
        print(f"║ Barkod: {urun_bilgisi.get('barcode', 'Bilinmiyor')}")
        print(f"║ Materyal ID: {urun_bilgisi.get('material', 'Bilinmiyor')}")
        
        # Materyal ID'sini anlamlı isme çevirme
        materyal_isimleri = {
            1: "PET",
            2: "Cam (Glass)", 
            3: "Alüminyum (Alu)"
        }
        materyal_adi = materyal_isimleri.get(urun_bilgisi.get('material'), "Bilinmeyen Materyal")
        print(f"║ Materyal Türü: {materyal_adi}")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ AĞIRLIK BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        
        min_agirlik = urun_bilgisi.get('packMinWeight')
        max_agirlik = urun_bilgisi.get('packMaxWeight')
        print(f"║ Minimum Ağırlık: {min_agirlik if min_agirlik is not None else 'Belirtilmemiş'} gr")
        print(f"║ Maksimum Ağırlık: {max_agirlik if max_agirlik is not None else 'Belirtilmemiş'} gr")
        
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ BOYUT BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        
        min_genislik = urun_bilgisi.get('packMinWidth')
        max_genislik = urun_bilgisi.get('packMaxWidth')
        min_yukseklik = urun_bilgisi.get('packMinHeight')
        max_yukseklik = urun_bilgisi.get('packMaxHeight')
        
        print(f"║ Minimum Genişlik: {min_genislik if min_genislik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Maksimum Genişlik: {max_genislik if max_genislik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Minimum Yükseklik: {min_yukseklik if min_yukseklik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Maksimum Yükseklik: {max_yukseklik if max_yukseklik is not None else 'Belirtilmemiş'} mm")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
                
        return urun_bilgisi
    else:
        print(f"[Veritabanı Doğrulama] ❌ Ürün bulunamadı: {barcode}")
        print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ HATA: Barkod '{barcode}' veritabanında kayıtlı değil!")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return None

def giris_iade():
    """
    Barkod verisi olmadığı için ürün iade edilir.
    """
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ İADE İŞLEMİ")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ ❌ ÜRÜN İADE EDİLDİ")
    print(f"║ Sebep: Barkod verisi bulunamadı")
    print(f"║ Ağırlık Verisi: {'✅ Var' if agirlik_lojik else '❌ Yok'}")
    print(f"║ Barkod Verisi: {'✅ Var' if barkod_lojik else '❌ Yok'}")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
    
    # Motor ile ürünü geri gönder
    if motor_ref:
        print("[Giriş İade] Ürün konveyör ile geri gönderiliyor...")
        motor_ref.konveyor_dur()
        print("[Giriş İade] Ürün iade edildi.")
    else:
        print("[Giriş İade] Motor referansı bulunamadı.")

############################################## Senaryolar Alt Kısım (İşlem Fonksiyonları) ##############################################

def olayi_isle(olay):
    global agirlik_lojik, barkod_lojik
    print(f"[Oturum Var] Gelen olay: {olay}")

    if olay.strip().lower() == "oturum_var":
        if sensor_ref:
            sensor_ref.led_ac()
        else:
            print("[Oturum Var] Sensor referansı bulunamadı.")

    if olay.strip().lower().startswith("a:"):
        agirlik_str = olay.split(":")[1]
        agirlik = float(agirlik_str.replace(",", "."))
        agirlik_verisi_al(agirlik)

    if olay.strip().lower() == "gsi":
        if motor_ref:
            
            motor_ref.konveyor_ileri()

            print("[Oturum Var] Motor aktif edildi.")
        else:
            print("[Oturum Var] Motor referansı bulunamadı.")

    if olay.strip().lower() == "gso":
        print("[Oturum Var] GSO mesajı alındı - Giriş kontrol ediliyor...")
        
        # Barkod verisi kontrol et
        if not barkod_lojik:
            print("[Oturum Var] ❌ Barkod verisi yok - İade işlemi başlatılıyor")
            giris_iade()
        else:
            print("[Oturum Var] ✅ Barkod verisi mevcut - İşlem devam ediyor")
            
        # Kontrol sonrası lojik değişkenlerini sıfırla
        agirlik_lojik = False
        barkod_lojik = False
        
    # Oturum yokken yapılacak diğer işlemler buraya eklenebilir