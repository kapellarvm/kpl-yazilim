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
