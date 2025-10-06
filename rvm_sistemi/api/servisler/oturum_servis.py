"""
Oturum Yönetimi Servisleri
Oturum başlatma, sonlandırma ve yönetim işlemleri
"""

from ...makine.senaryolar import oturum_var


class OturumServis:
    """Oturum yönetimi işlemlerini yöneten servis sınıfı"""
    
    @staticmethod
    def oturum_baslat(session_id: str, user_id: str) -> None:
        """DİM-DB'den gelen oturum başlatma"""
        oturum_var.sistem.aktif_oturum = {
            "aktif": True,
            "sessionId": session_id,
            "userId": user_id,
            "paket_uuid_map": {}
        }
        
        print(f"✅ [OTURUM] DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

    @staticmethod
    def oturum_sonlandir() -> None:
        """Oturumu sonlandır - DİM-DB bildirimi sunucu tarafından yapılacak"""
        from ...makine.uyari_yoneticisi import uyari_yoneticisi
        
        uyari_yoneticisi.uyari_kapat()
        oturum_var.sistem.sensor_ref.tare()
        
        if not oturum_var.sistem.aktif_oturum["aktif"]:
            print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
            return

        print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {oturum_var.sistem.aktif_oturum['sessionId']}")
        
        # Oturumu temizle
        oturum_var.sistem.aktif_oturum = {
            "aktif": False,
            "sessionId": None,
            "userId": None,
            "paket_uuid_map": {}
        }
        
        oturum_var.sistem.onaylanan_urunler.clear()
        print(f"🧹 [OTURUM] Yerel oturum temizlendi")
