"""
Ürün Güncelleyici - Zamanlı Görev
DİM-DB'den ürün listesini periyodik olarak günceller
"""

import asyncio
import time
from ..dimdb import dimdb_istemcisi
from ..utils.logger import log_system, log_error, log_success, log_warning


class UrunGuncelleyici:
    """Ürün listesini periyodik olarak güncelleyen sınıf"""
    
    def __init__(self, guncelleme_sikligi_dakika=5, ilk_guncelleme_yap=True):
        """
        Args:
            guncelleme_sikligi_dakika (int): Güncelleme sıklığı (dakika cinsinden)
            ilk_guncelleme_yap (bool): İlk güncellemeyi hemen yapıp yapmama
        """
        self.guncelleme_sikligi_dakika = guncelleme_sikligi_dakika
        self.ilk_guncelleme_yap = ilk_guncelleme_yap
        self.calistiriliyor = False
        self._gorev = None
        
    async def baslat(self):
        """Ürün güncelleme zamanlayıcısını başlatır"""
        if self.calistiriliyor:
            print("⚠️ [URUN_GUNCELLEYICI] Zaten çalışıyor!")
            log_warning("Ürün güncelleyici zaten çalışıyor!")
            return
            
        self.calistiriliyor = True
        print(f"🔄 [URUN_GUNCELLEYICI] Başlatılıyor (her {self.guncelleme_sikligi_dakika} dakikada bir)")
        log_system(f"Ürün güncelleyici başlatılıyor (her {self.guncelleme_sikligi_dakika} dakikada bir)")
        
        # İlk güncellemeyi yap (eğer isteniyorsa)
        if self.ilk_guncelleme_yap:
            print("🔄 [URUN_GUNCELLEYICI] İlk güncelleme yapılıyor...")
            log_system("İlk ürün güncellemesi yapılıyor...")
            await self._urun_guncelle()
        else:
            print("⏭️ [URUN_GUNCELLEYICI] İlk güncelleme atlandı")
            log_system("İlk ürün güncellemesi atlandı")
        
        # Zamanlayıcı döngüsünü başlat
        self._gorev = asyncio.create_task(self._zamanlayici_dongusu())
        
    async def _zamanlayici_dongusu(self):
        """Zamanlayıcı döngüsünü çalıştırır"""
        while self.calistiriliyor:
            # Dakika cinsinden saniyeye çevir: dakika * 60 = saniye
            await asyncio.sleep(self.guncelleme_sikligi_dakika * 60)
            
            if self.calistiriliyor:
                print(f"🔄 [URUN_GUNCELLEYICI] Periyodik güncelleme zamanı geldi...")
                log_system("Periyodik ürün güncelleme zamanı geldi...")
                await self._urun_guncelle()
    
    async def _urun_guncelle(self):
        """Ürün listesini günceller"""
        try:
            # UTC saatini kullan
            utc_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            print(f"🔄 [URUN_GUNCELLEYICI] Ürün güncellemesi başlatılıyor... ({utc_time})")
            log_system(f"Ürün güncellemesi başlatılıyor... ({utc_time})")
            await dimdb_istemcisi.get_all_products_and_save()
            utc_time_end = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            print(f"✅ [URUN_GUNCELLEYICI] Ürün güncellemesi tamamlandı ({utc_time_end})")
            log_success(f"Ürün güncellemesi tamamlandı ({utc_time_end})")
        except Exception as e:
            print(f"❌ [URUN_GUNCELLEYICI] Ürün güncelleme hatası: {e}")
            import traceback
            print(f"❌ [URUN_GUNCELLEYICI] Hata detayı: {traceback.format_exc()}")
            log_error(f"Ürün güncelleme hatası: {e}")
            log_error(f"Hata detayı: {traceback.format_exc()}")
    
    def durdur(self):
        """Ürün güncelleme zamanlayıcısını durdurur"""
        if not self.calistiriliyor:
            print("⚠️ [URUN_GUNCELLEYICI] Zaten durmuş!")
            log_warning("Ürün güncelleyici zaten durmuş!")
            return
            
        self.calistiriliyor = False
        if self._gorev:
            self._gorev.cancel()
        print("⏹️ [URUN_GUNCELLEYICI] Durduruldu")
        log_system("Ürün güncelleyici durduruldu")
    
    def manuel_guncelle(self):
        """Manuel ürün güncellemesi başlatır"""
        print("🔄 [URUN_GUNCELLEYICI] Manuel güncelleme başlatılıyor...")
        log_system("Manuel ürün güncellemesi başlatılıyor...")
        asyncio.create_task(self._urun_guncelle())
    
    def durum_bilgisi(self):
        """Mevcut durum bilgisini döndürür"""
        return {
            "calistiriliyor": self.calistiriliyor,
            "guncelleme_sikligi_dakika": self.guncelleme_sikligi_dakika,
            "ilk_guncelleme_yap": self.ilk_guncelleme_yap,
            "sonraki_guncelleme": f"{self.guncelleme_sikligi_dakika} dakika sonra" if self.calistiriliyor else None,
            "mevcut_utc_saat": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            "mevcut_yerel_saat": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        }


# Global instance
urun_guncelleyici = UrunGuncelleyici(
    guncelleme_sikligi_dakika=1,  # 5 dakikada bir güncelle
    ilk_guncelleme_yap=True  # İlk güncellemeyi yap
)