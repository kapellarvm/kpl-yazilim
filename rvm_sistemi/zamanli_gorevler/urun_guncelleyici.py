"""
Ürün Güncelleyici - Zamanlı Görev
DİM-DB'den ürün listesini periyodik olarak günceller
"""

import asyncio
import schedule
import time
from ..dimdb import istemci


class UrunGuncelleyici:
    """Ürün listesini periyodik olarak güncelleyen sınıf"""
    
    def __init__(self, guncelleme_sikligi_saat=6, ilk_guncelleme_yap=True):
        """
        Args:
            guncelleme_sikligi_saat (int): Güncelleme sıklığı (saat cinsinden)
            ilk_guncelleme_yap (bool): İlk güncellemeyi hemen yapıp yapmama
        """
        self.guncelleme_sikligi_saat = guncelleme_sikligi_saat
        self.ilk_guncelleme_yap = ilk_guncelleme_yap
        self.calistiriliyor = False
        
    async def baslat(self):
        """Ürün güncelleme zamanlayıcısını başlatır"""
        if self.calistiriliyor:
            print("⚠️ [URUN_GUNCELLEYICI] Zaten çalışıyor!")
            return
            
        self.calistiriliyor = True
        print(f"🔄 [URUN_GUNCELLEYICI] Başlatılıyor (her {self.guncelleme_sikligi_saat} saatte bir)")
        
        # İlk güncellemeyi yap (eğer isteniyorsa)
        if self.ilk_guncelleme_yap:
            print("🔄 [URUN_GUNCELLEYICI] İlk güncelleme yapılıyor...")
            await self._urun_guncelle()
        else:
            print("⏭️ [URUN_GUNCELLEYICI] İlk güncelleme atlandı")
        
        # Periyodik güncellemeyi ayarla
        schedule.every(self.guncelleme_sikligi_saat).hours.do(
            lambda: asyncio.create_task(self._urun_guncelle())
        )
        
        # Zamanlayıcıyı çalıştır
        await self._zamanlayici_dongusu()
    
    async def _zamanlayici_dongusu(self):
        """Zamanlayıcı döngüsünü çalıştırır"""
        while self.calistiriliyor:
            schedule.run_pending()
            await asyncio.sleep(1)
    
    async def _urun_guncelle(self):
        """Ürün listesini günceller"""
        try:
            print(f"🔄 [URUN_GUNCELLEYICI] Ürün güncellemesi başlatılıyor... ({time.strftime('%H:%M:%S')})")
            await istemci.get_all_products_and_save()
            print(f"✅ [URUN_GUNCELLEYICI] Ürün güncellemesi tamamlandı ({time.strftime('%H:%M:%S')})")
        except Exception as e:
            print(f"❌ [URUN_GUNCELLEYICI] Ürün güncelleme hatası: {e}")
    
    def durdur(self):
        """Ürün güncelleme zamanlayıcısını durdurur"""
        if not self.calistiriliyor:
            print("⚠️ [URUN_GUNCELLEYICI] Zaten durmuş!")
            return
            
        self.calistiriliyor = False
        print("⏹️ [URUN_GUNCELLEYICI] Durduruldu")
    
    def manuel_guncelle(self):
        """Manuel ürün güncellemesi başlatır"""
        print("🔄 [URUN_GUNCELLEYICI] Manuel güncelleme başlatılıyor...")
        asyncio.create_task(self._urun_guncelle())
    
    def durum_bilgisi(self):
        """Mevcut durum bilgisini döndürür"""
        return {
            "calistiriliyor": self.calistiriliyor,
            "guncelleme_sikligi_saat": self.guncelleme_sikligi_saat,
            "ilk_guncelleme_yap": self.ilk_guncelleme_yap,
            "sonraki_guncelleme": schedule.next_run() if self.calistiriliyor else None
        }


# Global instance
urun_guncelleyici = UrunGuncelleyici(
    guncelleme_sikligi_saat=6,
    ilk_guncelleme_yap=False  # İlk güncellemeyi yapma
)
