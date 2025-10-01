from .senaryolar import oturum_var, oturum_yok, bakim

class DurumMakinesi:
    def __init__(self):
        self.durum = "oturum_yok"  # Başlangıç durumu

    def durum_degistir(self, yeni_durum):
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.durum = yeni_durum
        self.olayi_isle(self.durum)

    def olayi_isle(self, olay):
        if self.durum == "oturum_yok":
            oturum_yok.olayi_isle(olay)
        elif self.durum == "oturum_var":
            oturum_var.mesaj_isle(olay)
        elif self.durum == "bakim":
            bakim.olayi_isle(olay)

durum_makinesi = DurumMakinesi()
