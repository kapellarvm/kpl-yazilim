"""
motor_karti.py - Motor Card Communication (Yeni Temiz Versiyon)
State-driven, event-based, tek thread'li, stabil mimari

API KOMPATİBİLİTE: Tüm mevcut fonksiyonlar korundu!
"""

from typing import Optional, Callable

from rvm_sistemi.makine.seri.base_card import BaseCard
from rvm_sistemi.utils.logger import log_system, log_success, log_warning


class MotorKart(BaseCard):
    """
    Motor Kartı Sınıfı

    Özellikler:
    - State-driven communication
    - Single worker thread
    - Event-based message processing
    - Automatic recovery

    API (GERİYE UYUMLU):
    - parametre_gonder()
    - konveyor_ileri(), konveyor_geri(), konveyor_dur()
    - yonlendirici_plastik(), yonlendirici_cam(), yonlendirici_dur()
    - klape_metal(), klape_plastik()
    - ping(), reset()
    """

    def __init__(self, port_adi: Optional[str] = None, callback: Optional[Callable] = None, cihaz_adi: str = "motor"):
        """
        Motor kartı başlatıcı

        Args:
            port_adi: Seri port adı
            callback: Mesaj callback fonksiyonu
            cihaz_adi: Cihaz adı
        """
        super().__init__(port=port_adi, callback=callback, device_name=cihaz_adi)

        # Motor parametreleri (MEVCUT DEĞİŞKENLER KORUNDU)
        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200

        # Klape flag (MEVCUT MANTIK KORUNDU)
        self.klape_flag = False

        # Port adı (geriye uyumluluk için)
        self.port_adi = port_adi
        self.cihaz_adi = cihaz_adi

        # Sağlık durumu (geriye uyumluluk için)
        self.saglikli = False

        log_system(f"[{self.cihaz_adi}] MotorKart initialized")

    # ============ ABSTRACT METHOD IMPLEMENTATIONS ============

    def _get_expected_boot_messages(self) -> list:
        """Return expected boot messages"""
        return ["ykt", "skt", "yino", "kino", "yono"]

    def _send_initial_config(self) -> None:
        """Send initial motor parameters"""
        self.parametre_gonder()

    def _process_application_message(self, msg: str) -> None:
        """
        Process application-specific messages

        Args:
            msg: Message from motor card
        """
        # Application mesajlarını callback'e ilet
        if self.callback:
            try:
                self.callback(msg)
            except Exception as e:
                log_warning(f"[{self.cihaz_adi}] Callback error: {e}")

    # ============ OVERRIDES FOR STATE MANAGEMENT ============

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

    # --- Motor Parametreleri ---

    def parametre_gonder(self) -> None:
        """Motor parametrelerini gönder"""
        if not self.is_ready():
            log_warning(f"[{self.cihaz_adi}] Cannot send parameters - not ready")
            return

        # Parametreleri sırayla gönder
        self._send_command(f"kh{self.konveyor_hizi}\n".encode())
        self._send_command(f"yh{self.yonlendirici_hizi}\n".encode())
        self._send_command(f"sh{self.klape_hizi}\n".encode())

        log_system(f"[{self.cihaz_adi}] Parameters sent: K:{self.konveyor_hizi} Y:{self.yonlendirici_hizi} S:{self.klape_hizi}")

    def parametre_degistir(self, konveyor: Optional[int] = None, yonlendirici: Optional[int] = None, klape: Optional[int] = None) -> None:
        """Motor parametrelerini değiştir"""
        if konveyor is not None:
            self.konveyor_hizi = konveyor
        if yonlendirici is not None:
            self.yonlendirici_hizi = yonlendirici
        if klape is not None:
            self.klape_hizi = klape

        self.parametre_gonder()

    def konveyor_hiz_ayarla(self, hiz: int) -> None:
        """Konveyör hızını ayarla"""
        self.konveyor_hizi = hiz
        self.parametre_gonder()

    def yonlendirici_hiz_ayarla(self, hiz: int) -> None:
        """Yönlendirici hızını ayarla"""
        self.yonlendirici_hizi = hiz
        self.parametre_gonder()

    def klape_hiz_ayarla(self, hiz: int) -> None:
        """Klape hızını ayarla"""
        self.klape_hizi = hiz
        self.parametre_gonder()

    # --- Motor Kontrol ---

    def motorlari_aktif_et(self) -> None:
        """Motorları aktif et"""
        self._send_command(b"aktif\n")

    def motorlari_iptal_et(self) -> None:
        """Motorları iptal et"""
        self._send_command(b"iptal\n")

    # --- Konveyör Kontrolü ---

    def konveyor_ileri(self) -> None:
        """Konveyör ileri"""
        self._send_command(b"kmi\n")

    def konveyor_geri(self) -> None:
        """Konveyör geri"""
        self._send_command(b"kmg\n")

    def konveyor_dur(self) -> None:
        """Konveyör dur"""
        self._send_command(b"kmd\n")

    def konveyor_problem_var(self) -> None:
        """Konveyör problem var"""
        self._send_command(b"pv\n")

    def konveyor_problem_yok(self) -> None:
        """Konveyör problem yok"""
        self._send_command(b"py\n")

    # --- Mesafe Ölçümü ---

    def mesafe_baslat(self) -> None:
        """Mesafe ölçümünü başlat"""
        self._send_command(b"mb\n")

    def mesafe_bitir(self) -> None:
        """Mesafe ölçümünü bitir"""
        self._send_command(b"ms\n")

    # --- Yönlendirici Kontrolü ---

    def yonlendirici_plastik(self) -> None:
        """Yönlendirici plastik konuma git"""
        self._send_command(b"ymp\n")

    def yonlendirici_cam(self) -> None:
        """Yönlendirici cam konuma git"""
        self._send_command(b"ymc\n")

    def yonlendirici_dur(self) -> None:
        """Yönlendirici durdur"""
        self._send_command(b"ymd\n")

    def yonlendirici_sensor_teach(self) -> None:
        """Yönlendirici sensör teach"""
        self._send_command(b"yst\n")

    # --- Klape Kontrolü (MEVCUT MANTIK KORUNDU) ---

    def klape_metal(self) -> None:
        """Klape metal konuma git"""
        self._send_command(b"smm\n")
        self.klape_flag = True

    def klape_plastik(self) -> None:
        """Klape plastik konuma git (flag kontrolü ile)"""
        if self.klape_flag:
            self._send_command(b"smp\n")
            self.klape_flag = False

    # --- Sensör Komutları ---

    def bme_sensor_veri(self) -> None:
        """BME sensör verisi al"""
        self._send_command(b"bme\n")

    def sensor_saglik_durumu(self) -> None:
        """Sensör sağlık durumu al"""
        self._send_command(b"msd\n")

    def atik_uzunluk(self) -> None:
        """Atık uzunluk ölç"""
        self._send_command(b"au\n")

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
Motor = MotorKart
