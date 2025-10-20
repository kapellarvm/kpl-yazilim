#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPS İzleme Servisi
Modbus timestamp parametresini izleyerek UPS durumunu tespit eder
"""

import asyncio
import time
import threading
from typing import Optional, Callable
from ...utils.logger import log_system, log_error, log_warning
from ...makine.senaryolar import oturum_var
from ...api.servisler.dimdb_servis import DimdbServis


class UPSMonitoringServis:
    """UPS durumunu izleyen servis sınıfı"""
    
    def __init__(self, modbus_client=None, timeout_seconds: float = 3.0):
        """
        UPS izleme servisini başlat
        Args:
            modbus_client: GA500ModbusClient instance
            timeout_seconds: Timestamp yanıt vermeme süresi (saniye)
        """
        self.modbus_client = modbus_client
        self.timeout_seconds = timeout_seconds
        self.is_running = False
        self.monitoring_task = None
        self.last_timestamp = None
        self.ups_connected = True
        self.power_failure_detected = False
        self.session_ended_due_to_power_failure = False
        
        # Callback fonksiyonları
        self.power_failure_callback: Optional[Callable] = None
        self.power_restored_callback: Optional[Callable] = None
        
        # Thread-safe lock
        self.lock = threading.Lock()
        
    def set_callbacks(self, power_failure_callback: Callable = None, 
                     power_restored_callback: Callable = None):
        """Callback fonksiyonlarını ayarla"""
        self.power_failure_callback = power_failure_callback
        self.power_restored_callback = power_restored_callback
    
    async def start_monitoring(self):
        """UPS izlemeyi başlat"""
        if self.is_running:
            log_warning("UPS izleme zaten çalışıyor")
            return
            
        # Modbus client yoksa da başlat (test için)
        if not self.modbus_client:
            log_warning("Modbus client bulunamadı, UPS izleme test modunda başlatılıyor")
            
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        log_system("UPS izleme servisi başlatıldı")
    
    async def stop_monitoring(self):
        """UPS izlemeyi durdur"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        log_system("UPS izleme servisi durduruldu")
    
    async def _monitoring_loop(self):
        """Ana izleme döngüsü"""
        consecutive_timeouts = 0
        max_consecutive_timeouts = 3  # 3 ardışık timeout sonrası kesinti tespit et (3 saniye)
        
        while self.is_running:
            try:
                # Modbus client yoksa test modunda çalış
                if not self.modbus_client or not self.modbus_client.is_connected:
                    # Test modunda - her 3 saniyede bir kesinti simüle et
                    consecutive_timeouts += 1
                    print(f"⚠️  [UPS İZLEME] Test modu - Timeout ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    log_warning(f"UPS test modu timeout ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        # Test kesintisi tespit edildi
                        with self.lock:
                            if not self.power_failure_detected:
                                self.power_failure_detected = True
                                self.ups_connected = False
                                print(f"⚡ [UPS İZLEME] TEST GÜÇ KESİNTİSİ TESPİT EDİLDİ!")
                                log_error("⚡ UPS TEST GÜÇ KESİNTİSİ TESPİT EDİLDİ!")
                                
                                if self.power_failure_callback:
                                    try:
                                        await self.power_failure_callback()
                                    except Exception as e:
                                        log_error(f"Power failure callback hatası: {e}")
                    
                    # 1 saniye bekle (test için)
                    await asyncio.sleep(1.0)
                    continue
                
                # Timestamp kontrolü yap
                current_timestamp = self._get_current_timestamp()
                
                if current_timestamp is not None:
                    # Timestamp alındı, UPS bağlı
                    with self.lock:
                        if not self.ups_connected:
                            # Güç geri geldi
                            self.ups_connected = True
                            self.power_failure_detected = False
                            self.session_ended_due_to_power_failure = False
                            print(f"🔌 [UPS İZLEME] Güç geri geldi - UPS normal çalışıyor")
                            log_system("🔌 UPS güç geri geldi")
                            
                            if self.power_restored_callback:
                                try:
                                    await self.power_restored_callback()
                                except Exception as e:
                                    log_error(f"Power restored callback hatası: {e}")
                    
                    self.last_timestamp = current_timestamp
                    consecutive_timeouts = 0
                    
                else:
                    # Timestamp alınamadı, timeout
                    consecutive_timeouts += 1
                    print(f"⚠️  [UPS İZLEME] Timestamp timeout ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    log_warning(f"UPS timestamp timeout ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        # UPS kesintisi tespit edildi
                        with self.lock:
                            if not self.power_failure_detected:
                                self.power_failure_detected = True
                                self.ups_connected = False
                                print(f"⚡ [UPS İZLEME] GÜÇ KESİNTİSİ TESPİT EDİLDİ!")
                                log_error("⚡ UPS GÜÇ KESİNTİSİ TESPİT EDİLDİ!")
                                
                                if self.power_failure_callback:
                                    try:
                                        await self.power_failure_callback()
                                    except Exception as e:
                                        log_error(f"Power failure callback hatası: {e}")
                
                # 1 saniye bekle
                await asyncio.sleep(1.0)
                
            except Exception as e:
                log_error(f"UPS izleme hatası: {e}")
                await asyncio.sleep(2.0)
    
    def _get_current_timestamp(self) -> Optional[float]:
        """Mevcut timestamp'i al - Modbus register'ından"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return None
                
            # Modbus client'tan status register'larını oku
            # Bu, UPS'in çalışıp çalışmadığını anlamak için yeterli
            status_data = self.modbus_client.read_status_registers(1)  # Slave ID 1
            
            if status_data and len(status_data) > 0:
                # Herhangi bir veri alındıysa UPS çalışıyor demektir
                return time.time()
            else:
                # Veri alınamadıysa UPS kesintisi olabilir
                return None
            
        except Exception as e:
            log_error(f"Timestamp alma hatası: {e}")
            return None
    
    def get_status(self) -> dict:
        """UPS servis durumunu döndürür"""
        with self.lock:
            return {
                "is_running": self.is_running,
                "ups_connected": self.ups_connected,
                "power_failure_detected": self.power_failure_detected,
                "session_ended_due_to_power_failure": self.session_ended_due_to_power_failure,
                "last_timestamp": self.last_timestamp,
                "timeout_seconds": self.timeout_seconds
            }


# Global UPS monitoring servis instance
ups_monitoring_servis = UPSMonitoringServis()
