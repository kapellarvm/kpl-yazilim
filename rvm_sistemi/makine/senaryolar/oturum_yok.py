import time
# Global motor referansı (seri_deneme.py'den ayarlanacak)
motor_ref = None

def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()

def olayi_isle(olay):
    print(f"[Oturum Yok] Gelen olay: {olay}")
    if olay.strip().lower() == "gsi":
        if motor_ref:
            
            motor_ref.konveyor_ileri()
            time.sleep(1)  # Motorun aktifleşmesi için kısa bir bekleme
            motor_ref.konveyor_dur()
            print("[Oturum Yok] Motor aktif edildi.")
        else:
            print("[Oturum Yok] Motor referansı bulunamadı.")
    # Oturum yokken yapılacak diğer işlemler buraya eklenebilir