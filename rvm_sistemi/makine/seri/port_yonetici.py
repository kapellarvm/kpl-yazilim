"""
Kart Haberleşme Servisi
Arduino tabanlı kartlarla seri port üzerinden haberleşme modülü.
"""

import serial
import time
import platform
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from serial.tools import list_ports

from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning
import subprocess
import os
import glob


# Sabit değerler
class Constants:
    """Sistem sabitleri"""
    DEFAULT_BAUDRATE = 115200
    PORT_TIMEOUT = 2
    RESET_WAIT_TIME = 2.5
    HARDWARE_INIT_TIME = 2.0
    COMMAND_DELAY = 0.3
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0
    CONFIRMATION_TIMEOUT = 0.2
    THREAD_POOL_SIZE = 4


class DeviceType(Enum):
    """Desteklenen cihaz tipleri"""
    SENSOR = "sensor"
    MOTOR = "motor"
    GUVENLIK = "guvenlik"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Geçerli cihaz tipi kontrolü"""
        return value.lower() in [item.value for item in cls]
    
    @classmethod
    def from_string(cls, value: str) -> Optional['DeviceType']:
        """String'den DeviceType oluştur"""
        value_lower = value.lower()
        for device in cls:
            if device.value == value_lower:
                return device
        return None


class Commands(Enum):
    """Sistem komutları"""
    RESET = b'reset\n'
    IDENTIFY = b's\n'
    CONFIRM = b'b\n'


@dataclass
class PortInfo:
    """Port bilgisi veri yapısı"""
    device: str
    device_type: DeviceType
    description: str = ""
    hardware_id: str = ""
    
    def __hash__(self):
        return hash(self.device)


class PortScanner:
    """Port tarama ve filtreleme işlemleri"""
    
    def __init__(self, system: str):
        self.system = system
    
    def get_available_ports(self) -> List[serial.tools.list_ports_common.ListPortInfo]:
        """Mevcut portları listele"""
        return list(list_ports.comports())
    
    def is_compatible_port(self, port_device: str) -> bool:
        """
        Platform bağımsız port uyumluluk kontrolü
        
        Args:
            port_device: Kontrol edilecek port
            
        Returns:
            bool: Port uyumlu mu?
        """
        device_lower = port_device.lower()
        
        if self.system == "Windows":
            return "com" in device_lower
        else:  # Linux, macOS
            return any(keyword in device_lower for keyword in ["usb", "acm", "arduino"])


class SerialConnection:
    """Seri port bağlantı yöneticisi"""
    
    def __init__(self, baudrate: int = Constants.DEFAULT_BAUDRATE):
        self.baudrate = baudrate
        self._lock = threading.Lock()
    
    @contextmanager
    def open_port(self, port_device: str, timeout: float = Constants.PORT_TIMEOUT):
        """
        Context manager ile güvenli port açma
        
        Args:
            port_device: Açılacak port
            timeout: Zaman aşımı süresi
            
        Yields:
            serial.Serial: Açık seri port nesnesi
        """
        ser = None
        try:
            ser = self._try_open_port(port_device, timeout)
            if ser:
                yield ser
            else:
                yield None
        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                    log_system(f"{port_device} portu kapatıldı")
                except Exception as e:
                    log_error(f"Port kapatma hatası: {e}")
    
    def _try_open_port(self, port_device: str, timeout: float, 
                       max_attempts: int = Constants.MAX_RETRY_ATTEMPTS) -> Optional[serial.Serial]:
        """
        Port açmayı dene (retry mekanizması ile)
        
        Args:
            port_device: Açılacak port
            timeout: Zaman aşımı
            max_attempts: Maksimum deneme sayısı
            
        Returns:
            Optional[serial.Serial]: Açık port veya None
        """
        for attempt in range(max_attempts):
            try:
                with self._lock:
                    ser = serial.Serial(
                        port=port_device,
                        baudrate=self.baudrate,
                        timeout=timeout,
                        write_timeout=timeout
                        # exclusive=True kaldırıldı - port çakışmasına neden oluyor
                    )
                    return ser
                    
            except serial.SerialException as e:
                error_str = str(e).lower()
                error_message = str(e)
                
                # Input/output error - genellikle fiziksel bağlantı sorunu
                if "input/output" in error_str or "errno 5" in error_str:
                    log_error(f"{port_device} I/O hatası - cihaz fiziksel olarak kopmuş olabilir: {error_message}")
                    break  # I/O hatası için tekrar deneme
                
                # Permission/busy errors - tekrar denenebilir
                elif any(keyword in error_str for keyword in ["permission", "denied", "busy", "in use"]):
                    if attempt < max_attempts - 1:
                        
                        log_warning(f"{port_device} meşgul, {attempt + 1}/{max_attempts} deneme: {error_message}")
                        time.sleep(Constants.RETRY_DELAY)
                        continue
                    else:
                        log_error(f"{port_device} sürekli meşgul: {error_message}")
                
                # Device not found
                elif "no such file" in error_str or "device not found" in error_str:
                    log_warning(f"{port_device} cihaz bulunamadı: {error_message}")
                    break
                
                # Diğer hatalar
                else:
                    log_error(f"{port_device} açılamadı: {error_message}")
                    if attempt < max_attempts - 1:
                        time.sleep(Constants.RETRY_DELAY)
                        continue
                
                break
            
            except OSError as e:
                # OSError - genellikle sistem seviyesi hatalar
                log_error(f"{port_device} sistem hatası: {e}")
                break
                
            except Exception as e:
                # Beklenmeyen hatalar
                log_error(f"{port_device} beklenmeyen hata: {e}")
                break
        
        return None


