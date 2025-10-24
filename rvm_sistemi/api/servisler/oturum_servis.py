"""
Oturum Yönetimi Servisleri
Oturum başlatma, sonlandırma ve yönetim işlemleri
"""

from ...makine.senaryolar import oturum_var
from ...utils.logger import log_oturum, log_warning, log_system
from ...utils.terminal import ok, warn, step
from .uyku_modu_servisi import uyku_modu_servisi


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
        
        # Uyku modu aktivitesini kaydet
        uyku_modu_servisi.aktivite_kaydet()
        
        ok("OTURUM", f"DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")
        log_oturum(f"DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

    @staticmethod
    def oturum_sonlandir() -> None:
        """Oturumu sonlandır - DİM-DB bildirimi sunucu tarafından yapılacak"""
        from ...makine.uyari_yoneticisi import uyari_yoneticisi
        
        uyari_yoneticisi.uyari_kapat()
        
        if not oturum_var.sistem.aktif_oturum["aktif"]:
            warn("OTURUM", "Aktif oturum yok, sonlandırma yapılmadı")
            log_warning("Aktif oturum yok, sonlandırma yapılmadı")
            return

        step("OTURUM", f"Oturum sonlandırılıyor: {oturum_var.sistem.aktif_oturum['sessionId']}")
        log_oturum(f"Oturum sonlandırılıyor: {oturum_var.sistem.aktif_oturum['sessionId']}")
        
        # Oturumu temizle
        oturum_var.sistem.aktif_oturum = {
            "aktif": False,
            "sessionId": None,
            "userId": None,
            "paket_uuid_map": {}
        }
        
        oturum_var.sistem.onaylanan_urunler.clear()
        ok("OTURUM", "Yerel oturum temizlendi")
        log_system("Yerel oturum temizlendi")
