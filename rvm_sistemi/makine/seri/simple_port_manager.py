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

        # DEBUG: Tüm portları logla
        log_system(f"Sistem portları: {len(ports)} port bulundu")
        for p in ports:
            log_system(f"  - {p.device} | {p.description} | {p.hwid}")

        compatible_ports = [p for p in ports if self._is_compatible_port(p.device)]

        if not compatible_ports:
            log_warning("Hiçbir uyumlu USB port bulunamadı!")
            log_warning("Kontrol edin: USB kabloları bağlı mı?")
            return False, "Uyumlu port bulunamadı", {}

        log_system(f"{len(compatible_ports)} uyumlu port bulundu")

        # Portları tara
        found_cards = {}

        for port_info in compatible_ports:
            port = port_info.device
            log_system(f"Port test ediliyor: {port}")

            # Port'u test et
            device_type = self._identify_device(port)

            if device_type:
                found_cards[device_type] = port
                log_success(f"{device_type.upper()} kartı bulundu: {port}")
            else:
                log_warning(f"{port} - Tanımlanamayan cihaz")

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
                timeout=2,
                write_timeout=2
            )

            log_system(f"  {port} açıldı, cihaz tanımlanıyor...")

            # ESP32 boot bekle (resetlendiyse)
            time.sleep(1.5)

            # Buffer'ı temizle
            ser.reset_input_buffer()

            # Identify komutu gönder (2 kez dene)
            for attempt in range(2):
                ser.write(b's\n')
                ser.flush()
                time.sleep(0.5)

                # Cevabı oku
                if ser.in_waiting > 0:
                    response = ser.readline().decode('utf-8', errors='ignore').strip().lower()
                    log_system(f"  {port} cevap: '{response}'")

                    ser.close()

                    if response == "motor":
                        return "motor"
                    elif response == "sensor":
                        return "sensor"

            log_warning(f"  {port} - Cevap alınamadı")
            ser.close()

        except (serial.SerialException, OSError) as e:
            log_warning(f"  {port} test hatası: {e}")

        return None
