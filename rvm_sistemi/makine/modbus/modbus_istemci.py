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

class GA500ModbusClient:
    """GA500 Modbus RTU Client - GUI kodundaki frekans mantığı ile"""
    
    def __init__(self, port=None, baudrate=9600, 
                 stopbits=1, parity='N', bytesize=8, timeout=1,
                 logger=None):
        
        # Port otomatik tespit edilecek (ttyS0 önce, sonra ttyS1)
        self.port_list = ["/dev/ttyS0", "/dev/ttyS1"] if port is None else [port]
        self.port = None  # Başarılı port burada saklanacak
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.bytesize = bytesize
        self.timeout = timeout
        
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
        self.status_data = {1: {}, 2: {}}
        
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
        for test_port in self.port_list:
            try:
                self.logger.info(f"🔌 Modbus bağlantısı deneniyor: {test_port}")
                
                self.client = ModbusSerialClient(
                    method='rtu',
                    port=test_port,
                    baudrate=self.baudrate,
                    stopbits=self.stopbits,
                    parity=self.parity,
                    bytesize=self.bytesize,
                    timeout=self.timeout
                )
                
                if self.client.connect():
                    # Basit bir test ile bağlantıyı doğrula
                    test_result = self.client.read_holding_registers(address=0x0020, count=1, unit=1)
                    if not test_result.isError():
                        self.port = test_port  # Başarılı portu kaydet
                        self.is_connected = True
                        self.logger.info(f"✅ Modbus bağlantısı başarılı: {test_port}")
                        
                        # SÜRÜCÜLERE RESET GÖNDER - Sürekli haberleşme için gerekli
                        self.logger.info("🔄 Sürücülere reset gönderiliyor...")
                        self.reset(1)  # Sürücü 1'i resetle
                        self.reset(2)  # Sürücü 2'yi resetle
                        
                        self.logger.info("✅ Reset tamamlandı, sürekli haberleşme başlayacak")
                        return True
                    else:
                        self.logger.warning(f"⚠️ {test_port} portunda cihaz bulunamadı")
                        self.client.close()
                else:
                    self.logger.warning(f"⚠️ {test_port} portuna bağlanılamadı")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ {test_port} bağlantı hatası: {e}")
                
        # Hiçbir port çalışmazsa
        self.logger.error("❌ Hiçbir Modbus portuna bağlanılamadı!")
        self.logger.error("📋 Denenen portlar: " + ", ".join(self.port_list))
        return False
    
    def _handle_connection_error(self):
        """Bağlantı hatası durumunda yeniden bağlantı dene"""
        try:
            self.logger.warning("🔄 Bağlantı hatası tespit edildi, yeniden bağlanıyor...")
            
            # Mevcut bağlantıyı kapat
            if self.client and self.is_connected:
                self.client.close()
                self.is_connected = False
            
            # Kısa bekleme
            time.sleep(1)
            
            # Mevcut başarılı portu önce dene, sonra diğerlerini
            if self.port:
                # Önceki başarılı port varsa önce onu dene
                test_ports = [self.port]
                # Sonra diğer portları ekle
                for p in self.port_list:
                    if p != self.port:
                        test_ports.append(p)
                self.port_list = test_ports
                self.logger.info(f"🔄 Port sırası güncellendi: {self.port_list}")
            
            # Yeniden bağlan
            if self.connect():
                self.logger.info("✅ Yeniden bağlantı başarılı")
                return True
            else:
                self.logger.error("❌ Yeniden bağlantı başarısız")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Yeniden bağlantı hatası: {e}")
            return False
    
    def disconnect(self):
        """Modbus bağlantısını kapat"""
        try:
            self.stop_reading = True
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=2)
                
            if self.client and self.is_connected:
                self.client.close()
                self.is_connected = False
                self.logger.info("🔌 Modbus bağlantısı kapatıldı")
        except Exception as e:
            self.logger.error(f"❌ Bağlantı kapatma hatası: {e}")
    
    def set_frequency(self, slave_id, frequency):
        """Frekans değerini ayarla (Hz) - GUI kodundaki mantık"""
        try:
            self.logger.info(f"🔧 Sürücü {slave_id}: Frekans ayarlanıyor {frequency} Hz")
            
            # GUI kodundaki gibi: hz * 100 (0.01 Hz çözünürlük)
            freq_value = int(frequency * 100)
            
            result = self.client.write_register(self.FREQUENCY_REGISTER, freq_value, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Sürücü {slave_id}: Frekans ayarlandı {frequency} Hz")
                return True
            else:
                self.logger.error(f"❌ Register yazma hatası: {result}")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Frekans ayarlama hatası: {e}")
            self._handle_connection_error()
            return False
    
    def run_forward(self, slave_id):
        """İleri yönde çalıştır"""
        try:
            self.logger.info(f"▶️ Sürücü {slave_id}: İleri çalıştırma")
            
            result = self.client.write_register(self.CONTROL_REGISTER, self.CMD_FORWARD, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Sürücü {slave_id}: İleri çalıştırıldı")
                return True
            else:
                self.logger.error(f"❌ İleri çalıştırma hatası: {result}")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ İleri çalıştırma hatası: {e}")
            self._handle_connection_error()
            return False
    
    def stop(self, slave_id):
        """Motoru durdur"""
        try:
            self.logger.info(f"⏹️ Sürücü {slave_id}: Durdurma")
            
            result = self.client.write_register(self.CONTROL_REGISTER, self.CMD_STOP, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Sürücü {slave_id}: Durduruldu")
                return True
            else:
                self.logger.error(f"❌ Durdurma hatası: {result}")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Durdurma hatası: {e}")
            self._handle_connection_error()
            return False
    
    def reset(self, slave_id):
        """Sürücüyü resetle - Bağlantı için gerekli"""
        try:
            self.logger.info(f"🔄 Sürücü {slave_id}: Reset atılıyor")
            
            result = self.client.write_register(self.CONTROL_REGISTER, self.CMD_RESET, unit=slave_id)
            if not result.isError():
                self.logger.info(f"✅ Sürücü {slave_id}: Reset tamamlandı")
                time.sleep(0.5)  # Reset sonrası bekleme
                return True
            else:
                self.logger.error(f"❌ Reset register yazma hatası: {result}")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Reset hatası: {e}")
            self._handle_connection_error()
            return False
    
    def clear_fault(self, slave_id):
        """Arıza durumunu temizle - GA500 için arıza reset"""
        try:
            self.logger.info(f"🔧 Sürücü {slave_id}: Arıza temizleniyor...")
            
            # Önce reset gönder
            reset_result = self.client.write_register(self.CONTROL_REGISTER, self.CMD_RESET, unit=slave_id)
            if reset_result.isError():
                self.logger.error(f"❌ Arıza reset hatası: {reset_result}")
                self._handle_connection_error()
                return False
            
            time.sleep(0.5)  # Reset sonrası bekleme
            
            # Arıza durumunu kontrol et
            status_result = self.client.read_holding_registers(address=self.STATUS_REGISTER, count=1, unit=slave_id)
            if not status_result.isError():
                status = status_result.registers[0]
                fault_bit = status & 0x8  # Bit 3: Arıza durumu
                
                if fault_bit == 0:
                    self.logger.info(f"✅ Sürücü {slave_id}: Arıza temizlendi")
                    return True
                else:
                    self.logger.warning(f"⚠️ Sürücü {slave_id}: Arıza hala mevcut, tekrar deneyiniz")
                    return False
            else:
                self.logger.error(f"❌ Durum okuma hatası: {status_result}")
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
            with self.lock:
                # GUI kodundaki gibi register okuma
                r1 = self.client.read_holding_registers(address=self.MON_BASE, count=5, unit=slave_id)
                r2 = self.client.read_holding_registers(address=self.DCBUS_REG, count=1, unit=slave_id)
                r3 = self.client.read_holding_registers(address=self.STATUS_REGISTER, count=1, unit=slave_id)
                r4 = self.client.read_holding_registers(address=self.TEMP_REG, count=1, unit=slave_id)
            
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
                self.logger.error(f"❌ Register okuma hatası - Slave {slave_id}")
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
        
        while not self.stop_reading and self.is_connected:
            try:
                success = True
                for slave_id in [1, 2]:
                    if self.stop_reading:
                        break
                        
                    # Status registerlerini oku
                    status = self.read_status_registers(slave_id)
                    
                    # Eğer boş data dönerse (hata durumu)
                    if not status:
                        success = False
                        break
                    
                    # Thread-safe veri güncelleme
                    with self.lock:
                        self.status_data[slave_id] = status
                    
                    # Konsola yazdır
                    self.print_status(slave_id, status)
                
                if success:
                    consecutive_errors = 0  # Başarılı okuma, error sayacını sıfırla
                else:
                    consecutive_errors += 1
                    self.logger.warning(f"⚠️ Okuma hatası #{consecutive_errors}")
                    
                    # Çok fazla ardışık hata varsa yeniden bağlan
                    if consecutive_errors >= max_errors:
                        self.logger.error(f"❌ {max_errors} ardışık okuma hatası, yeniden bağlanıyor...")
                        consecutive_errors = 0
                        self._handle_connection_error()
                
                # 0.5 saniye bekle
                time.sleep(0.1)
                
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
        """Status verilerini formatla ve yazdır"""
        if not status:
            return
            
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
        direction = "GERİ" if (drive_status & 0x0002) else "İLERİ"
        is_ready = (drive_status & 0x0004) != 0
        has_fault = (drive_status & 0x0008) != 0
        
        status_text = "ÇALIŞIYOR" if is_running else "DURUYOR"
        ready_text = "EVET" if is_ready else "HAYIR"
        fault_text = "VAR" if has_fault else "YOK"
        
        print(f"[Sürücü {slave_id}] Frekans Referansı: {freq_ref:.1f} Hz")
        print(f"[Sürücü {slave_id}] Çıkış Frekansı: {freq_out:.1f} Hz")
        print(f"[Sürücü {slave_id}] Çıkış Gerilimi: {voltage:.1f} V")
        print(f"[Sürücü {slave_id}] Çıkış Akımı: {current:.1f} A")
        print(f"[Sürücü {slave_id}] Çıkış Gücü: {power}")
        print(f"[Sürücü {slave_id}] DC Bus Voltajı: {dc_voltage} V")
        print(f"[Sürücü {slave_id}] Sıcaklık: {temperature} °C")
        print(f"[Sürücü {slave_id}] ▶ Durum: {status_text}, Yön: {direction}, Hazır: {ready_text}, Arıza: {fault_text}")
        print("─" * 50)
    
    def start_continuous_reading(self):
        """Sürekli okuma thread'ini başlat"""
        if self.reading_thread is not None and self.reading_thread.is_alive():
            self.logger.warning("⚠️ Okuma thread'i zaten çalışıyor")
            return
        
        self.stop_reading = False
        self.reading_thread = threading.Thread(target=self.continuous_reading_worker, daemon=True)
        self.reading_thread.start()
        self.logger.info("📊 Sürekli okuma thread'i başlatıldı")
    
    def stop_continuous_reading(self):
        """Sürekli okuma thread'ini durdur"""
        self.stop_reading = True
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=2)
        self.logger.info("⏹️ Sürekli okuma thread'i durduruldu")
