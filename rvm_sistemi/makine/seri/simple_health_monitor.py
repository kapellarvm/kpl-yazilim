"""
simple_health_monitor.py - Basit Sağlık İzleme
Sadece periyodik ping atar, state machine recovery'yi halleder
"""

import threading
import time
from typing import Dict

from rvm_sistemi.makine.seri.base_card import BaseCard
from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning


class SimpleHealthMonitor:
    """
    Basit sağlık izleme servisi

    - Periyodik ping
    - Oturum kontrolü
    - O kadar! State machine kendi recovery'sini yapar.
    """

    def __init__(self, cards: Dict[str, BaseCard]):
        """
        Initialize health monitor

        Args:
            cards: Kartlar {"motor": motor_card, "sensor": sensor_card}
        """
        self.cards = cards

        # Monitoring thread
        self._running = False
        self._monitor_thread: threading.Thread = None

        # Oturum kontrolü
        self._session_active = False

        # Ping interval
        self.ping_interval = 5  # saniye

        log_system("SimpleHealthMonitor initialized")

    def start(self) -> None:
        """Start health monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="health_monitor"
        )
        self._monitor_thread.start()

        log_success("Health monitoring started")

    def stop(self) -> None:
        """Stop health monitoring"""
        self._running = False

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

        log_system("Health monitoring stopped")

    def set_session_active(self, active: bool) -> None:
        """
        Set session status

        Args:
            active: Session aktif mi?
        """
        self._session_active = active

        if active:
            log_system("Session active - health monitoring paused")
        else:
            log_system("Session inactive - health monitoring resumed")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        log_system("Health monitor loop started")

        while self._running:
            try:
                # Oturum aktifse atla
                if self._session_active:
                    time.sleep(1)
                    continue

                # Her kartı ping'le
                for card_name, card in self.cards.items():
                    self._check_card(card_name, card)

                # Bekleme
                time.sleep(self.ping_interval)

            except Exception as e:
                log_error(f"Health monitor error: {e}")
                time.sleep(1)

        log_system("Health monitor loop stopped")

    def _check_card(self, card_name: str, card: BaseCard) -> None:
        """
        Check single card health

        Args:
            card_name: Kart adı
            card: Kart instance
        """
        # Sadece READY durumundaysa ping at
        if not card.is_ready():
            return

        # Ping gönder
        success = card.ping()

        if success:
            log_system(f"[{card_name}] Health check OK")
        else:
            log_warning(f"[{card_name}] Health check FAILED")
            # BaseCard kendi recovery'sini tetikleyecek (3 başarısız ping sonrası)
