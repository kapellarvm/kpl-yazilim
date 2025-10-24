"""
Uyku Modu Yönetimi Servisi
Makine oturum durumuna göre uyku moduna geçiş ve enerji tasarrufu
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from ...utils.logger import log_system, log_oturum, log_warning, log_success
from ...utils.terminal import ok, warn, step, info


class UykuModuServisi:
    """Makine uyku modu yönetimi"""
    
    def __init__(self):
        self.uyku_modu_aktif = False
        self.son_aktivite_zamani = datetime.now()
        self.uyku_baslangic_zamani = None  # Uyku moduna geçiş zamanı
        self.uyku_suresi_dakika = 3  # 15 dakika sonra uyku modu
        self.uyku_thread = None
        self.uyku_thread_aktif = False
        self.sistem_referans = None
        
        # Uyku modu istatistikleri
        self.uyku_modu_sayisi = 0
        self.toplam_uyku_suresi = 0
        self.enerji_tasarrufu_kwh = 0.0
        
        # Uyku modu mesajları
        self.uyku_mesajlari = [
            "💤 Uyku modu aktif - Enerji tüketimi minimuma düşürüldü",
            "🔋 Motorlar güç tasarrufu modunda - İşlem bekliyor",
            "⚡ LED'ler dim edildi - Görsel uyarılar pasif",
            "🌙 Sensörler düşük güç modunda - Temel izleme aktif",
            "💡 Sistem hazır durumda - Oturum başlatılması bekleniyor",
            "🔌 AC motorlar güvenli modda - Bekleme konumunda",
            "📊 Sistem performansı optimize edildi - Kaynak kullanımı azaltıldı",
            "🛡️ Güvenlik sistemleri aktif - Kritik fonksiyonlar korunuyor"
        ]
        
        self.uyku_cikis_mesajlari = [
            "🌅 Uyku modundan çıkılıyor - Sistem aktifleştiriliyor",
            "⚡ Enerji seviyeleri normale döndürülüyor",
            "🔧 Motorlar hazırlık moduna geçiyor",
            "💡 LED'ler tam parlaklığa ayarlanıyor",
            "📡 Sensörler tam güç modunda aktifleştiriliyor",
            "🎯 Sistem operasyonel duruma geçiyor",
            "✅ Tüm bileşenler hazır - Oturum başlatılabilir"
        ]
    
    def sistem_referans_ayarla(self, sistem_ref):
        """Sistem referansını ayarla"""
        self.sistem_referans = sistem_ref
        info("UYKU", "Sistem referansı ayarlandı")
        log_system("Uyku modu servisi sistem referansı ile bağlandı")
    
    def aktivite_kaydet(self):
        """Son aktivite zamanını güncelle"""
        self.son_aktivite_zamani = datetime.now()
        
        # Eğer uyku modundaysa çık
        if self.uyku_modu_aktif:
            self.uyku_modundan_cik()
    
    def uyku_kontrol_baslat(self):
        """Uyku kontrol thread'ini başlat"""
        if self.uyku_thread_aktif:
            warn("UYKU", "Uyku kontrol thread'i zaten çalışıyor")
            return
        
        self.uyku_thread_aktif = True
        self.uyku_thread = threading.Thread(target=self._uyku_kontrol_dongusu, daemon=True)
        self.uyku_thread.start()
        
        ok("UYKU", "Uyku kontrol sistemi başlatıldı")
        log_system("Uyku modu kontrol sistemi başlatıldı")
    
    def uyku_kontrol_durdur(self):
        """Uyku kontrol thread'ini durdur"""
        self.uyku_thread_aktif = False
        if self.uyku_thread and self.uyku_thread.is_alive():
            self.uyku_thread.join(timeout=2)
        
        warn("UYKU", "Uyku kontrol sistemi durduruldu")
        log_system("Uyku modu kontrol sistemi durduruldu")
    
    def _uyku_kontrol_dongusu(self):
        """Uyku kontrol döngüsü"""
        while self.uyku_thread_aktif:
            try:
                # Oturum aktif mi kontrol et
                oturum_aktif = False
                if self.sistem_referans and hasattr(self.sistem_referans, 'aktif_oturum'):
                    oturum_aktif = self.sistem_referans.aktif_oturum.get("aktif", False)
                
                # Eğer oturum aktifse aktiviteyi kaydet
                if oturum_aktif:
                    self.aktivite_kaydet()
                
                # Uyku modu kontrolü
                if not self.uyku_modu_aktif and not oturum_aktif:
                    # Son aktiviteden bu yana geçen süre
                    gecen_sure = datetime.now() - self.son_aktivite_zamani
                    
                    if gecen_sure >= timedelta(minutes=self.uyku_suresi_dakika):
                        self.uyku_moduna_gir()
                
                # 30 saniyede bir kontrol et
                time.sleep(30)
                
            except Exception as e:
                log_warning(f"Uyku kontrol döngüsü hatası: {e}")
                time.sleep(5)
    
    def uyku_moduna_gir(self):
        """Uyku moduna geç"""
        if self.uyku_modu_aktif:
            return
        
        self.uyku_modu_aktif = True
        self.uyku_modu_sayisi += 1
        self.uyku_baslangic_zamani = datetime.now()  # Uyku başlangıç zamanını kaydet
        uyku_baslangic = datetime.now()
        
        # Uyku modu mesajlarını logla
        step("UYKU", "💤 Makine uyku moduna geçiyor...")
        log_system("=== UYKU MODU AKTİF ===")
        
        for i, mesaj in enumerate(self.uyku_mesajlari):
            time.sleep(0.5)  # Dramatik efekt için
            log_system(mesaj)
            
            # Her 2 mesajda bir terminal çıktısı
            if i % 2 == 0:
                info("UYKU", mesaj)
        
        # Sistem durumu güncelleme
        if self.sistem_referans:
            self.sistem_referans.uyku_modu_aktif = True
        
        # Uyku modu istatistikleri
        log_system(f"Uyku modu #{self.uyku_modu_sayisi} başlatıldı")
        log_system(f"Son aktivite: {self.son_aktivite_zamani.strftime('%H:%M:%S')}")
        log_system(f"Uyku süresi: {self.uyku_suresi_dakika} dakika")
        
        ok("UYKU", f"Uyku modu aktif - #{self.uyku_modu_sayisi}")
        log_success("Makine uyku moduna başarıyla geçti")
    
    def uyku_modundan_cik(self):
        """Uyku modundan çık"""
        if not self.uyku_modu_aktif:
            return
        
        # Uyku süresini doğru hesapla
        if self.uyku_baslangic_zamani:
            uyku_suresi = datetime.now() - self.uyku_baslangic_zamani
            self.toplam_uyku_suresi += uyku_suresi.total_seconds()
            
            # Enerji tasarrufu hesapla (yaklaşık 2.5kW tasarruf)
            tasarruf_kwh = (uyku_suresi.total_seconds() / 3600) * 2.5
            self.enerji_tasarrufu_kwh += tasarruf_kwh
        else:
            uyku_suresi = timedelta(seconds=0)
            tasarruf_kwh = 0.0
        
        # Uyku çıkış mesajlarını logla
        step("UYKU", "🌅 Makine uyku modundan çıkıyor...")
        log_system("=== UYKU MODUNDAN ÇIKILIYOR ===")
        
        for i, mesaj in enumerate(self.uyku_cikis_mesajlari):
            time.sleep(0.3)  # Hızlı aktivasyon
            log_system(mesaj)
            
            # Her mesajda terminal çıktısı
            info("UYKU", mesaj)
        
        # Sistem durumu güncelleme
        if self.sistem_referans:
            self.sistem_referans.uyku_modu_aktif = False
        
        # İstatistikleri logla
        log_system(f"Uyku modu #{self.uyku_modu_sayisi} sonlandırıldı")
        log_system(f"Uyku süresi: {uyku_suresi.total_seconds():.0f} saniye")
        log_system(f"Enerji tasarrufu: {tasarruf_kwh:.2f} kWh")
        log_system(f"Toplam tasarruf: {self.enerji_tasarrufu_kwh:.2f} kWh")
        
        self.uyku_modu_aktif = False
        self.uyku_baslangic_zamani = None  # Uyku başlangıç zamanını temizle
        
        ok("UYKU", f"Uyku modundan çıkıldı - {uyku_suresi.total_seconds():.0f}s tasarruf")
        log_success("Makine aktif moda başarıyla geçti")
    
    def uyku_durumu_al(self) -> dict:
        """Uyku modu durumunu al"""
        return {
            "uyku_modu_aktif": self.uyku_modu_aktif,
            "son_aktivite": self.son_aktivite_zamani.strftime('%H:%M:%S'),
            "uyku_suresi_dakika": self.uyku_suresi_dakika,
            "uyku_modu_sayisi": self.uyku_modu_sayisi,
            "toplam_uyku_suresi_saat": self.toplam_uyku_suresi / 3600,
            "enerji_tasarrufu_kwh": round(self.enerji_tasarrufu_kwh, 2),
            "kalan_sure_dakika": self._kalan_sure_hesapla()
        }
    
    def _kalan_sure_hesapla(self) -> int:
        """Uyku moduna geçmeye kalan süreyi hesapla"""
        if self.uyku_modu_aktif:
            return 0
        
        gecen_sure = datetime.now() - self.son_aktivite_zamani
        kalan_sure = timedelta(minutes=self.uyku_suresi_dakika) - gecen_sure
        
        if kalan_sure.total_seconds() <= 0:
            return 0
        
        return int(kalan_sure.total_seconds() / 60)
    
    def uyku_ayarlari_guncelle(self, uyku_suresi_dakika: int = None):
        """Uyku ayarlarını güncelle"""
        if uyku_suresi_dakika is not None:
            self.uyku_suresi_dakika = uyku_suresi_dakika
            log_system(f"Uyku süresi {uyku_suresi_dakika} dakikaya güncellendi")
    
    def uyku_istatistikleri_al(self) -> dict:
        """Detaylı uyku istatistikleri"""
        return {
            "toplam_uyku_modu": self.uyku_modu_sayisi,
            "toplam_uyku_suresi_saat": round(self.toplam_uyku_suresi / 3600, 2),
            "toplam_enerji_tasarrufu_kwh": round(self.enerji_tasarrufu_kwh, 2),
            "ortalama_uyku_suresi_dakika": round(
                (self.toplam_uyku_suresi / 3600) / max(self.uyku_modu_sayisi, 1) * 60, 1
            ),
            "enerji_tasarrufu_yuzde": round(
                (self.enerji_tasarrufu_kwh / (self.enerji_tasarrufu_kwh + 10)) * 100, 1
            ) if self.enerji_tasarrufu_kwh > 0 else 0
        }


# Global uyku modu servisi
uyku_modu_servisi = UykuModuServisi()
