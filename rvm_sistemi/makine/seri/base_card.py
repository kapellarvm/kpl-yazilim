"""
base_card.py - State-Driven Serial Card Communication
Tüm kartlar için temel state machine ve event-driven haberleşme
"""

import threading
import queue
import time
import serial
from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict
from dataclasses import dataclass

from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning


# ============ STATE DEFINITIONS ============

class CardState(Enum):
    """Kart durumları - Her state bir aşamayı temsil eder"""
    DISCONNECTED = "disconnected"      # Port yok
    CONNECTING = "connecting"          # Port açıldı, boot bekleniyor
    CONNECTED = "connected"            # Boot tamamlandı
    READY = "ready"                    # İlk PONG alındı, hazır
    ERROR = "error"                    # Hata durumu


class CardEvent(Enum):
    """Kart eventleri - State transition'ları tetikler"""
    PORT_OPENED = "port_opened"
    BOOT_MESSAGE = "boot_message"      # "resetlendi"
    DEVICE_IDENTIFIED = "device_identified"  # "motor" veya "sensor"
    CALIBRATION_DONE = "calibration_done"
    PONG_RECEIVED = "pong_received"
    IO_ERROR = "io_error"
    PING_FAILED = "ping_failed"
    RECOVERY_STARTED = "recovery_started"


@dataclass
class Message:
    """Serial'den gelen mesaj"""
    data: str
    timestamp: float


# ============ BASE CARD CLASS ============

