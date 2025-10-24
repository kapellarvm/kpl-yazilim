"""
System State Manager - Temiz bayrak yapısı
Tüm USB reset ve reconnection işlemlerini merkezi olarak yönetir
"""

import threading
import time
from enum import Enum
from typing import Dict, Optional, Set
from dataclasses import dataclass
from rvm_sistemi.utils.logger import log_system, log_warning, log_error, log_success
from rvm_sistemi.makine.senaryolar import uyari


class SystemState(Enum):
    """Sistem durumları"""
    NORMAL = "normal"                    # Normal çalışma
    USB_RESETTING = "usb_resetting"     # USB reset devam ediyor
    RECONNECTING = "reconnecting"        # Kartlar yeniden bağlanıyor
    POWER_RECOVERY = "power_recovery"    # Güç kesintisi sonrası kurtarma
    EMERGENCY = "emergency"              # Acil durum - tüm işlemler durdur


class CardState(Enum):
    """Kart durumları"""
    CONNECTED = "connected"              # Bağlı ve sağlıklı
    DISCONNECTED = "disconnected"       # Bağlantı yok
    RECONNECTING = "reconnecting"        # Yeniden bağlanıyor
    ERROR = "error"                      # Hata durumu
    DISABLED = "disabled"                # Devre dışı (manuel)


@dataclass
class ResetOperation:
    """Reset operasyonu bilgisi"""
    operation_id: str
    start_time: float
    timeout: float
    cards_involved: Set[str]
    initiated_by: str  # "port_health", "card_error", "manual"


