#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPS İzleme Servisi - DEPRECATED
Artık voltage_power_monitoring.py kullanılıyor
Bu dosya geriye dönük uyumluluk için korunuyor
"""

import asyncio
import time
import threading
from typing import Optional, Callable
from ...utils.logger import log_system, log_error, log_warning
from ...utils.terminal import status, warn, ok
from ...makine.senaryolar import oturum_var
from ...api.servisler.dimdb_servis import DimdbServis
from .voltage_power_monitoring import voltage_power_monitoring_servis


class UPSMonitoringServis:
    """UPS durumunu izleyen servis sınıfı - DEPRECATED
    
    Bu sınıf artık voltage_power_monitoring_servis'i kullanıyor.
    Geriye dönük uyumluluk için korunuyor.
    """
    
    def __init__(self, modbus_client=None, timeout_seconds: float = 3.0):
        """
        UPS izleme servisini başlat - DEPRECATED
        Artık voltage_power_monitoring_servis kullanılıyor
        """
        log_warning("UPSMonitoringServis DEPRECATED - voltage_power_monitoring_servis kullanın")
        
        # Voltage monitoring servisini kullan
        self.voltage_servis = voltage_power_monitoring_servis
        self.voltage_servis.modbus_client = modbus_client
        
        # Geriye dönük uyumluluk için eski property'ler
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
        """Callback fonksiyonlarını ayarla - DEPRECATED"""
        self.power_failure_callback = power_failure_callback
        self.power_restored_callback = power_restored_callback
        
        # Voltage servisine de callback'leri aktar
        self.voltage_servis.set_callbacks(power_failure_callback, power_restored_callback)
    
    async def start_monitoring(self):
        """UPS izlemeyi başlat - DEPRECATED"""
        log_warning("UPSMonitoringServis.start_monitoring() DEPRECATED - voltage_power_monitoring_servis kullanın")
        
        # Voltage monitoring servisini başlat
        await self.voltage_servis.start_monitoring()
        
        # Geriye dönük uyumluluk için eski property'leri güncelle
        self.is_running = self.voltage_servis.is_running
        log_system("UPS izleme servisi başlatıldı (voltage monitoring ile)")
    
    async def stop_monitoring(self):
        """UPS izlemeyi durdur - DEPRECATED"""
        log_warning("UPSMonitoringServis.stop_monitoring() DEPRECATED - voltage_power_monitoring_servis kullanın")
        
        # Voltage monitoring servisini durdur
        await self.voltage_servis.stop_monitoring()
        
        # Geriye dönük uyumluluk için eski property'leri güncelle
        self.is_running = self.voltage_servis.is_running
        log_system("UPS izleme servisi durduruldu (voltage monitoring ile)")
    
    def get_status(self) -> dict:
        """UPS servis durumunu döndürür - DEPRECATED"""
        # Voltage servisinden durumu al
        voltage_status = self.voltage_servis.get_status()
        
        # Geriye dönük uyumluluk için eski format
        return {
            "is_running": voltage_status["is_running"],
            "ups_connected": voltage_status["power_connected"],
            "power_failure_detected": voltage_status["power_failure_detected"],
            "session_ended_due_to_power_failure": voltage_status["session_ended_due_to_power_failure"],
            "last_timestamp": voltage_status["last_voltage"],  # Voltage değeri timestamp olarak
            "timeout_seconds": self.timeout_seconds,
            "voltage_threshold": voltage_status["voltage_threshold"],
            "last_voltage": voltage_status["last_voltage"]
        }


# Global UPS monitoring servis instance
ups_monitoring_servis = UPSMonitoringServis()