class DeviceCommunicator:
    """Cihaz iletişim protokolü yöneticisi"""
    
    @staticmethod
    def reset_device(ser: serial.Serial) -> None:
        """
        Cihazı resetle
        
        Args:
            ser: Seri port nesnesi
        """
        # Buffer'ları temizle
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Reset komutu gönder
        ser.write(Commands.RESET.value)
        ser.flush()
        time.sleep(Constants.RESET_WAIT_TIME)
        # Buffer'ları tekrar temizle
        ser.reset_input_buffer()
    
    @staticmethod
    def identify_device(ser: serial.Serial) -> Optional[DeviceType]:
        """
        Cihaz kimliğini sorgula
        
        Args:
            ser: Seri port nesnesi
            
        Returns:
            Optional[DeviceType]: Cihaz tipi veya None
        """
        # İlk sorgu
        ser.write(Commands.IDENTIFY.value)
        ser.flush()
        time.sleep(Constants.COMMAND_DELAY)
        
        # Cevap kontrolü
        response = None
        if ser.in_waiting > 0:
            response = ser.readline().decode(errors='ignore').strip().lower()
        else:
            # İkinci deneme
            ser.write(Commands.IDENTIFY.value)
            ser.flush()
            time.sleep(Constants.COMMAND_DELAY)
            
            if ser.in_waiting > 0:
                response = ser.readline().decode(errors='ignore').strip().lower()
        
        # Buffer temizle
        if ser.in_waiting > 0:
            ser.reset_input_buffer()
        
        # Cihaz tipini kontrol et
        if response and DeviceType.is_valid(response):
            return DeviceType.from_string(response)
        
        return None
    
    @staticmethod
    def confirm_connection(ser: serial.Serial) -> bool:
        """
        Bağlantıyı onayla
        
        Args:
            ser: Seri port nesnesi
            
        Returns:
            bool: Onay başarılı mı?
        """
        ser.write(Commands.CONFIRM.value)
        ser.flush()
        time.sleep(Constants.CONFIRMATION_TIMEOUT)
        
        # Opsiyonel: Onay cevabını kontrol et
        if ser.in_waiting > 0:
            confirmation = ser.readline().decode(errors='ignore').strip()
            return bool(confirmation)
        
        return True  # Cevap gelmese bile onaylandı say