class SystemStateManager:
    """
    Merkezi sistem durumu yöneticisi
    Tüm USB reset ve reconnection işlemlerini koordine eder
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Sistem durumu
        self._system_state = SystemState.NORMAL
        self._state_lock = threading.RLock()
        
        # Kart durumları
        self._card_states: Dict[str, CardState] = {}
        self._card_lock = threading.RLock()
        
        # Reset operasyonları
        self._active_reset: Optional[ResetOperation] = None
        self._reset_lock = threading.RLock()
        
        # Reconnection takibi
        self._reconnecting_cards: Set[str] = set()
        self._reconnection_start_times: Dict[str, float] = {}  # ✅ Reconnection timing
        self._reconnect_lock = threading.RLock()
        
        # Reset kontrolü - timeout yerine bayrak
        self._reset_in_progress = False
        self._reset_cooldown = False
        
        # Thread takibi
        self._active_threads: Dict[str, threading.Thread] = {}
        self._thread_lock = threading.RLock()

        # ✅ PORT SAHİPLİĞİ TAKİBİ - Temel mimari çözüm
        self._owned_ports: Dict[str, tuple[str, float]] = {}  # port -> (card_name, claim_timestamp)
        self._port_lock = threading.RLock()

        # ✅ USB DEVICE TRACKING - Touchscreen & Camera sağlık izleme
        # Agresif reset sonrası güncellenir (update_usb_baseline)
        self.touchscreen_device_num: Optional[str] = None  # "075" veya None
        self.camera_device_num: Optional[str] = None       # "002" veya None
        self._usb_baseline_lock = threading.RLock()

        self._initialized = True
        log_system("System State Manager başlatıldı")
    
    # ============ SISTEM DURUMU YÖNETİMİ ============
    
    def get_system_state(self) -> SystemState:
        """Mevcut sistem durumunu al"""
        with self._state_lock:
            return self._system_state
    
    def set_system_state(self, new_state: SystemState, reason: str = "") -> bool:
        """
        Sistem durumunu değiştir
        
        Args:
            new_state: Yeni durum
            reason: Değişiklik nedeni
            
        Returns:
            bool: Değişiklik başarılı mı?
        """
        with self._state_lock:
            old_state = self._system_state
            
            # Durum geçiş kontrolü
            if not self._is_valid_state_transition(old_state, new_state):
                log_warning(f"Geçersiz durum geçişi: {old_state.value} -> {new_state.value}")
                return False
            
            self._system_state = new_state
            
            # RECONNECTING durumuna geçişte zamanı kaydet
            if new_state == SystemState.RECONNECTING:
                self._reconnecting_start_time = time.time()
            
            log_system(f"Sistem durumu değişti: {old_state.value} -> {new_state.value} ({reason})")
            return True
    
    def _is_valid_state_transition(self, from_state: SystemState, to_state: SystemState) -> bool:
        """Durum geçişinin geçerli olup olmadığını kontrol et"""
        # NORMAL'den her duruma geçilebilir
        if from_state == SystemState.NORMAL:
            return True
        
        # EMERGENCY'den sadece NORMAL'e geçilebilir
        if from_state == SystemState.EMERGENCY:
            return to_state == SystemState.NORMAL
        
        # USB_RESETTING'den RECONNECTING veya NORMAL'e geçilebilir
        if from_state == SystemState.USB_RESETTING:
            return to_state in [SystemState.RECONNECTING, SystemState.NORMAL, SystemState.EMERGENCY]
        
        # RECONNECTING'den NORMAL, USB_RESETTING veya EMERGENCY'a geçilebilir
        if from_state == SystemState.RECONNECTING:
            return to_state in [SystemState.NORMAL, SystemState.USB_RESETTING, SystemState.EMERGENCY]
        
        # POWER_RECOVERY'den NORMAL'e geçilebilir
        if from_state == SystemState.POWER_RECOVERY:
            return to_state in [SystemState.NORMAL, SystemState.EMERGENCY]
        
        return False
    
    def is_system_busy(self) -> bool:
        """Sistem meşgul mu? (Reset veya reconnection devam ediyor)"""
        with self._state_lock:
            return self._system_state in [
                SystemState.USB_RESETTING, 
                SystemState.RECONNECTING, 
                SystemState.POWER_RECOVERY
            ]
    
    # ============ KART DURUMU YÖNETİMİ ============
    
    def get_card_state(self, card_name: str) -> CardState:
        """Kart durumunu al"""
        with self._card_lock:
            return self._card_states.get(card_name, CardState.DISCONNECTED)
    
    def set_card_state(self, card_name: str, new_state: CardState, reason: str = "") -> bool:
        """
        Kart durumunu değiştir
        
        Args:
            card_name: Kart adı (motor, sensor, etc.)
            new_state: Yeni durum
            reason: Değişiklik nedeni
            
        Returns:
            bool: Değişiklik başarılı mı?
        """
        with self._card_lock:
            old_state = self._card_states.get(card_name, CardState.DISCONNECTED)
            self._card_states[card_name] = new_state
            
            if old_state != new_state:
                log_system(f"Kart durumu değişti [{card_name}]: {old_state.value} -> {new_state.value} ({reason})")
            
            return True
    
    def get_all_card_states(self) -> Dict[str, CardState]:
        """Tüm kart durumlarını al"""
        with self._card_lock:
            return self._card_states.copy()
    
    def are_critical_cards_connected(self, critical_cards: Set[str]) -> bool:
        """Kritik kartlar bağlı mı?"""
        with self._card_lock:
            for card in critical_cards:
                if self._card_states.get(card, CardState.DISCONNECTED) != CardState.CONNECTED:
                    return False
            return True
    
    # ============ RESET OPERASYON YÖNETİMİ ============
    
    def can_start_reset(self) -> bool:
        """Reset başlatılabilir mi?"""
        with self._reset_lock:
            # Zaten reset devam ediyorsa hayır
            if self._reset_in_progress:
                return False
            
            # Cooldown durumundaysa hayır
            if self._reset_cooldown:
                return False
            
            return True
    
    def start_reset_operation(self, cards: Set[str], initiated_by: str) -> Optional[str]:
        """
        Reset operasyonu başlat
        
        Args:
            cards: Reset edilecek kartlar
            initiated_by: Kim başlattı
            
        Returns:
            Optional[str]: Operation ID veya None (başlatılamazsa)
        """
        if not self.can_start_reset():
            return None
        
        with self._reset_lock:
            # Reset bayrağını set et
            self._reset_in_progress = True
            
            # Sistem durumunu değiştir
            if not self.set_system_state(SystemState.USB_RESETTING, f"Reset başlatıldı: {initiated_by}"):
                self._reset_in_progress = False
                return None
            
            # Reset operasyonu oluştur
            operation_id = f"reset_{int(time.time())}"
            self._active_reset = ResetOperation(
                operation_id=operation_id,
                start_time=time.time(),
                timeout=0,  # Timeout kaldırıldı
                cards_involved=cards.copy(),
                initiated_by=initiated_by
            )
            
            # Kartları reconnecting durumuna al
            for card in cards:
                self.set_card_state(card, CardState.RECONNECTING, "Reset başlatıldı")
            
            log_system(f"Reset operasyonu başlatıldı: {operation_id} ({initiated_by})")
            return operation_id
    
    def finish_reset_operation(self, operation_id: str, success: bool) -> bool:
        """
        Reset operasyonunu bitir
        
        Args:
            operation_id: Operasyon ID
            success: Başarılı mı?
            
        Returns:
            bool: İşlem başarılı mı?
        """
        with self._reset_lock:
            if self._active_reset is None or self._active_reset.operation_id != operation_id:
                log_warning(f"Geçersiz reset operasyonu: {operation_id}")
                return False
            
            # Reset bayrağını temizle
            self._reset_in_progress = False
            
            # Başarısızsa cooldown aktif et
            if not success:
                self._reset_cooldown = True
                log_system("Reset başarısız - cooldown aktif edildi")
            
            # Operasyonu temizle
            cards = self._active_reset.cards_involved.copy()
            self._active_reset = None
            
            # Sistem durumunu değiştir
            if success:
                self.set_system_state(SystemState.RECONNECTING, "Reset başarılı")
            else:
                self.set_system_state(SystemState.NORMAL, "Reset başarısız")
                # Kartları error durumuna al
                for card in cards:
                    self.set_card_state(card, CardState.ERROR, "Reset başarısız")
            
            log_system(f"Reset operasyonu bitti: {operation_id} ({'başarılı' if success else 'başarısız'})")
            return True
    
    def get_active_reset(self) -> Optional[ResetOperation]:
        """Aktif reset operasyonunu al"""
        with self._reset_lock:
            return self._active_reset
    
    def set_reset_cooldown(self, enabled: bool) -> None:
        """Reset cooldown durumunu ayarla"""
        with self._reset_lock:
            self._reset_cooldown = enabled
            if enabled:
                log_system("Reset cooldown aktif edildi")
            else:
                log_system("Reset cooldown deaktif edildi")
    
    def is_reset_cooldown_active(self) -> bool:
        """Reset cooldown aktif mi?"""
        with self._reset_lock:
            return self._reset_cooldown
    
    # ============ RECONNECTION YÖNETİMİ ============
    
    def can_start_reconnection(self, card_name: str) -> bool:
        """Kart için reconnection başlatılabilir mi?"""
        # Sistem meşgulse hayır (sadece USB_RESETTING durumunda)
        if self._system_state == SystemState.USB_RESETTING:
            return False
        
        with self._reconnect_lock:
            # Zaten reconnecting'se hayır (ama I/O Error durumunda zorla başlat)
            if card_name in self._reconnecting_cards:
                return False
            
            return True
    
    def start_reconnection(self, card_name: str, reason: str = "") -> bool:
        """
        Kart reconnection başlat
        
        Args:
            card_name: Kart adı
            reason: Reconnection nedeni
            
        Returns:
            bool: Başlatıldı mı?
        """
        if not self.can_start_reconnection(card_name):
            return False
        
        with self._reconnect_lock:
            self._reconnecting_cards.add(card_name)
            self._reconnection_start_times[card_name] = time.time()  # ✅ Başlangıç zamanı kaydet
            self.set_card_state(card_name, CardState.RECONNECTING, reason)
            
            log_system(f"Reconnection başlatıldı [{card_name}]: {reason}")
            return True
    
    def finish_reconnection(self, card_name: str, success: bool) -> bool:
        """
        Kart reconnection bitir
        
        Args:
            card_name: Kart adı
            success: Başarılı mı?
            
        Returns:
            bool: İşlem başarılı mı?
        """
        with self._reconnect_lock:
            if card_name not in self._reconnecting_cards:
                return False
            
            self._reconnecting_cards.remove(card_name)
            
            # ✅ Başlangıç zamanını temizle
            if card_name in self._reconnection_start_times:
                duration = time.time() - self._reconnection_start_times[card_name]
                del self._reconnection_start_times[card_name]
                log_system(f"Reconnection süresi [{card_name}]: {duration:.1f}s")
            
            if success:
                self.set_card_state(card_name, CardState.CONNECTED, "Reconnection başarılı")

                # ✅ UYARI KAPATMA: Başarılı reconnection sonrası
                # Eğer BAŞKA HİÇBİR kart reconnecting değilse uyarı kapat
                if not self._reconnecting_cards:  # Artık hiçbir kart reconnecting değil
                    try:
                        uyari.uyari_kapat()
                        log_system(f"{card_name.upper()} reconnection sonrası uyarı kapatıldı (tüm kartlar bağlandı)")
                    except Exception as e:
                        log_error(f"Uyarı kapatma hatası: {e}")
            else:
                self.set_card_state(card_name, CardState.ERROR, "Reconnection başarısız")

            log_system(f"Reconnection bitti [{card_name}]: {'başarılı' if success else 'başarısız'}")
            return True
    
    def is_card_reconnecting(self, card_name: str) -> bool:
        """Kart reconnecting durumunda mı?"""
        with self._reconnect_lock:
            return card_name in self._reconnecting_cards
    
    def get_reconnection_duration(self, card_name: str) -> float:
        """
        Reconnection ne kadar süredir devam ediyor?
        
        Args:
            card_name: Kart adı
            
        Returns:
            float: Süre (saniye), reconnection yoksa 0.0
        """
        with self._reconnect_lock:
            if card_name not in self._reconnecting_cards:
                return 0.0
            
            start_time = self._reconnection_start_times.get(card_name, time.time())
            return time.time() - start_time
    
    def is_reconnection_stuck(self) -> bool:
        """RECONNECTING durumu takıldı mı?"""
        with self._state_lock:
            if self._system_state != SystemState.RECONNECTING:
                return False
            
            # Reconnecting kartlar var ama hiçbiri başarılı olmamışsa takılmış
            with self._reconnect_lock:
                return len(self._reconnecting_cards) > 0
    
    # ============ THREAD YÖNETİMİ ============
    
    def register_thread(self, thread_name: str, thread: threading.Thread) -> bool:
        """Thread kaydet"""
        with self._thread_lock:
            if thread_name in self._active_threads:
                old_thread = self._active_threads[thread_name]
                if old_thread.is_alive():
                    log_warning(f"Thread zaten aktif: {thread_name}")
                    return False
            
            self._active_threads[thread_name] = thread
            log_system(f"Thread kaydedildi: {thread_name}")
            return True
    
    def unregister_thread(self, thread_name: str) -> bool:
        """Thread kaydını sil"""
        with self._thread_lock:
            if thread_name in self._active_threads:
                del self._active_threads[thread_name]
                log_system(f"Thread kaydı silindi: {thread_name}")
                return True
            return False
    
    def get_active_threads(self) -> Dict[str, threading.Thread]:
        """Aktif thread'leri al"""
        with self._thread_lock:
            return {name: thread for name, thread in self._active_threads.items() if thread.is_alive()}
    
    def cleanup_dead_threads(self) -> int:
        """Ölü thread'leri temizle"""
        with self._thread_lock:
            dead_threads = [name for name, thread in self._active_threads.items() if not thread.is_alive()]
            for name in dead_threads:
                del self._active_threads[name]
            
            if dead_threads:
                log_system(f"Ölü thread'ler temizlendi: {dead_threads}")
            
            return len(dead_threads)
    
    # ============ UTILITY METODLAR ============
    
    def emergency_stop(self, reason: str = "Manuel durdurma") -> bool:
        """Acil durdurma - tüm işlemleri durdur"""
        log_warning(f"ACİL DURDURMA: {reason}")
        
        with self._state_lock, self._reset_lock, self._reconnect_lock:
            # Sistem durumunu emergency yap
            self._system_state = SystemState.EMERGENCY
            
            # Aktif reset'i iptal et
            if self._active_reset:
                log_warning(f"Reset operasyonu iptal edildi: {self._active_reset.operation_id}")
                self._active_reset = None
            
            # Reconnection'ları temizle
            if self._reconnecting_cards:
                log_warning(f"Reconnection'lar iptal edildi: {self._reconnecting_cards}")
                self._reconnecting_cards.clear()
            
            # Tüm kartları error durumuna al
            for card_name in self._card_states:
                self._card_states[card_name] = CardState.ERROR
            
            return True
    
    def reset_to_normal(self) -> bool:
        """Sistemi normal duruma döndür"""
        with self._state_lock, self._reset_lock, self._reconnect_lock:
            self._system_state = SystemState.NORMAL
            self._active_reset = None
            self._reconnecting_cards.clear()
            
            # Thread'leri temizle
            self.cleanup_dead_threads()
            
            # Bayrakları temizle
            self._reset_in_progress = False
            self._reset_cooldown = False
            
            log_success("Sistem normal duruma döndürüldü")
            return True
    
    def get_status_summary(self) -> Dict:
        """Sistem durumu özeti"""
        with self._state_lock, self._card_lock, self._reset_lock, self._reconnect_lock:
            return {
                "system_state": self._system_state.value,
                "card_states": {name: state.value for name, state in self._card_states.items()},
                "active_reset": self._active_reset.operation_id if self._active_reset else None,
                "reconnecting_cards": list(self._reconnecting_cards),
                "active_threads": list(self.get_active_threads().keys()),
                "reset_in_progress": self._reset_in_progress,
                "reset_cooldown": self._reset_cooldown,
                "system_busy": self.is_system_busy()
            }

    # ============ PORT SAHİPLİĞİ YÖNETİMİ ============

    def claim_port(self, port: str, card_name: str) -> bool:
        """
        Port sahipliğini talep et

        Args:
            port: Port path (örn. /dev/ttyUSB0)
            card_name: Kart adı (motor, sensor)

        Returns:
            bool: Başarılı mı?
        """
        with self._port_lock:
            # Port zaten sahipli mi?
            if port in self._owned_ports:
                owner, timestamp = self._owned_ports[port]
                # Aynı kart tekrar claim ediyorsa izin ver
                if owner == card_name:
                    log_system(f"Port zaten sahipli [{card_name}]: {port}")
                    return True
                else:
                    log_warning(f"Port başka kart tarafından kullanılıyor [{owner}]: {port} (talep: {card_name})")
                    return False

            # Port'u claim et
            self._owned_ports[port] = (card_name, time.time())
            log_system(f"✅ Port claim edildi [{card_name}]: {port}")
            return True

    def release_port(self, port: str, card_name: str) -> bool:
        """
        Port sahipliğini bırak

        Args:
            port: Port path
            card_name: Kart adı

        Returns:
            bool: Başarılı mı?
        """
        with self._port_lock:
            if port not in self._owned_ports:
                log_system(f"Port zaten serbest: {port}")
                return True

            owner, _ = self._owned_ports[port]
            if owner != card_name:
                log_warning(f"Port başka kart tarafından sahiplenmiş [{owner}]: {port} (release isteği: {card_name})")
                return False

            del self._owned_ports[port]
            log_system(f"✅ Port release edildi [{card_name}]: {port}")
            return True

    def get_port_owner(self, port: str) -> Optional[str]:
        """
        Port sahibini döndür

        Args:
            port: Port path

        Returns:
            Optional[str]: Sahip kart adı veya None
        """
        with self._port_lock:
            if port in self._owned_ports:
                return self._owned_ports[port][0]
            return None

    def is_port_owned(self, port: str) -> bool:
        """
        Port sahipli mi?

        Args:
            port: Port path

        Returns:
            bool: Sahipli mi?
        """
        with self._port_lock:
            return port in self._owned_ports

    def get_owned_port(self, card_name: str) -> Optional[str]:
        """
        Kartın sahip olduğu portu döndür

        Args:
            card_name: Kart adı

        Returns:
            Optional[str]: Port path veya None
        """
        with self._port_lock:
            for port, (owner, _) in self._owned_ports.items():
                if owner == card_name:
                    return port
            return None

    def force_release_port(self, port: str, reason: str = "") -> bool:
        """
        Port sahipliğini ZORLA bırak (acil durum için)

        Args:
            port: Port path
            reason: Release nedeni

        Returns:
            bool: Başarılı mı?
        """
        with self._port_lock:
            if port in self._owned_ports:
                owner, _ = self._owned_ports[port]
                del self._owned_ports[port]
                log_warning(f"⚠️ Port ZORLA release edildi [{owner}]: {port} ({reason})")
                return True
            return False

    def get_all_owned_ports(self) -> Dict[str, str]:
        """
        Tüm sahiplenmiş portları döndür

        Returns:
            Dict[str, str]: {port: card_name}
        """
        with self._port_lock:
            return {port: owner for port, (owner, _) in self._owned_ports.items()}

    # ============ USB DEVICE BASELINE MANAGEMENT ============

    def update_usb_baseline(self):
        """
        USB cihaz baseline'ını güncelle (Touchscreen & Camera)

        Bu metod agresif reset tamamlandıktan SONRA çağrılır.
        Mevcut USB device numaralarını alır ve baseline olarak kaydeder.
        USB health monitor bu baseline'a bakarak reconnect tespit eder.

        İzlenen cihazlar:
        - Touchscreen: 2575:0001 (CoolTouch® System)
        - Camera: 2bdf:0001 (Hikrobot MV-CS004-10UC)
        """
        import subprocess

        with self._usb_baseline_lock:
            try:
                # lsusb çalıştır
                result = subprocess.run(
                    ["lsusb"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode != 0:
                    log_error("USB baseline güncelleme başarısız - lsusb çalışmadı")
                    return

                # Parse et
                touchscreen_num = None
                camera_num = None

                for line in result.stdout.strip().split('\n'):
                    # Örnek: Bus 003 Device 075: ID 2575:0001 Weida Hi-Tech Co., Ltd. CoolTouch® System
                    if "2575:0001" in line:  # Touchscreen
                        # Device numarasını parse et
                        parts = line.split()
                        if len(parts) >= 4 and parts[1] == "Bus" and parts[3] == "Device":
                            device_str = parts[4].rstrip(':')  # "075:"
                            touchscreen_num = device_str

                    elif "2bdf:0001" in line:  # Camera
                        parts = line.split()
                        if len(parts) >= 4 and parts[1] == "Bus" and parts[3] == "Device":
                            device_str = parts[4].rstrip(':')
                            camera_num = device_str

                # Baseline'ı güncelle
                old_touchscreen = self.touchscreen_device_num
                old_camera = self.camera_device_num

                self.touchscreen_device_num = touchscreen_num
                self.camera_device_num = camera_num

                # Log
                if touchscreen_num:
                    if old_touchscreen != touchscreen_num:
                        log_system(f"🔍 [USB-BASELINE] Touchscreen baseline güncellendi: {old_touchscreen} → {touchscreen_num}")
                    else:
                        log_system(f"🔍 [USB-BASELINE] Touchscreen baseline: {touchscreen_num}")
                else:
                    log_warning("🔍 [USB-BASELINE] Touchscreen bulunamadı")

                if camera_num:
                    if old_camera != camera_num:
                        log_system(f"🔍 [USB-BASELINE] Camera baseline güncellendi: {old_camera} → {camera_num}")
                    else:
                        log_system(f"🔍 [USB-BASELINE] Camera baseline: {camera_num}")
                else:
                    log_warning("🔍 [USB-BASELINE] Camera bulunamadı")

            except subprocess.TimeoutExpired:
                log_error("USB baseline güncelleme timeout")
            except Exception as e:
                log_error(f"USB baseline güncelleme hatası: {e}")

    def get_usb_baseline(self) -> tuple[Optional[str], Optional[str]]:
        """
        Mevcut USB baseline'ı döndür

        Returns:
            tuple: (touchscreen_device_num, camera_device_num)
        """
        with self._usb_baseline_lock:
            return (self.touchscreen_device_num, self.camera_device_num)


# Global instance
system_state = SystemStateManager()
