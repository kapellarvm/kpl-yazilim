#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import logging

# Pymodbus import - farklı versiyonlar için uyumluluk
try:
    from pymodbus.client.sync import ModbusSerialClient
except ImportError:
    try:
        from pymodbus.client.serial import ModbusSerialClient
    except ImportError:
        from pymodbus.client import ModbusSerialClient

from ...utils.terminal import section, status, ok, warn, err, step
from ...dimdb.config import config

class GA500ModbusClient:
    """GA500 Modbus RTU Client - GUI kodundaki frekans mantığı ile"""
    
    def __init__(self, port=None, baudrate=9600, 
                 stopbits=1, parity='N', bytesize=8, timeout=1,
                 logger=None, callback=None, cihaz_adi="modbus"):
        
        # Makine sınıfını al
        self.makine_sinifi = config.MAKINE_SINIFI
        self.kirici_var_mi = self.makine_sinifi == "KPL-04"  # True: KPL-04 (Kırıcılı), False: KPL-05 (Kırıcısız)
        
        # Port otomatik tespit edilecek - genişletilmiş port listesi
        if port is None:
            self.port_list = [
                "/dev/ttyS0", "/dev/ttyS1", "/dev/ttyS2", "/dev/ttyS3",
                "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3",
                "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2"
            ]
        else:
            self.port_list = [port]
        
        # Başarılı portlar burada saklanacak
        self.ezici_port = None  # Ezici motor portu
        self.kirici_port = None  # Kırıcı motor portu (sadece KPL-04)
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.bytesize = bytesize
        self.timeout = timeout
        
        # Callback parametreleri - sensör kartı mantığı
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        
        self.client = None
        self.is_connected = False
        self.lock = threading.Lock()
        
        if logger is None:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        
        # Thread-based sürekli okuma için
        self.reading_thread = None
        self.stop_reading = False
        
        # Status data - makine tipine göre
        self.status_data = {1: {}}  # Ezici motor (slave 1)
        if self.kirici_var_mi:  # True: KPL-04 (Kırıcılı), False: KPL-05 (Kırıcısız)
            self.status_data[2] = {}  # Kırıcı motor (slave 2, sadece KPL-04)
        
        # Modbus client'ları
        self.ezici_client = None  # Ezici motor client'ı
        self.kirici_client = None  # Kırıcı motor client'ı (sadece KPL-04)
        
        # Bağlantı durumları
        self.ezici_connected = False
        self.kirici_connected = False
        
        # GA500 registerleri - GUI kodundan
        self.CONTROL_REGISTER = 0x0001  # RUN_REG = 1 
        self.FREQUENCY_REGISTER = 0x0002  # FREQ_REG = 2
        self.STATUS_REGISTER = 0x0020
        
        # Monitor registerleri - GUI kodundan
        self.MON_BASE = 0x0023        # 5 adet ardışık: ref freq, out freq, out volt, out current, out power
        self.DCBUS_REG = 0x0031       # DC bus voltage
        self.TEMP_REG = 0x0068        # Temperature
        
        # Komutlar - GUI kodundan
        self.CMD_STOP = 0x0000
        self.CMD_FORWARD = 0x0001
        self.CMD_REVERSE = 0x0002
        self.CMD_RESET = 0x0008
        
    def connect(self):
        """Modbus bağlantısını başlat ve sürücüleri resetle - Port otomatik tespit"""
        
        # Önce ezici motor bağlantısını dene
        self.logger.info("🔍 Ezici motor portu aranıyor...")
        ezici_success = self._connect_drive(1, "Ezici")
        if not ezici_success:
            self.logger.error("❌ Ezici motor bağlantısı başarısız!")
            return False
        
        # KPL-04 için kırıcı motor bağlantısını da dene
        if self.kirici_var_mi:
            self.logger.info("🔍 Kırıcı motor portu aranıyor...")
            kirici_success = self._connect_drive(2, "Kırıcı")
            if not kirici_success:
                self.logger.error("❌ Kırıcı motor bağlantısı başarısız!")
                # Ezici bağlantısını da kapat
                if self.ezici_client:
                    self.ezici_client.close()
                    self.ezici_connected = False
                return False
        
        # Tüm bağlantılar başarılı
        self.is_connected = True
        return True
    
    def _connect_drive(self, slave_id, drive_name):
        """Belirli bir sürücü için port arama ve bağlantı"""
        for test_port in self.port_list:
            try:
                # Modbus bağlantısı deneniyor
                client = ModbusSerialClient(
                    method='rtu',
                    port=test_port,
                    baudrate=self.baudrate,
                    stopbits=self.stopbits,
                    parity=self.parity,
                    bytesize=self.bytesize,
                    timeout=self.timeout
                )
                
                if client.connect():
                    # Basit bir test ile bağlantıyı doğrula
                    test_result = client.read_holding_registers(address=0x0020, count=1, unit=slave_id)
                    if not test_result.isError():
                        # Başarılı portu kaydet
                        if slave_id == 1:
                            self.ezici_port = test_port
                            self.ezici_client = client
                            self.ezici_connected = True
                        else:
                            self.kirici_port = test_port
                            self.kirici_client = client
                            self.kirici_connected = True
                        
                        self.logger.info(f"✅ {drive_name} motor portu bulundu: {test_port}")
                        
                        # SÜRÜCÜYE RESET GÖNDER
                        self.reset(slave_id)
                        return True
                    else:
                        client.close()
                else:
                    pass
                    
            except Exception as e:
                self.logger.warning(f"⚠️ {test_port} bağlantı hatası: {e}")
        
        # Hiçbir port çalışmazsa
        self.logger.error(f"❌ {drive_name} motor portu bulunamadı!")
        self.logger.error("📋 Denenen portlar: " + ", ".join(self.port_list))
        return False
    
    def _handle_connection_error(self):
        """Bağlantı hatası durumunda yeniden bağlantı dene"""
        try:
            self.logger.warning("🔄 Bağlantı hatası tespit edildi, yeniden bağlanıyor...")
            
            # UPS kesintisi tespit edildi - hemen işlemleri başlat
            self._trigger_ups_power_failure()
            
            # Mevcut bağlantıları kapat
            if self.ezici_client and self.ezici_connected:
                self.ezici_client.close()
                self.ezici_connected = False
            
            if self.kirici_var_mi and self.kirici_client and self.kirici_connected:
                self.kirici_client.close()
                self.kirici_connected = False
            
            self.is_connected = False
            
            # Yeniden bağlantı parametreleri
            max_retries = 5  # Maksimum deneme sayısı
            retry_delay = 5  # Denemeler arası bekleme süresi (saniye)
            current_retry = 0
            
            while current_retry < max_retries:
                current_retry += 1
                self.logger.info(f"🔄 Yeniden bağlantı denemesi {current_retry}/{max_retries}")
                
                # Port listesini başarılı portlara göre düzenle
                test_ports = []
                
                # Ezici portu varsa önce onu dene
                if self.ezici_port:
                    test_ports.append(self.ezici_port)
                
                # Kırıcı portu varsa sonra onu dene
                if self.kirici_var_mi and self.kirici_port:
                    test_ports.append(self.kirici_port)
                
                # Diğer portları ekle
                for p in self.port_list:
                    if p not in test_ports:
                        test_ports.append(p)
                
                self.port_list = test_ports
                self.logger.info(f"🔍 Port sırası: {self.port_list}")
                
                # Yeniden bağlan
                if self.connect():
                    self.logger.info(f"✅ Yeniden bağlantı başarılı (Deneme {current_retry})")
                    return True
                
                # Başarısız deneme sonrası bekle
                if current_retry < max_retries:
                    self.logger.warning(f"⏳ {retry_delay} saniye sonra tekrar denenecek...")
                    time.sleep(retry_delay)
            
            # Tüm denemeler başarısız
            self.logger.error(f"❌ {max_retries} deneme sonrası bağlantı kurulamadı!")
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Yeniden bağlantı hatası: {e}")
            return False
    
    def _trigger_ups_power_failure(self):
        """UPS kesintisi tespit edildiğinde işlemleri başlat"""
        try:
            import asyncio
            from ...api.servisler.ups_power_handlers import handle_power_failure
            
            section("⚡ ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!", "UPS çalışıyor - Acil işlemler başlatılıyor")
            
            # Asenkron fonksiyonu çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_power_failure())
            loop.close()
            
        except Exception as e:
            err("UPS KESİNTİSİ", f"İşlem hatası: {e}")
            self.logger.error(f"UPS kesintisi işleme hatası: {e}")
    
    def disconnect(self):
        """Modbus bağlantılarını kapat"""
        try:
            # Sürekli okuma thread'ini durdur
            self.stop_reading = True
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=2)
            
            # Ezici motor bağlantısını kapat
            if self.ezici_client and self.ezici_connected:
                self.ezici_client.close()
                self.ezici_connected = False
                self.logger.info("🔌 Ezici motor bağlantısı kapatıldı")
            
            # Kırıcı motor bağlantısını kapat (KPL-04)
            if self.kirici_var_mi and self.kirici_client and self.kirici_connected:
                self.kirici_client.close()
                self.kirici_connected = False
                self.logger.info("🔌 Kırıcı motor bağlantısı kapatıldı")
            
            self.is_connected = False
            
        except Exception as e:
            self.logger.error(f"❌ Bağlantı kapatma hatası: {e}")
    
    def set_frequency(self, slave_id, frequency):
        """Frekans değerini ayarla (Hz) - GUI kodundaki mantık"""
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return False
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return False
            
            # GUI kodundaki gibi: hz * 100 (0.01 Hz çözünürlük)
            freq_value = int(frequency * 100)
            
            result = client.write_register(self.FREQUENCY_REGISTER, freq_value, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Motor {slave_id}: Frekans ayarlandı ({frequency} Hz)")
                return True
            else:
                self.logger.error(f"❌ Motor {slave_id}: Frekans ayarlama hatası")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Frekans ayarlama hatası: {e}")
            self._handle_connection_error()
            return False
    
    def run_forward(self, slave_id):
        """İleri yönde çalıştır"""
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return False
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return False
            
            self.logger.info(f"▶️ Motor {slave_id}: İleri çalıştırma")
            
            result = client.write_register(self.CONTROL_REGISTER, self.CMD_FORWARD, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Motor {slave_id}: İleri çalıştırıldı")
                return True
            else:
                self.logger.error(f"❌ Motor {slave_id}: İleri çalıştırma hatası")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ İleri çalıştırma hatası: {e}")
            self._handle_connection_error()
            return False
    
    def stop(self, slave_id):
        """Motoru durdur"""
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return False
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return False
            
            self.logger.info(f"⏹️ Motor {slave_id}: Durdurma")
            
            result = client.write_register(self.CONTROL_REGISTER, self.CMD_STOP, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Motor {slave_id}: Durduruldu")
                return True
            else:
                self.logger.error(f"❌ Motor {slave_id}: Durdurma hatası")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Durdurma hatası: {e}")
            self._handle_connection_error()
            return False
    
    def reset(self, slave_id):
        """Sürücüyü resetle - Bağlantı için gerekli"""
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return False
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return False
            
            self.logger.info(f"🔄 Motor {slave_id}: Reset atılıyor...")
            
            result = client.write_register(self.CONTROL_REGISTER, self.CMD_RESET, unit=slave_id)
            if not result.isError():
                time.sleep(0.5)  # Reset sonrası bekleme
                self.logger.info(f"✅ Motor {slave_id}: Reset tamamlandı")
                return True
            else:
                self.logger.error(f"❌ Motor {slave_id}: Reset hatası")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Reset hatası: {e}")
            self._handle_connection_error()
            return False
    
    def clear_fault(self, slave_id):
        """Arıza durumunu temizle - GA500 için arıza reset"""
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return False
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return False
            
            self.logger.info(f"🔧 Motor {slave_id}: Arıza temizleniyor...")
            
            # Önce reset gönder
            reset_result = client.write_register(self.CONTROL_REGISTER, self.CMD_RESET, unit=slave_id)
            if reset_result.isError():
                self.logger.error(f"❌ Motor {slave_id}: Arıza reset hatası")
                self._handle_connection_error()
                return False
            
            time.sleep(0.5)  # Reset sonrası bekleme
            
            # Arıza durumunu kontrol et
            status_result = client.read_holding_registers(address=self.STATUS_REGISTER, count=1, unit=slave_id)
            if not status_result.isError():
                status = status_result.registers[0]
                fault_bit = status & 0x8  # Bit 3: Arıza durumu
                
                if fault_bit == 0:
                    self.logger.info(f"✅ Motor {slave_id}: Arıza temizlendi")
                    return True
                else:
                    self.logger.warning(f"⚠️ Motor {slave_id}: Arıza hala mevcut, tekrar deneyiniz")
                    return False
            else:
                self.logger.error(f"❌ Motor {slave_id}: Durum okuma hatası")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Arıza temizleme hatası: {e}")
            self._handle_connection_error()
            return False
    
    def read_status_registers(self, slave_id):
        """Sürücü durum registerlerini oku - GUI kodundaki mantık"""
        status_data = {}
        
        try:
            # Makine tipine göre kontrol
            if slave_id == 2 and not self.kirici_var_mi:
                self.logger.error("❌ Bu makinede kırıcı motor yok! (KPL-05)")
                return {}
            
            # Doğru client'ı seç
            client = self.ezici_client if slave_id == 1 else self.kirici_client
            if not client:
                self.logger.error(f"❌ Motor {slave_id} client'ı bulunamadı!")
                return {}
            
            with self.lock:
                # GUI kodundaki gibi register okuma
                r1 = client.read_holding_registers(address=self.MON_BASE, count=5, unit=slave_id)
                r2 = client.read_holding_registers(address=self.DCBUS_REG, count=1, unit=slave_id)
                r3 = client.read_holding_registers(address=self.STATUS_REGISTER, count=1, unit=slave_id)
                r4 = client.read_holding_registers(address=self.TEMP_REG, count=1, unit=slave_id)
            
            # Verileri parse et - ac_surucu_v1.py kodundaki doğru mantık
            if r1 and r2 and r3 and r4 and not (r1.isError() or r2.isError() or r3.isError() or r4.isError()):
                # ac_surucu_v1.py kodundaki doğru scaling
                status_data['freq_reference'] = {
                    'value': r1.registers[0] / 100.0,  # ÷100 (0.01 Hz çözünürlük)
                    'raw': r1.registers[0],
                    'unit': 'Hz',
                    'description': 'Frekans Referansı'
                }
                status_data['output_freq'] = {
                    'value': r1.registers[1] / 100.0,  # ÷100 (0.01 Hz çözünürlük)
                    'raw': r1.registers[1],
                    'unit': 'Hz',
                    'description': 'Çıkış Frekansı'
                }
                status_data['output_voltage'] = {
                    'value': r1.registers[2] / 10.0,   # ÷10 (0.1V çözünürlük)
                    'raw': r1.registers[2],
                    'unit': 'V',
                    'description': 'Çıkış Voltajı'
                }
                status_data['output_current'] = {
                    'value': r1.registers[3] / 10.0,   # ÷10 (0.1A çözünürlük)
                    'raw': r1.registers[3],
                    'unit': 'A',
                    'description': 'Çıkış Akımı'
                }
                status_data['output_power'] = {
                    'value': r1.registers[4] / 100.0,  # ÷100 (0.01 kW çözünürlük)
                    'raw': r1.registers[4],
                    'unit': 'kW',
                    'description': 'Güç Çıkışı'
                }
                
                # r2: dc_bus_voltage
                status_data['dc_bus_voltage'] = {
                    'value': r2.registers[0],
                    'raw': r2.registers[0],
                    'unit': 'V',
                    'description': 'DC Bus Voltajı'
                }
                
                # r3: drive_status
                status_data['drive_status'] = {
                    'value': r3.registers[0],
                    'raw': r3.registers[0],
                    'unit': '',
                    'description': 'Sürücü Durumu'
                }
                
                # r4: temperature
                status_data['temperature'] = {
                    'value': r4.registers[0],
                    'raw': r4.registers[0],
                    'unit': '°C',
                    'description': 'Sıcaklık'
                }
            else:
                self.logger.error(f"❌ Motor {slave_id}: Register okuma hatası")
                # Register okuma hatası durumunda yeniden bağlantı dene
                self._handle_connection_error()
                
        except Exception as e:
            self.logger.error(f"❌ Status okuma hatası: {e}")
            # Exception durumunda da yeniden bağlantı dene
            self._handle_connection_error()
        
        return status_data
    
    def continuous_reading_worker(self):
        """Sürekli okuma worker thread'i"""
        consecutive_errors = 0
        max_errors = 3  # 3 ardışık hata sonrası yeniden bağlan
        reconnect_attempt = 0
        
        # Yeniden bağlantı aralıkları (saniye)
        retry_intervals = [
            10,     # İlk 10 deneme: 10 saniye aralıkla
            30,     # Sonraki 10 deneme: 30 saniye aralıkla
            60,     # Sonraki 10 deneme: 1 dakika aralıkla
            300     # Sonraki denemeler: 5 dakika aralıkla
        ]
        
        while not self.stop_reading:
            try:
                # Bağlantı yoksa yeniden bağlanmayı dene
                if not self.is_connected:
                    reconnect_attempt += 1
                    
                    # Deneme sayısına göre bekleme süresini belirle
                    if reconnect_attempt <= 10:
                        wait_time = retry_intervals[0]
                        phase = "Faz 1"
                    elif reconnect_attempt <= 20:
                        wait_time = retry_intervals[1]
                        phase = "Faz 2"
                    elif reconnect_attempt <= 30:
                        wait_time = retry_intervals[2]
                        phase = "Faz 3"
                    else:
                        wait_time = retry_intervals[3]
                        phase = "Faz 4"
                    
                    self.logger.warning(f"⚡ Bağlantı kopuk. {phase}: Deneme {reconnect_attempt} ({wait_time} saniye aralıkla)")
                    
                    if self._handle_connection_error():
                        self.logger.info("✅ Bağlantı yeniden kuruldu!")
                        reconnect_attempt = 0  # Başarılı bağlantı sonrası sayacı sıfırla
                        consecutive_errors = 0
                    else:
                        self.logger.warning(f"⏳ {wait_time} saniye sonra tekrar denenecek...")
                        time.sleep(wait_time)
                        continue
                
                success = True
                
                # Ezici motor okuma (her zaman)
                if self.stop_reading:
                    break
                
                # Ezici motor status'unu oku
                ezici_status = self.read_status_registers(1)
                if not ezici_status:
                    success = False
                else:
                    # Thread-safe veri güncelleme
                    with self.lock:
                        self.status_data[1] = ezici_status
                    
                    # Konsola yazdır ve callback'e gönder
                    modbus_veri = self.print_status(1, ezici_status)
                    if modbus_veri and self.callback:
                        try:
                            veri_str = "s1:" + ",".join([f"{k}:{v}" for k, v in modbus_veri.items()])
                            self.callback(veri_str)
                        except Exception as e:
                            self.logger.error(f"❌ Ezici callback hatası: {e}")
                
                # Kırıcı motor okuma (sadece KPL-04)
                if self.kirici_var_mi and self.kirici_connected:
                    kirici_status = self.read_status_registers(2)
                    if not kirici_status:
                        success = False
                    else:
                        # Thread-safe veri güncelleme
                        with self.lock:
                            self.status_data[2] = kirici_status
                        
                        # Konsola yazdır ve callback'e gönder
                        modbus_veri = self.print_status(2, kirici_status)
                        if modbus_veri and self.callback:
                            try:
                                veri_str = "s2:" + ",".join([f"{k}:{v}" for k, v in modbus_veri.items()])
                                self.callback(veri_str)
                            except Exception as e:
                                self.logger.error(f"❌ Kırıcı callback hatası: {e}")

                if success:
                    consecutive_errors = 0  # Başarılı okuma, error sayacını sıfırla
                    reconnect_attempt = 0  # Başarılı okuma sonrası yeniden bağlantı sayacını da sıfırla
                
                else:
                    consecutive_errors += 1
                    self.logger.warning(f"⚠️ Okuma hatası #{consecutive_errors}")
                    
                    # Çok fazla ardışık hata varsa yeniden bağlan
                    if consecutive_errors >= max_errors:
                        self.logger.error(f"❌ {max_errors} ardışık okuma hatası, yeniden bağlanıyor...")
                        consecutive_errors = 0
                        if not self._handle_connection_error():
                            self.is_connected = False  # Bağlantı başarısız, ana döngü yeniden deneyecek
                
                # 0.5 saniye bekle
                time.sleep(0.5)


            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"❌ Okuma thread hatası #{consecutive_errors}: {e}")
                
                # Çok fazla ardışık hata varsa yeniden bağlan
                if consecutive_errors >= max_errors:
                    self.logger.error(f"❌ {max_errors} ardışık thread hatası, yeniden bağlanıyor...")
                    consecutive_errors = 0
                    self._handle_connection_error()
                
                time.sleep(1)
    
    def print_status(self, slave_id, status):
        """Status verilerini formatla ve döndür"""
        if not status:
            return None
            
        freq_ref = status.get('freq_reference', {}).get('value', 0)
        freq_out = status.get('output_freq', {}).get('value', 0)
        voltage = status.get('output_voltage', {}).get('value', 0)
        current = status.get('output_current', {}).get('value', 0)
        power = status.get('output_power', {}).get('value', 0)
        dc_voltage = status.get('dc_bus_voltage', {}).get('value', 0)
        temperature = status.get('temperature', {}).get('value', 0)
        drive_status = status.get('drive_status', {}).get('raw', 0)
        
        # Durum analizi - GUI kodundaki mantık
        is_running = (drive_status & 0x0001) != 0
        is_ready = (drive_status & 0x0004) != 0
        has_fault = (drive_status & 0x0008) != 0
        
        # Yön bilgisi sadece motor çalışırken gösterilir
        if is_running:
            direction = "İLERİ" if (drive_status & 0x0002) else "GERİ"
        else:
            direction = "DURUYOR"
        
        status_text = "ÇALIŞIYOR" if is_running else "DURUYOR"
        ready_text = "EVET" if is_ready else "HAYIR"
        fault_text = "VAR" if has_fault else "YOK"
        
        # Callback için formatlanmış string döndür
        modbus_data = {
            'freq_ref': freq_ref,
            'freq_out': freq_out,
            'voltage': voltage,
            'current': current,
            'power': power,
            'dc_voltage': dc_voltage,
            'temperature': temperature,
            'status': status_text,
            'direction': direction,
            'ready': ready_text,
            'fault': fault_text
        }
        
        return modbus_data
    
    def get_bus_voltage(self, slave_id=1):
        """Bus voltage değerini döndürür - Voltage monitoring için"""
        try:
            if not self.is_connected:
                return None
                
            # Status register'larını oku
            status_data = self.read_status_registers(slave_id)
            
            if status_data and 'dc_bus_voltage' in status_data:
                voltage_data = status_data['dc_bus_voltage']
                voltage_value = voltage_data.get('value', None)
                return voltage_value
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Bus voltage okuma hatası: {e}")
            return None
    
    def start_continuous_reading(self):
        """Sürekli okuma thread'ini başlat"""
        if self.reading_thread is not None and self.reading_thread.is_alive():
            # Okuma thread'i zaten çalışıyor - sadece log dosyasına yazılır
            return
        
        self.stop_reading = False
        self.reading_thread = threading.Thread(target=self.continuous_reading_worker, daemon=True)
        self.reading_thread.start()
        # Sürekli okuma thread'i başlatıldı - sadece log dosyasına yazılır
    
    def stop_continuous_reading(self):
        """Sürekli okuma thread'ini durdur"""
        self.stop_reading = True
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=2)
        self.logger.info("⏹️ Sürekli okuma thread'i durduruldu")