class BaseCard(ABC):
    """
    Abstract base class for all serial cards

    State Machine:
        DISCONNECTED → CONNECTING → CONNECTED → READY
                ↓           ↓           ↓           ↓
               ERROR ←────────────────────────────┘
                ↓ (auto recovery)
            DISCONNECTED
    """

    def __init__(self, port: Optional[str], callback: Optional[Callable], device_name: str):
        """
        Base card initialization

        Args:
            port: Serial port path
            callback: Callback for application messages
            device_name: Device identifier (motor/sensor)
        """
        self.port = port
        self.callback = callback
        self.device_name = device_name

        # State machine
        self._state = CardState.DISCONNECTED
        self._state_lock = threading.RLock()

        # Event queue
        self._event_queue = queue.Queue()

        # Serial communication
        self._serial: Optional[serial.Serial] = None
        self._serial_lock = threading.RLock()

        # Command queue (write)
        self._write_queue = queue.Queue(maxsize=100)

        # Worker thread
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Health tracking
        self._last_pong_time = 0
        self._consecutive_ping_failures = 0

        log_system(f"[{self.device_name}] BaseCard initialized")

    # ============ PUBLIC API ============

    def start(self) -> bool:
        """
        Start the card communication

        Returns:
            bool: Started successfully
        """
        if self._running:
            log_warning(f"[{self.device_name}] Already running")
            return False

        if not self.port:
            log_error(f"[{self.device_name}] No port specified")
            return False

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.device_name}_worker"
        )
        self._worker_thread.start()

        # Trigger port connection
        self._event_queue.put(CardEvent.PORT_OPENED)

        log_success(f"[{self.device_name}] Started")
        return True

    def stop(self) -> None:
        """Stop the card communication"""
        self._running = False

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)

        with self._serial_lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
                self._serial = None

        log_system(f"[{self.device_name}] Stopped")

    def ping(self) -> bool:
        """
        Ping the card

        Returns:
            bool: PONG received
        """
        if self._state not in [CardState.READY, CardState.CONNECTED]:
            log_warning(f"[{self.device_name}] Cannot ping - state: {self._state.value}")
            return False

        # Send ping
        self._write_queue.put(b'ping\n')

        # Wait for pong (with timeout)
        start_time = time.time()
        timeout = 0.5

        while time.time() - start_time < timeout:
            if time.time() - self._last_pong_time < 0.1:  # Recent pong
                log_success(f"[{self.device_name}] PONG received")
                self._consecutive_ping_failures = 0
                return True
            time.sleep(0.01)

        # Ping failed
        self._consecutive_ping_failures += 1
        log_error(f"[{self.device_name}] PING failed ({self._consecutive_ping_failures})")

        if self._consecutive_ping_failures >= 3:
            self._event_queue.put(CardEvent.PING_FAILED)

        return False

    def reset(self) -> bool:
        """
        Reset the card

        Returns:
            bool: Command sent
        """
        if self._state == CardState.DISCONNECTED:
            log_warning(f"[{self.device_name}] Cannot reset - disconnected")
            return False

        self._write_queue.put(b'reset\n')
        log_system(f"[{self.device_name}] Reset command sent")

        # Transition to CONNECTING (wait for boot message)
        self._transition_to(CardState.CONNECTING)

        return True

    def get_state(self) -> CardState:
        """Get current state"""
        with self._state_lock:
            return self._state

    def is_ready(self) -> bool:
        """Check if card is ready"""
        return self._state == CardState.READY

    # ============ ABSTRACT METHODS ============

    @abstractmethod
    def _get_expected_boot_messages(self) -> list:
        """Return expected boot messages (e.g., ['ykt', 'skt'])"""
        pass

    @abstractmethod
    def _send_initial_config(self) -> None:
        """Send initial configuration after boot"""
        pass

    @abstractmethod
    def _process_application_message(self, msg: str) -> None:
        """Process application-specific messages"""
        pass

    # ============ INTERNAL STATE MACHINE ============

    def _transition_to(self, new_state: CardState) -> None:
        """
        Transition to a new state

        Args:
            new_state: Target state
        """
        with self._state_lock:
            old_state = self._state

            if old_state == new_state:
                return

            self._state = new_state
            log_system(f"[{self.device_name}] State: {old_state.value} → {new_state.value}")

    def _worker_loop(self) -> None:
        """
        Main worker thread - Single thread for all operations
        """
        log_system(f"[{self.device_name}] Worker thread started")

        while self._running:
            try:
                # 1. Process events (state transitions)
                self._process_events()

                # 2. Read from serial
                self._read_serial()

                # 3. Write to serial
                self._write_serial()

                # 4. Process current state
                self._process_current_state()

                # Sleep to prevent busy loop
                time.sleep(0.01)

            except Exception as e:
                log_error(f"[{self.device_name}] Worker loop error: {e}")
                time.sleep(0.1)

        log_system(f"[{self.device_name}] Worker thread stopped")

    def _process_events(self) -> None:
        """Process event queue"""
        try:
            while not self._event_queue.empty():
                event = self._event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass

    def _handle_event(self, event: CardEvent) -> None:
        """
        Handle a single event

        Args:
            event: Event to handle
        """
        if event == CardEvent.PORT_OPENED:
            self._on_port_opened()

        elif event == CardEvent.BOOT_MESSAGE:
            self._on_boot_message()

        elif event == CardEvent.CALIBRATION_DONE:
            self._on_calibration_done()

        elif event == CardEvent.PONG_RECEIVED:
            self._on_pong_received()

        elif event == CardEvent.IO_ERROR:
            self._on_io_error()

        elif event == CardEvent.PING_FAILED:
            self._on_ping_failed()

        elif event == CardEvent.RECOVERY_STARTED:
            self._on_recovery_started()

    def _on_port_opened(self) -> None:
        """Handle PORT_OPENED event"""
        if not self._open_serial_port():
            log_error(f"[{self.device_name}] Failed to open port: {self.port}")
            self._transition_to(CardState.ERROR)
            self._schedule_recovery()
            return

        self._transition_to(CardState.CONNECTING)

    def _on_boot_message(self) -> None:
        """Handle BOOT_MESSAGE event"""
        if self._state != CardState.CONNECTING:
            return

        # Send identification command
        self._write_queue.put(b's\n')
        time.sleep(0.1)

        # Send boot confirmation
        self._write_queue.put(b'b\n')
        log_system(f"[{self.device_name}] Boot sequence initiated")

    def _on_calibration_done(self) -> None:
        """Handle CALIBRATION_DONE event"""
        if self._state != CardState.CONNECTING:
            return

        log_success(f"[{self.device_name}] Calibration complete")
        self._transition_to(CardState.CONNECTED)

        # Send initial configuration
        self._send_initial_config()

        # Send first ping to transition to READY
        self._write_queue.put(b'ping\n')

    def _on_pong_received(self) -> None:
        """Handle PONG_RECEIVED event"""
        self._last_pong_time = time.time()
        self._consecutive_ping_failures = 0

        if self._state == CardState.CONNECTED:
            # First pong after boot
            self._transition_to(CardState.READY)
            log_success(f"[{self.device_name}] Ready!")

    def _on_io_error(self) -> None:
        """Handle IO_ERROR event"""
        log_error(f"[{self.device_name}] I/O Error detected")
        self._transition_to(CardState.ERROR)
        self._close_serial_port()
        self._schedule_recovery()

    def _on_ping_failed(self) -> None:
        """Handle PING_FAILED event"""
        log_error(f"[{self.device_name}] Multiple ping failures")
        self._transition_to(CardState.ERROR)
        self._close_serial_port()
        self._schedule_recovery()

    def _on_recovery_started(self) -> None:
        """Handle RECOVERY_STARTED event"""
        log_system(f"[{self.device_name}] Recovery started")
        self._transition_to(CardState.DISCONNECTED)
        self._consecutive_ping_failures = 0

        # Wait before retry
        time.sleep(2)

        # Retry connection
        self._event_queue.put(CardEvent.PORT_OPENED)

    def _process_current_state(self) -> None:
        """Process actions based on current state"""
        state = self._state

        if state == CardState.CONNECTING:
            # Check for boot completion (calibration messages)
            # This is handled in _process_incoming_message
            pass

        elif state == CardState.CONNECTED:
            # Waiting for first pong
            pass

        elif state == CardState.READY:
            # Normal operation
            pass

        elif state == CardState.ERROR:
            # Recovery will be triggered by event
            pass

    def _schedule_recovery(self) -> None:
        """Schedule automatic recovery"""
        def recovery_worker():
            time.sleep(3)  # Wait before recovery
            if self._state == CardState.ERROR:
                self._event_queue.put(CardEvent.RECOVERY_STARTED)

        threading.Thread(target=recovery_worker, daemon=True).start()

    # ============ SERIAL COMMUNICATION ============

    def _open_serial_port(self) -> bool:
        """
        Open serial port

        Returns:
            bool: Success
        """
        try:
            with self._serial_lock:
                if self._serial and self._serial.is_open:
                    return True

                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=115200,
                    timeout=0.1,
                    write_timeout=0.5
                )

                log_success(f"[{self.device_name}] Port opened: {self.port}")
                return True

        except (serial.SerialException, OSError) as e:
            log_error(f"[{self.device_name}] Port open error: {e}")
            return False

    def _close_serial_port(self) -> None:
        """Close serial port"""
        with self._serial_lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None
                log_system(f"[{self.device_name}] Port closed")

    def _read_serial(self) -> None:
        """Read from serial port"""
        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                return

            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        self._process_incoming_message(data)

            except (serial.SerialException, OSError) as e:
                log_error(f"[{self.device_name}] Read error: {e}")
                self._event_queue.put(CardEvent.IO_ERROR)

    def _write_serial(self) -> None:
        """Write to serial port"""
        try:
            command = self._write_queue.get_nowait()

            with self._serial_lock:
                if not self._serial or not self._serial.is_open:
                    return

                try:
                    self._serial.write(command)
                    self._serial.flush()

                except (serial.SerialException, OSError) as e:
                    log_error(f"[{self.device_name}] Write error: {e}")
                    self._event_queue.put(CardEvent.IO_ERROR)

        except queue.Empty:
            pass

    def _process_incoming_message(self, msg: str) -> None:
        """
        Process incoming serial message

        Args:
            msg: Message string
        """
        msg_lower = msg.lower()

        # Protocol messages
        if msg_lower == "resetlendi":
            log_system(f"[{self.device_name}] Boot message received")
            self._event_queue.put(CardEvent.BOOT_MESSAGE)

        elif msg_lower == "pong":
            self._event_queue.put(CardEvent.PONG_RECEIVED)

        elif msg_lower in self._get_expected_boot_messages():
            # Check if all boot messages received
            log_system(f"[{self.device_name}] Boot message: {msg}")
            # Simplified: assume calibration done after any boot message
            self._event_queue.put(CardEvent.CALIBRATION_DONE)

        else:
            # Application message
            self._process_application_message(msg)

    # ============ COMMAND HELPERS ============

    def _send_command(self, cmd: bytes) -> None:
        """
        Send a command to the card

        Args:
            cmd: Command bytes
        """
        if self._state not in [CardState.CONNECTED, CardState.READY]:
            log_warning(f"[{self.device_name}] Cannot send command - state: {self._state.value}")
            return

        try:
            self._write_queue.put(cmd, timeout=0.1)
        except queue.Full:
            log_warning(f"[{self.device_name}] Write queue full, command dropped")
