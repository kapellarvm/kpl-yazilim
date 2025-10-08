from .senaryolar import oturum_var, oturum_yok, bakim
from .senaryolar import uyari
from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning


class DurumMakinesi:
    def __init__(self):
        self.durum = "oturum_yok"  # Başlangıç durumu
        self.onceki_durum = None  # Önceki durumu takip et
        self.bakim_url = "http://192.168.53.2:4321/bakim"  # Varsayılan bakım URL'i

    def durum_degistir(self, yeni_durum):
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        log_system(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.onceki_durum = self.durum
        self.durum = yeni_durum
        
        
        # Bakım moduna giriliyorsa, otomatik ekran değişimi
        if yeni_durum == "bakim" and self.onceki_durum != "bakim":
            bakim.bakim_moduna_gir(self.bakim_url)
        
        # Bakım modundan çıkılıyorsa, ana ekrana dön
        elif self.onceki_durum == "bakim" and yeni_durum != "bakim":
            bakim.bakim_modundan_cik()
        
        elif yeni_durum == "oturum_yok" and self.onceki_durum != "oturum_yok":
            uyari.uyari_kapat()

        elif yeni_durum == "oturum_var" and self.onceki_durum != "oturum_var":
            uyari.uyari_kapat()
        
        self.olayi_isle(self.durum)

    def olayi_isle(self, olay):
        if self.durum == "oturum_yok":
            oturum_yok.olayi_isle(olay)
        elif self.durum == "oturum_var":
            oturum_var.mesaj_isle(olay)
        elif self.durum == "bakim":
            bakim.olayi_isle(olay)

    def modbus_mesaj(self, modbus_veri):
        if self.durum == "oturum_var":
            oturum_var.modbus_mesaj(modbus_veri)
        #elif self.durum == "bakim":
         #   bakim.modbus_mesaj(modbus_veri)
            

durum_makinesi = DurumMakinesi()
