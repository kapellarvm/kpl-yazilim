"""
sensor_karti.py - Sensor Card Communication (Yeni Temiz Versiyon)
State-driven, event-based, tek thread'li, stabil mimari

API KOMPATİBİLİTE: Tüm mevcut fonksiyonlar korundu!
"""

from typing import Optional, Callable

from rvm_sistemi.makine.seri.base_card import BaseCard
from rvm_sistemi.utils.logger import log_system, log_success, log_warning


class SensorKart(BaseCard):
    """
    Sensor Kartı Sınıfı

    Özellikler:
    - State-driven communication
    - Single worker thread
    - Event-based message processing
    - Automatic recovery
    - Güvenlik kartı komutları yönlendirme (# ile başlayanlar)

    API (GERİYE UYUMLU):
    - loadcell_olc(), tare(), teach()
    - led_ac(), led_kapat(), led_pwm()
    - ezici_ileri(), ezici_geri(), ezici_dur()
    - kirici_ileri(), kirici_geri(), kirici_dur()
    - Güvenlik kartı komutları: ust_kilit_ac(), alt_kilit_ac(), vb.
    - ping(), reset()
    """

    def __init__(self, port_adi: Optional[str] = None, callback: Optional[Callable] = None, cihaz_adi: str = "sensor"):
        """
        Sensor kartı başlatıcı

        Args:
            port_adi: Seri port adı
            callback: Mesaj callback fonksiyonu
            cihaz_adi: Cihaz adı
        """
        super().__init__(port=port_adi, callback=callback, device_name=cihaz_adi)

        # Port adı (geriye uyumluluk için)
        self.port_adi = port_adi
        self.cihaz_adi = cihaz_adi

        # Sağlık durumu (geriye uyumluluk için)
        self.saglikli = False

        log_system(f"[{self.cihaz_adi}] SensorKart initialized")

    # ============ ABSTRACT METHOD IMPLEMENTATIONS ============

    def _get_expected_boot_messages(self) -> list:
        """Return expected boot messages"""
        # Sensor kartı boot mesajları daha basit
        return []  # Boot'u "resetlendi" mesajı ile tamamla

    def _send_initial_config(self) -> None:
        """Send initial configuration (sensor kartı için ekstra config yok)"""
        pass

    def _process_application_message(self, msg: str) -> None:
        """
        Process application-specific messages

        Args:
            msg: Message from sensor card
        """
        # Güvenlik kartından gelen mesajlar (g/ ile başlar)
        if msg.startswith("g/"):
            security_msg = msg[2:]  # "g/" kısmını kaldır
            if self.callback:
                try:
                    self.callback(security_msg)
                except Exception as e:
                    log_warning(f"[{self.cihaz_adi}] Callback error: {e}")
        else:
            # Sensor kartından gelen mesajlar
            if self.callback:
                try:
                    self.callback(msg)
                except Exception as e:
                    log_warning(f"[{self.cihaz_adi}] Callback error: {e}")

    # ============ OVERRIDES FOR STATE MANAGEMENT ============

    def _on_boot_message(self) -> None:
        """Override: Sensor kartı boot sequence'ı daha basit"""
        from rvm_sistemi.makine.seri.base_card import CardState

        if self._state != CardState.CONNECTING:
            return

        # Sensor kartı için boot'u hemen tamamla
        log_system(f"[{self.cihaz_adi}] Boot message received")

        # Send identification
        self._write_queue.put(b's\n')

        # Send boot confirmation
        self._write_queue.put(b'b\n')

        # Boot tamamlandı (kalibrasyon bekleme yok)
        self._transition_to(CardState.CONNECTED)

        # İlk ping gönder
        self._write_queue.put(b'ping\n')

    def _on_pong_received(self) -> None:
        """Override: Update saglikli flag"""
        super()._on_pong_received()
        self.saglikli = True

    def _on_io_error(self) -> None:
        """Override: Update saglikli flag"""
        self.saglikli = False
        super()._on_io_error()

    def _on_ping_failed(self) -> None:
        """Override: Update saglikli flag"""
        self.saglikli = False
        super()._on_ping_failed()

    # ============ PUBLIC API (GERİYE UYUMLU) ============

    # --- Loadcell ---

    def loadcell_olc(self) -> None:
        """Loadcell ölçüm yap"""
        self._send_command(b"lo\n")

    def teach(self) -> None:
        """Loadcell teach"""
        self._send_command(b"gst\n")

    def tare(self) -> None:
        """Loadcell tare"""
        self._send_command(b"lst\n")

    def agirlik_olc(self) -> bool:
        """Ağırlık ölçümü (alias)"""
        self.loadcell_olc()
        return True

    # --- LED Kontrolü ---

    def led_ac(self) -> None:
        """LED aç (animasyonlu)"""
        self._send_command(b"as\n")

    def led_kapat(self) -> None:
        """LED kapat (animasyonlu)"""
        self._send_command(b"ad\n")

    def led_full_ac(self) -> None:
        """LED full aç"""
        self._send_command(b"la\n")

    def led_full_kapat(self) -> None:
        """LED full kapat"""
        self._send_command(b"ls\n")

    def led_pwm(self, deger: int) -> None:
        """
        LED PWM ayarla

        Args:
            deger: PWM değeri (0-100)
        """
        self._send_command(f"l:{deger}\n".encode())

    # --- Ezici Motor Kontrolü ---

    def ezici_ileri(self) -> None:
        """Ezici ileri"""
        self._send_command(b"ei\n")

    def ezici_geri(self) -> None:
        """Ezici geri"""
        self._send_command(b"eg\n")

    def ezici_dur(self) -> None:
        """Ezici dur"""
        self._send_command(b"ed\n")

    # --- Kırıcı Motor Kontrolü ---

    def kirici_ileri(self) -> None:
        """Kırıcı ileri"""
        self._send_command(b"ki\n")

    def kirici_geri(self) -> None:
        """Kırıcı geri"""
        self._send_command(b"kg\n")

    def kirici_dur(self) -> None:
        """Kırıcı dur"""
        self._send_command(b"kd\n")

    # --- Durum Sorguları ---

    def doluluk_oranı(self) -> None:
        """Doluluk oranı sorgula"""
        self._send_command(b"do\n")

    def sds_sensorler(self) -> bool:
        """SDS sensör durumları (eski API)"""
        self._send_command(b"sds\n")
        return True

    # --- Makine Durumu ---

    def makine_oturum_var(self) -> None:
        """Makine oturum var"""
        self._send_command(b"mov\n")

    def makine_oturum_yok(self) -> None:
        """Makine oturum yok"""
        self._send_command(b"moy\n")

    def makine_bakim_modu(self) -> None:
        """Makine bakım modu"""
        self._send_command(b"mb\n")

    # --- Güvenlik Kartı Komutları (# ile başlar) ---

    def ust_kilit_ac(self) -> None:
        """Üst kilit aç"""
        self._send_command(b"#uka\n")

    def ust_kilit_kapat(self) -> None:
        """Üst kilit kapat"""
        self._send_command(b"#ukk\n")

    def alt_kilit_ac(self) -> None:
        """Alt kilit aç"""
        self._send_command(b"#aka\n")

    def alt_kilit_kapat(self) -> None:
        """Alt kilit kapat"""
        self._send_command(b"#akk\n")

    def ust_kilit_durum_sorgula(self) -> None:
        """Üst kilit durum sorgula"""
        self._send_command(b"#msud\n")

    def alt_kilit_durum_sorgula(self) -> None:
        """Alt kilit durum sorgula"""
        self._send_command(b"#msad\n")

    def bme_guvenlik(self) -> None:
        """BME güvenlik sensörü oku"""
        self._send_command(b"#bme\n")

    def manyetik_saglik(self) -> None:
        """Manyetik sensör sağlık durumu"""
        self._send_command(b"#mesd\n")

    def fan_pwm(self, deger: int) -> None:
        """
        Fan PWM ayarla

        Args:
            deger: PWM değeri (0-100)
        """
        self._send_command(f"#f:{deger}\n".encode())

    def bypass_modu_ac(self) -> None:
        """Bypass modu aç"""
        self._send_command(b"#bypa\n")

    def bypass_modu_kapat(self) -> None:
        """Bypass modu kapat"""
        self._send_command(b"#bypp\n")

    def guvenlik_role_reset(self) -> None:
        """Güvenlik role reset"""
        self._send_command(b"#gr\n")

    def guvenlik_kart_reset(self) -> None:
        """Güvenlik kartı reset"""
        self._send_command(b"#reset\n")

    # --- Sağlık Kontrolü ---

    def getir_saglik_durumu(self) -> bool:
        """
        Sağlık durumu al

        Returns:
            bool: Sağlıklı mı?
        """
        return self.saglikli

    # --- Geriye Uyumluluk İçin Eski Metodlar ---

    def portu_ac(self) -> bool:
        """
        Port aç (geriye uyumluluk için)

        Returns:
            bool: Başarılı mı?
        """
        if self.is_ready():
            return True

        return self.start()

    def dinlemeyi_baslat(self) -> None:
        """Dinlemeyi başlat (geriye uyumluluk için)"""
        if not self._running:
            self.start()

    def dinlemeyi_durdur(self) -> None:
        """Dinlemeyi durdur (geriye uyumluluk için)"""
        self.stop()


# ============ GERİYE UYUMLULUK İÇİN ALIAS ============
# Eski import'lar çalışsın diye
Sensor = SensorKart
