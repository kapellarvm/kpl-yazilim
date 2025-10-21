import time
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
    #print(f"[Oturum Yok] Gelen olay: {olay}")
    if olay.strip().lower() == "oturum_yok":
        sensor_ref.led_kapat()
        sensor_ref.makine_oturum_yok()
        sensor_ref.bypass_modu_ac()
        sensor_ref.bypass_modu_ac()
        time.sleep(1)
        sensor_ref.guvenlik_role_reset()
        
        # Port sağlık servisine oturum durumunu bildir
        from ..seri.port_saglik_servisi import port_saglik_servisi
        if port_saglik_servisi:
            port_saglik_servisi.oturum_durumu_guncelle(False)
            from ...utils.logger import log_system
            log_system("Port sağlık servisi devam ediyor - Oturum pasif")
        
    #elif olay.strip().lower() == "gsi":
      #  if motor_ref:
            
     #       motor_ref.konveyor_geri()
      #      time.sleep(1)  # Motorun aktifleşmesi için kısa bir bekleme
      #      motor_ref.konveyor_dur()
      #      print("[Oturum Yok] Motor aktif edildi.")
      #  else:
      #      print("[Oturum Yok] Motor referansı bulunamadı.")
    # Oturum yokken yapılacak diğer işlemler buraya eklenebilir