"""
simple_port_manager.py - Basit Port Scanner
Karmaşık USB reset mantığı YOK, sadece port bulma
"""

import serial
import time
from serial.tools import list_ports
from typing import Dict, Optional, Tuple

from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning


class SimplePortManager:
    """
    Basit port yöneticisi

    - Port listeler
    - Kartları identify eder
    - Port döndürür
    - O kadar! USB reset, state management yok.
    """

    def __init__(self):
        """Initialize port manager"""
        self.baudrate = 115200
        log_system("SimplePortManager initialized")

    def find_cards(self) -> Tuple[bool, str, Dict[str, str]]:
        """
        Kartları bul ve port'larını döndür

        Returns:
            Tuple[bool, str, Dict[str, str]]:
                - Başarı durumu
                - Mesaj
                - Bulunan kartlar: {"motor": "/dev/ttyUSB0", "sensor": "/dev/ttyUSB1"}
        """
        log_system("Port taraması başlatılıyor...")

        # Mevcut portları al
        ports = list_ports.comports()
        compatible_ports = [p for p in ports if self._is_compatible_port(p.device)]

        if not compatible_ports:
            return False, "Uyumlu port bulunamadı", {}

        log_system(f"{len(compatible_ports)} uyumlu port bulundu")

        # Portları tara
        found_cards = {}

        for port_info in compatible_ports:
            port = port_info.device

            # Port'u test et
            device_type = self._identify_device(port)

            if device_type:
                found_cards[device_type] = port
                log_success(f"{device_type.upper()} kartı bulundu: {port}")

        if not found_cards:
            return False, "Tanımlı kart bulunamadı", {}

        return True, f"{len(found_cards)} kart bulundu", found_cards

    def _is_compatible_port(self, port_device: str) -> bool:
        """
        Port uyumlu mu?

        Args:
            port_device: Port path

        Returns:
            bool: Uyumlu mu?
        """
        device_lower = port_device.lower()
        return any(keyword in device_lower for keyword in ["usb", "acm", "tty"])

    def _identify_device(self, port: str) -> Optional[str]:
        """
        Porttaki cihazı identify et

        Args:
            port: Port path

        Returns:
            Optional[str]: "motor" veya "sensor", ya da None
        """
        try:
            # Port'u aç
            ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=1
            )

            # Boot message'ı bekle (zaten çalışıyorsa)
            time.sleep(0.5)

            # Buffer'ı temizle
            ser.reset_input_buffer()

            # Identify komutu gönder
            ser.write(b's\n')
            ser.flush()
            time.sleep(0.3)

            # Cevabı oku
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip().lower()

                ser.close()

                if response == "motor":
                    return "motor"
                elif response == "sensor":
                    return "sensor"

            ser.close()

        except (serial.SerialException, OSError) as e:
            log_warning(f"Port test hatası {port}: {e}")

        return None
