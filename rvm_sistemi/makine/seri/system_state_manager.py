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
        self._reconnect_lock = threading.RLock()
        
        # Timing kontrolü
        self._last_reset_time = 0
        self._min_reset_interval = 30  # Minimum 30 saniye aralık
        
        # Thread takibi
        self._active_threads: Dict[str, threading.Thread] = {}
        self._thread_lock = threading.RLock()
        
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
            if self._active_reset is not None:
                return False
            
            # Minimum süre geçmemişse hayır
            current_time = time.time()
            if current_time - self._last_reset_time < self._min_reset_interval:
                remaining = self._min_reset_interval - (current_time - self._last_reset_time)
                log_warning(f"Reset çok erken, {remaining:.1f} saniye bekleyin")
                return False
            
            return True
    
    def start_reset_operation(self, cards: Set[str], initiated_by: str, timeout: float = 60) -> Optional[str]:
        """
        Reset operasyonu başlat
        
        Args:
            cards: Reset edilecek kartlar
            initiated_by: Kim başlattı
            timeout: Timeout süresi
            
        Returns:
            Optional[str]: Operation ID veya None (başlatılamazsa)
        """
        if not self.can_start_reset():
            return None
        
        with self._reset_lock:
            # Sistem durumunu değiştir
            if not self.set_system_state(SystemState.USB_RESETTING, f"Reset başlatıldı: {initiated_by}"):
                return None
            
            # Reset operasyonu oluştur
            operation_id = f"reset_{int(time.time())}"
            self._active_reset = ResetOperation(
                operation_id=operation_id,
                start_time=time.time(),
                timeout=timeout,
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
            
            # Zamanı kaydet
            self._last_reset_time = time.time()
            
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
    
    def is_reset_timeout(self) -> bool:
        """Reset timeout oldu mu?"""
        with self._reset_lock:
            if self._active_reset is None:
                return False
            
            elapsed = time.time() - self._active_reset.start_time
            return elapsed > self._active_reset.timeout
    
    # ============ RECONNECTION YÖNETİMİ ============
    
    def can_start_reconnection(self, card_name: str) -> bool:
        """Kart için reconnection başlatılabilir mi?"""
        # Sistem meşgulse hayır
        if self.is_system_busy():
            return False
        
        with self._reconnect_lock:
            # Zaten reconnecting'se hayır
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
            
            if success:
                self.set_card_state(card_name, CardState.CONNECTED, "Reconnection başarılı")
            else:
                self.set_card_state(card_name, CardState.ERROR, "Reconnection başarısız")
            
            log_system(f"Reconnection bitti [{card_name}]: {'başarılı' if success else 'başarısız'}")
            return True
    
    def is_card_reconnecting(self, card_name: str) -> bool:
        """Kart reconnecting durumunda mı?"""
        with self._reconnect_lock:
            return card_name in self._reconnecting_cards
    
    def is_reconnection_timeout(self, timeout_seconds: float = 30.0) -> bool:
        """RECONNECTING durumu timeout oldu mu?"""
        with self._state_lock:
            if self._system_state != SystemState.RECONNECTING:
                return False
            
            # RECONNECTING durumunda 30 saniyeden fazla devam ediyorsa timeout
            if hasattr(self, '_reconnecting_start_time'):
                elapsed = time.time() - self._reconnecting_start_time
                return elapsed > timeout_seconds
            
            return False
    
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
                "last_reset_time": self._last_reset_time,
                "system_busy": self.is_system_busy()
            }


# Global instance
system_state = SystemStateManager()
