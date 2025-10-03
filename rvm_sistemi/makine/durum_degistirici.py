from .senaryolar import oturum_var, oturum_yok, bakim

class DurumMakinesi:
    def __init__(self):
        self.durum = "oturum_yok"  # Başlangıç durumu
        self.onceki_durum = None  # Önceki durumu takip et
        self.bakim_url = "http://192.168.53.2:4321/bakim"  # Varsayılan bakım URL'i

    def durum_degistir(self, yeni_durum):
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.onceki_durum = self.durum
        self.durum = yeni_durum
        
        # Bakım moduna giriliyorsa, otomatik ekran değişimi
        if yeni_durum == "bakim" and self.onceki_durum != "bakim":
            bakim.bakim_moduna_gir(self.bakim_url)
        
        # Bakım modundan çıkılıyorsa, ana ekrana dön
        elif self.onceki_durum == "bakim" and yeni_durum != "bakim":
            bakim.bakim_modundan_cik()
        
        
        self.olayi_isle(self.durum)

    def olayi_isle(self, olay):
        if self.durum == "oturum_yok":
            oturum_yok.olayi_isle(olay)
        elif self.durum == "oturum_var":
            oturum_var.mesaj_isle(olay)
        elif self.durum == "bakim":
            bakim.olayi_isle(olay)

durum_makinesi = DurumMakinesi()
