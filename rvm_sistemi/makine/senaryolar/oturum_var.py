import time

from ..dogrulama import DogrulamaServisi

dogrulama_servisi = DogrulamaServisi()

# Global motor referansı (seri_deneme.py'den ayarlanacak)
motor_ref = None
sensor_ref = None

def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()

def sensor_referansini_ayarla(sensor):
    global sensor_ref
    sensor_ref = sensor
    

def olayi_isle(olay):
    print(f"[Oturum Var] Gelen olay: {olay}")

    if olay.strip().lower() == "oturum_var":
        if sensor_ref:
            sensor_ref.led_ac()
        else:
            print("[Oturum Var] Sensor referansı bulunamadı.")

    if olay.strip().lower().startswith("a:"):
        agirlik_str = olay.split(":")[1]
        agirlik = float(agirlik_str.replace(",", "."))
        dogrulama_servisi.agirlik_dogrula(agirlik)

    if olay.strip().lower() == "gsi":
        if motor_ref:
            
            motor_ref.konveyor_geri()
            time.sleep(1)  # Motorun aktifleşmesi için kısa bir bekleme
            motor_ref.konveyor_dur()
            print("[Oturum Var] Motor aktif edildi.")
        else:
            print("[Oturum Var] Motor referansı bulunamadı.")
    # Oturum yokken yapılacak diğer işlemler buraya eklenebilir