class KartHaberlesmeServis:
    """
    Ana kart haberleşme servisi
    
    Attributes:
        baudrate: İletişim hızı
        scanner: Port tarayıcı
        connection: Bağlantı yöneticisi
        communicator: İletişim yöneticisi
    """
    
    def __init__(self, baudrate: int = Constants.DEFAULT_BAUDRATE):
        """
        Servis başlatıcı
        
        Args:
            baudrate: Seri port iletişim hızı
        """
        self.baudrate = baudrate
        self.system = platform.system()
        self.scanner = PortScanner(self.system)
        self.connection = SerialConnection(baudrate)
        self.communicator = DeviceCommunicator()
        
        log_system(f"Kart Haberleşme Servisi başlatıldı - Sistem: {self.system}")
    
    def _reset_usb_port(self, port_device: str) -> bool:
        """
        USB portuna hard reset at
        
        Args:
            port_device: Reset atılacak port
            
        Returns:
            bool: Reset başarılı mı?
        """
        try:
            import os
            import subprocess
            
            # Önce güç döngüsü dene
            power_script = os.path.join(os.path.dirname(__file__), "usb_power_cycle.sh")
            if os.path.exists(power_script):
                log_system(f"USB güç döngüsü başlatılıyor: {port_device}")
                result = subprocess.run([power_script, port_device], 
                                     capture_output=True, text=True)
                
                if result.returncode == 0:
                    log_success(f"USB güç döngüsü başarılı: {port_device}")
                    return True
                else:
                    log_warning(f"USB güç döngüsü başarısız, hard reset deneniyor: {result.stderr}")
            
            # Güç döngüsü başarısız olursa hard reset dene
            reset_script = os.path.join(os.path.dirname(__file__), "usb_reset_helper.sh")
            if os.path.exists(reset_script):
                log_system(f"USB hard reset başlatılıyor: {port_device}")
                result = subprocess.run([reset_script, port_device], 
                                     capture_output=True, text=True)
                
                if result.returncode == 0:
                    log_success(f"USB hard reset başarılı: {port_device}")
                    return True
                else:
                    log_error(f"USB hard reset hatası: {result.stderr}")
                    return False
            else:
                log_error(f"USB reset scriptleri bulunamadı")
                return False
                
        except Exception as e:
            log_error(f"USB reset hatası: {e}")
            return False

    def _reset_all_usb_ports(self) -> bool:
        """
        Tüm USB portlarını toplu olarak resetle
        
        Returns:
            bool: Reset başarılı mı?
        """
        try:
            import os
            import subprocess
            
            reset_all_script = os.path.join(os.path.dirname(__file__), "usb_reset_all.sh")
            if not os.path.exists(reset_all_script):
                log_error(f"USB toplu reset scripti bulunamadı: {reset_all_script}")
                return False
            
            log_system("TÜM USB portları resetleniyor...")
            # Sudo ile çalıştır (program zaten sudo ile çalışıyor olabilir)
            try:
                # Önce sudo olmadan dene
                result = subprocess.run([reset_all_script], 
                                     capture_output=True, text=True, timeout=30)
                if result.returncode != 0 and "Permission denied" in result.stderr:
                    # Permission hatası varsa sudo ile dene
                    log_warning("Permission hatası, sudo ile deneniyor...")
                    result = subprocess.run(['sudo', reset_all_script], 
                                         capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                log_error("USB reset timeout!")
                return False
            
            if result.returncode == 0:
                log_success("Tüm USB portları başarıyla resetlendi")
                # Çıktıyı logla
                for line in result.stdout.split('\n'):
                    if line.strip():
                        log_system(f"  {line}")
                
                # Reset sonrası autosuspend'i kapat
                time.sleep(1)  # USB cihazların yeniden tanınması için bekle
                self._disable_usb_autosuspend()
                
                return True
            else:
                log_error(f"USB toplu reset hatası: {result.stderr}")
                return False
                
        except Exception as e:
            log_error(f"USB toplu reset hatası: {e}")
            return False
    
    def _soft_usb_reset(self) -> bool:
        """
        Yumuşak USB reset (sadece CH341 sürücüsünü yeniden yükle)
        
        Returns:
            bool: İşlem başarılı mı?
        """
        try:
            log_system("Yumuşak USB reset başlatılıyor...")
            
            # CH341 sürücüsünü yeniden yükle
            result = subprocess.run(['modprobe', '-r', 'ch341'], 
                                 capture_output=True, text=True)
            if result.returncode != 0:
                log_warning(f"CH341 sürücüsü kaldırılamadı: {result.stderr}")
            
            time.sleep(1)  # Kısa bekleme
            
            result = subprocess.run(['modprobe', 'ch341'], 
                                 capture_output=True, text=True)
            if result.returncode != 0:
                log_error(f"CH341 sürücüsü yüklenemedi: {result.stderr}")
                return False
            
            log_success("CH341 sürücüsü başarıyla yeniden yüklendi")
            return True
            
        except Exception as e:
            log_error(f"Yumuşak USB reset hatası: {e}")
            return False

    def _run_autosuspend_script(self) -> bool:
        """
        USB autosuspend kapatma shell script'ini çalıştır
        
        Returns:
            bool: İşlem başarılı mı?
        """
        try:
            script_path = os.path.join(os.path.dirname(__file__), "usb_autosuspend_kapat.sh")
            if not os.path.exists(script_path):
                log_warning(f"USB autosuspend script bulunamadı: {script_path}")
                return False
            
            log_system("USB autosuspend shell script çalıştırılıyor...")
            result = subprocess.run([script_path], 
                                 capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                log_success("USB autosuspend shell script başarılı")
                # Çıktıyı logla
                for line in result.stdout.split('\n'):
                    if line.strip():
                        log_system(f"  {line}")
                return True
            else:
                log_warning(f"USB autosuspend shell script hatası: {result.stderr}")
                return False
                
        except Exception as e:
            log_error(f"USB autosuspend script hatası: {e}")
            return False

    def _disable_usb_autosuspend(self) -> bool:
        """
        USB autosuspend'i kapat (Motor kartının kaybolmasını önler)
        
        Returns:
            bool: İşlem başarılı mı?
        """
        try:
            log_system("USB autosuspend kapatılıyor...")
            disabled_count = 0
            
            # Yöntem 1: Tüm USB cihazları için autosuspend'i kapat
            control_files = glob.glob("/sys/bus/usb/devices/*/power/control")
            for control_file in control_files:
                try:
                    with open(control_file, 'w') as f:
                        f.write('on')
                    disabled_count += 1
                except (PermissionError, IOError):
                    pass  # Root değilse geç
            
            # Yöntem 2: CH340/CH341 için özel ayarlar (Vendor ID: 1a86)
            ch341_count = 0
            device_dirs = glob.glob("/sys/bus/usb/devices/*/idVendor")
            for vendor_file in device_dirs:
                try:
                    with open(vendor_file, 'r') as f:
                        vendor = f.read().strip()
                    
                    if vendor == "1a86":  # CH340/CH341
                        device_dir = os.path.dirname(vendor_file)
                        device_name = os.path.basename(device_dir)
                        
                        # Autosuspend kapat
                        control_file = os.path.join(device_dir, "power", "control")
                        if os.path.exists(control_file):
                            with open(control_file, 'w') as f:
                                f.write('on')
                            ch341_count += 1
                            
                        # Autosuspend delay'i maksimuma çıkar
                        delay_file = os.path.join(device_dir, "power", "autosuspend_delay_ms")
                        if os.path.exists(delay_file):
                            with open(delay_file, 'w') as f:
                                f.write('2147483647')
                        
                        # Persist aktif et
                        persist_file = os.path.join(device_dir, "power", "persist")
                        if os.path.exists(persist_file):
                            with open(persist_file, 'w') as f:
                                f.write('1')
                        
                        # Yöntem 3: Runtime suspend'i kapat
                        runtime_file = os.path.join(device_dir, "power", "runtime_enabled")
                        if os.path.exists(runtime_file):
                            with open(runtime_file, 'w') as f:
                                f.write('0')
                        
                        # Yöntem 4: Async suspend'i kapat
                        async_file = os.path.join(device_dir, "power", "async")
                        if os.path.exists(async_file):
                            with open(async_file, 'w') as f:
                                f.write('disabled')
                        
                        log_system(f"  - CH340/CH341 bulundu: {device_name} - autosuspend kapatıldı")
                        
                except (PermissionError, IOError):
                    pass  # Root değilse geç
            
            # Yöntem 5: Kernel parametresi kontrolü ve uygulama
            try:
                # GRUB parametresini kontrol et
                with open('/proc/cmdline', 'r') as f:
                    cmdline = f.read()
                
                if 'usbcore.autosuspend=-1' not in cmdline:
                    log_warning("GRUB'da usbcore.autosuspend=-1 yok - kalıcı çözüm için gerekli")
                    log_warning("Kalıcı çözüm için: sudo nano /etc/default/grub")
                    log_warning("GRUB_CMDLINE_LINUX=\"usbcore.autosuspend=-1\" ekleyin")
                    log_warning("Sonra: sudo update-grub && sudo reboot")
                
                # Geçici olarak kernel parametresini uygula
                subprocess.run(['echo', '-1'], stdout=open('/sys/module/usbcore/parameters/autosuspend', 'w'), 
                             check=False, timeout=5)
                log_system("  - Kernel autosuspend parametresi uygulandı")
                
            except Exception as e:
                log_warning(f"Kernel parametresi uygulanamadı: {e}")
            
            if disabled_count > 0 or ch341_count > 0:
                log_success(f"USB autosuspend kapatıldı ({disabled_count} cihaz, {ch341_count} CH340/CH341)")
                return True
            else:
                log_warning("USB autosuspend ayarları yapılamadı (root yetkisi gerekebilir)")
                return False
                
        except Exception as e:
            log_error(f"USB autosuspend kapatma hatası: {e}")
            return False

    def _close_all_ports(self, try_usb_reset: bool = False) -> None:
        """
        Tüm seri portları kapat
        
        Args:
            try_usb_reset: I/O hatası durumunda USB reset denensin mi?
        """
        try:
            log_system("Tüm açık portlar kapatılıyor...")
            ports = self.scanner.get_available_ports()
            has_io_error = False
            
            for port_info in ports:
                if self.scanner.is_compatible_port(port_info.device):
                    try:
                        # Portu açmayı dene ve hemen kapat
                        test_ser = serial.Serial(port_info.device, timeout=0.1)
                        test_ser.close()
                        log_system(f"{port_info.device} portu kapatıldı")
                    except serial.SerialException as e:
                        # Port zaten kapalı, meşgul veya I/O hatası
                        error_str = str(e).lower()
                        if "input/output" in error_str or "errno 5" in error_str:
                            log_warning(f"{port_info.device} I/O hatası - fiziksel bağlantı kopmuş: {e}")
                            has_io_error = True
                        elif any(keyword in error_str for keyword in ["permission", "busy", "in use"]):
                            log_warning(f"{port_info.device} port meşgul: {e}")
                        # Diğer SerialException'lar için sessiz geç
                    except OSError as e:
                        log_warning(f"{port_info.device} sistem hatası: {e}")
                    except Exception as e:
                        log_warning(f"{port_info.device} kapatma hatası: {e}")
            
            # I/O hatası varsa tüm USB portlarını resetle
            if has_io_error and try_usb_reset:
                log_warning("I/O hatası tespit edildi - TÜM USB portları resetleniyor...")
                if self._reset_all_usb_ports():
                    log_success("USB portları başarıyla resetlendi, 3 saniye bekleniyor...")
                    time.sleep(3)
            else:
            # Kısa bir bekleme ile portların tamamen serbest bırakılmasını sağla
                time.sleep(0.5)
            
            log_system("Port temizleme işlemi tamamlandı")
            
        except Exception as e:
            log_error(f"Port temizleme hatası: {e}")
    
    def baglan(self, cihaz_adi: Optional[str] = None, try_usb_reset: bool = True, max_retries: int = 2, kritik_kartlar: Optional[List[str]] = None) -> Tuple[bool, str, Dict[str, str]]:
        """
        Kartları bul ve bağlan
        
        Args:
            cihaz_adi: Aranacak spesifik cihaz adı (opsiyonel)
            try_usb_reset: I/O hatası durumunda USB reset denensin mi?
            max_retries: Maksimum deneme sayısı (USB reset ile)
            kritik_kartlar: Bulunması gereken kritik kartlar listesi (örn: ["motor", "sensor"])
            
        Returns:
            Tuple[bool, str, Dict[str, str]]: 
                - Başarı durumu
                - Mesaj
                - Bulunan kartlar (cihaz_adi: port)
        """
        # İlk deneme
        log_system(f"Kart arama başlatıldı (Deneme 1/{max_retries+1})")
        
        # İlk önce USB autosuspend'i kapat (sadece ilk denemede)
        if max_retries == 2:  # İlk deneme
            self._disable_usb_autosuspend()
            # Ek olarak shell script ile de dene
            self._run_autosuspend_script()
        
        # İlk olarak tüm portları kapat
        self._close_all_ports(try_usb_reset=try_usb_reset)
        
        start_time = time.time()
        log_system(f"Kart arama başlatıldı - Hedef: {cihaz_adi or 'Tümü'}")
        
        # Mevcut portları al
        ports = self.scanner.get_available_ports()
        if not ports:
            log_error("Hiçbir seri port bulunamadı!")
            return False, "Hiçbir seri port bulunamadı!", {}
        
        # Uyumlu portları filtrele
        compatible_ports = [
            p for p in ports 
            if self.scanner.is_compatible_port(p.device)
        ]
        
        if not compatible_ports:
            log_warning("Uyumlu port bulunamadı")
            return False, "Uyumlu port bulunamadı!", {}
        
        log_system(f"{len(compatible_ports)} uyumlu port bulundu")
        
        # Paralel port tarama
        discovered_devices = self._parallel_port_scan(compatible_ports, cihaz_adi)
        
        # Sonuçları değerlendir
        elapsed_time = time.time() - start_time
        basarili, mesaj, bulunan_kartlar = self._evaluate_results(discovered_devices, cihaz_adi, elapsed_time)
        
        # Kritik kartları kontrol et
        kritik_eksik = False
        if kritik_kartlar:
            eksik_kartlar = [kart for kart in kritik_kartlar if kart not in bulunan_kartlar]
            if eksik_kartlar:
                kritik_eksik = True
                log_warning(f"Kritik kartlar eksik: {eksik_kartlar}")
        
        # Başarısızsa VEYA kritik kart eksikse, USB reset dene
        if (not basarili or kritik_eksik) and try_usb_reset and max_retries > 0:
            log_warning(f"İlk denemede başarısız (basarili={basarili}, kritik_eksik={kritik_eksik})")
            log_warning(f"USB reset ile tekrar deneniyor ({max_retries} deneme kaldı)")
            
            # Direkt agresif reset dene (daha güvenilir)
            log_warning("Direkt agresif USB reset deneniyor...")
            if self._reset_all_usb_ports():
                log_success("Agresif USB reset başarılı, portlar yeniden taranacak...")
                time.sleep(5)  # USB hub reset sonrası daha uzun bekleme
                
                # Tekrar dene (max_retries-1 ile)
                return self.baglan(cihaz_adi=cihaz_adi, try_usb_reset=False, max_retries=max_retries-1, kritik_kartlar=kritik_kartlar)
            else:
                # Agresif reset başarısız, yumuşak reset dene
                log_warning("Agresif reset başarısız, yumuşak reset deneniyor...")
                if self._soft_usb_reset():
                    log_success("Yumuşak USB reset başarılı, portlar yeniden taranacak...")
                    time.sleep(3)  # Portların oluşması için bekle
                    
                    # Tekrar dene (max_retries-1 ile)
                    return self.baglan(cihaz_adi=cihaz_adi, try_usb_reset=False, max_retries=max_retries-1, kritik_kartlar=kritik_kartlar)
                else:
                    log_error("Her iki USB reset yöntemi de başarısız oldu")
        
        return basarili, mesaj, bulunan_kartlar
    
    def _parallel_port_scan(self, ports: List, target_device: Optional[str] = None) -> Dict[str, str]:
        """
        Portları paralel olarak tara
        
        Args:
            ports: Taranacak port listesi
            target_device: Hedef cihaz adı
            
        Returns:
            Dict[str, str]: Bulunan cihazlar
        """
        discovered = {}
        
        # Thread pool ile paralel tarama
        with ThreadPoolExecutor(max_workers=min(len(ports), Constants.THREAD_POOL_SIZE)) as executor:
            # Görevleri başlat
            future_to_port = {
                executor.submit(self._scan_single_port, port, target_device): port 
                for port in ports
            }
            
            # Sonuçları topla
            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    result = future.result(timeout=10)
                    if result:
                        device_type, port_name = result
                        discovered[device_type] = port_name
                        
                        # Hedef cihaz bulunduysa diğerlerini iptal et
                        if target_device and device_type == target_device:
                            for f in future_to_port:
                                if f != future:
                                    f.cancel()
                            break
                            
                except Exception as e:
                    log_error(f"{port.device} tarama hatası: {e}")
        
        return discovered
    
    def _scan_single_port(self, port_info, target_device: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Tek bir portu tara
        
        Args:
            port_info: Port bilgisi
            target_device: Hedef cihaz
            
        Returns:
            Optional[Tuple[str, str]]: (cihaz_tipi, port_adı) veya None
        """
        port_device = port_info.device
        
        log_system(f"{port_device} taranıyor...")
        
        # Port'un fiziksel olarak mevcut olup olmadığını kontrol et
        try:
            # Port dosyasının varlığını kontrol et (Linux için)
            import os
            if not os.path.exists(port_device):
                log_warning(f"{port_device} fiziksel olarak mevcut değil")
                return None
        except:
            pass  # Windows'ta bu kontrol çalışmayabilir
        
        with self.connection.open_port(port_device) as ser:
            if not ser:
                log_warning(f"{port_device} açılamadı")
                return None
            
            try:
                # Port açıldıktan sonra tekrar erişilebilirlik kontrolü
                try:
                    ser.is_open  # Port durumunu kontrol et
                    ser.reset_input_buffer()  # Buffer'a erişimi test et
                except (OSError, serial.SerialException) as e:
                    log_warning(f"{port_device} erişim testi başarısız: {e}")
                    return None
                
                # Hardware başlatma beklemesi
                time.sleep(Constants.HARDWARE_INIT_TIME)
                
                # Cihazı resetle
                self.communicator.reset_device(ser)
                
                # Cihaz kimliğini sorgula
                device_type = self.communicator.identify_device(ser)
                
                if device_type:
                    device_name = device_type.value
                    log_success(f"{device_name.upper()} kartı {port_device} portunda bulundu")
                    
                    # Bağlantıyı onayla
                    if self.communicator.confirm_connection(ser):
                        log_system(f"{device_name} bağlantısı onaylandı")
                    
                    return device_name, port_device
                else:
                    log_warning(f"{port_device} - Tanımlanamayan cihaz")
                    
            except (serial.SerialException, OSError) as e:
                error_str = str(e).lower()
                if "input/output" in error_str or "errno 5" in error_str:
                    log_error(f"{port_device} I/O hatası - cihaz fiziksel olarak kopmuş: {e}")
                else:
                    log_error(f"{port_device} iletişim hatası: {e}")
            except Exception as e:
                log_error(f"{port_device} beklenmeyen hata: {e}")
        
        return None
    
    def _evaluate_results(self, discovered: Dict[str, str], 
                         target_device: Optional[str], 
                         elapsed_time: float) -> Tuple[bool, str, Dict[str, str]]:
        """
        Tarama sonuçlarını değerlendir
        
        Args:
            discovered: Bulunan cihazlar
            target_device: Hedef cihaz
            elapsed_time: Geçen süre
            
        Returns:
            Tuple[bool, str, Dict[str, str]]: Sonuç tuple'ı
        """
        log_system(f"Tarama tamamlandı - Süre: {elapsed_time:.2f} saniye")
        
        if not discovered:
            log_error("Tanımlı hiçbir kart bulunamadı!")
            return False, "Tanımlı hiçbir kart bulunamadı!", {}
        
        if target_device:
            if target_device in discovered:
                log_success(f"'{target_device}' kartı başarıyla bulundu")
                return True, f"'{target_device}' kartı bulundu", {target_device: discovered[target_device]}
            else:
                log_warning(f"'{target_device}' bulunamadı. Mevcut: {list(discovered.keys())}")
                return False, f"'{target_device}' kartı bulunamadı", discovered
        else:
            log_success(f"{len(discovered)} kart bulundu: {list(discovered.keys())}")
            return True, f"{len(discovered)} kart bulundu", discovered
    
    def __repr__(self) -> str:
        """String temsili"""
        return f"KartHaberlesmeServis(baudrate={self.baudrate}, system={self.system})"


# Opsiyonel: Async versiyon için hazırlık
class AsyncKartHaberlesmeServis:
    """
    Asenkron kart haberleşme servisi (Gelecek geliştirme için)
    """
    
    def __init__(self, baudrate: int = Constants.DEFAULT_BAUDRATE):
        self.baudrate = baudrate
        # Async implementasyon gelecekte eklenebilir
    
    async def baglan_async(self, cihaz_adi: Optional[str] = None):
        """Asenkron bağlantı metodu"""
        # TODO: Async/await implementasyonu
        pass