<<<<<<< HEAD
from senaryolar import oturum_var, oturum_yok, bakim

class DurumMakinesi:
    def __init__(self):
        self.durum = "oturum_yok"  # Başlangıç durumu

    def durum_degistir(self, yeni_durum):
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.durum = yeni_durum

    def olayi_isle(self, olay):
        if self.durum == "oturum_yok":
            oturum_yok.olayi_isle(olay)
        elif self.durum == "oturum_var":
            oturum_var.olayi_isle(olay)
        elif self.durum == "bakim":
            bakim.olayi_isle(olay)

durum_makinesi = DurumMakinesi()
=======
# rvm_sistemi/makine/mod_degistirici.py

class DurumMakinesi:
    """
    RVM'nin anlık çalışma durumunu (oturum_yok, oturum_var, bakim)
    yöneten merkezi sınıf.
    """
    # DÜZELTME: Metot adı '__init__' olmalıdır (çift alt çizgi).
    def __init__(self):
        self.durum = "oturum_yok" # Başlangıç durumu
        print(f"Durum makinesi başlatıldı. Mevcut durum: {self.durum}")

    def durum_degistir(self, yeni_durum):
        """Mevcut durumu güvenli bir şekilde değiştirir."""
        if self.durum == yeni_durum:
            return # Durum zaten aynıysa bir şey yapma
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.durum = yeni_durum

# Uygulamanın her yerinden erişilecek olan tek durum makinesi nesnesi
durum_makinesi = DurumMakinesi()
>>>>>>> b8ab3112ccea751c6f4d39f86f75c9ac5a6f3cb3
