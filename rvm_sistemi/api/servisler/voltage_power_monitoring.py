#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voltage Power Monitoring Servisi
Modbus bus_voltage verisini izleyerek elektrik kesintisi tespit eder
"""

import asyncio
import time
import threading
from typing import Optional, Callable
from ...utils.logger import log_system, log_error, log_warning
from ...utils.terminal import status, warn, ok
from ...makine.senaryolar import oturum_var
from ...api.servisler.dimdb_servis import DimdbServis


class VoltagePowerMonitoringServis:
    """Voltage tabanlı elektrik kesintisi izleme servisi"""
    
    def __init__(self, modbus_client=None, voltage_threshold: float = 300.0):
        """
        Voltage monitoring servisini başlat
        Args:
            modbus_client: GA500ModbusClient instance
            voltage_threshold: Elektrik kesintisi tespit eşiği (Volt) - varsayılan 300V
        """
        self.modbus_client = modbus_client
        self.voltage_threshold = voltage_threshold
        self.is_running = False
        self.monitoring_task = None
        self.last_voltage = None
        self.power_connected = True
        self.power_failure_detected = False
        self.session_ended_due_to_power_failure = False
        
        # Callback fonksiyonları
        self.power_failure_callback: Optional[Callable] = None
        self.power_restored_callback: Optional[Callable] = None
        
        # Thread-safe lock
        self.lock = threading.Lock()
        
        # Voltage okuma geçmişi (hysteresis için)
        self.voltage_history = []
        self.history_size = 5  # Son 5 okumayı sakla
        self.hysteresis_threshold = 50.0  # 50V hysteresis (300V altı kesinti, 350V üstü normal)
        
        # Başlangıç bypass mekanizması - basitleştirildi
        self.startup_bypass_active = True
        self.startup_bypass_duration = 5.0  # 5 saniye basit bypass
        self.startup_bypass_start_time = None
        
    def set_modbus_client(self, modbus_client):
        """Modbus client referansını ayarla"""
        self.modbus_client = modbus_client
        
    def set_callbacks(self, power_failure_callback: Callable = None, 
                     power_restored_callback: Callable = None):
        """Callback fonksiyonlarını ayarla"""
        self.power_failure_callback = power_failure_callback
        self.power_restored_callback = power_restored_callback
    
    async def start_monitoring(self):
        """Voltage monitoring'i başlat"""
        if self.is_running:
            log_warning("Voltage monitoring zaten çalışıyor")
            return
        
        # Modbus client yoksa da başlat (test için)
        if not self.modbus_client:
            log_warning("Modbus client bulunamadı, voltage monitoring test modunda başlatılıyor")
        
        # Başlangıç bypass'ını başlat
        self.startup_bypass_active = True
        self.startup_bypass_start_time = time.time()
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        log_system("Voltage power monitoring servisi başlatıldı")
    
    async def stop_monitoring(self):
        """Voltage monitoring'i durdur"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        log_system("Voltage power monitoring servisi durduruldu")
    
    def _check_startup_bypass(self) -> bool:
        """Başlangıç bypass kontrolü - True dönerse monitoring atlanır"""
        current_time = time.time()
        elapsed_time = current_time - self.startup_bypass_start_time
        
        # Basit zaman bazlı bypass kontrolü
        if elapsed_time < self.startup_bypass_duration:
            return True
        
        # Bypass tamamlandı
        self.startup_bypass_active = False
        log_system("Voltage monitoring başlangıç bypass tamamlandı")
        return False
    
    def _is_voltage_stable(self, voltage: float) -> bool:
        """Voltage değerinin stabil olup olmadığını kontrol et"""
        if voltage is None:
            return False
        
        # Voltage değeri makul aralıkta mı? (100V - 500V arası)
        if voltage < 100.0 or voltage > 500.0:
            return False
        
        # Geçmişteki değerlerle karşılaştır
        if len(self.voltage_history) < 3:
            return True  # Henüz yeterli geçmiş yok, stabil kabul et
        
        # Son 3 değerin ortalamasından çok farklı mı?
        recent_avg = sum(self.voltage_history[-3:]) / 3
        if abs(voltage - recent_avg) > 50.0:  # 50V'den fazla fark varsa stabil değil
            return False
        
        return True
    
    async def _monitoring_loop(self):
        """Ana voltage monitoring döngüsü"""
        consecutive_low_voltage = 0
        max_consecutive_low_voltage = 2  # 2 ardışık düşük voltaj sonrası kesinti tespit et (1 saniyede tespit)
        
        
        while self.is_running:
            # Başlangıç bypass kontrolü
            if self.startup_bypass_active:
                if self._check_startup_bypass():
                    await asyncio.sleep(0.5)  # Bypass sırasında 0.5 saniye bekle
                    continue
            try:
                # Modbus client yoksa sadece bekle
                if not self.modbus_client or not self.modbus_client.is_connected:
                    # Modbus bağlantısı yoksa sadece bekle
                    await asyncio.sleep(5.0)
                    continue
                
                # Bus voltage kontrolü yap
                current_voltage = self._get_bus_voltage()
                
                if current_voltage is not None:
                    # Voltage alındı, geçmişe ekle
                    self._add_voltage_to_history(current_voltage)
                    
                    # Güç geri geldi mi kontrol et (daha önce kesinti tespit edilmişse)
                    if self.power_failure_detected and current_voltage > self.voltage_threshold:
                        print(f"🔌 Güç geri geldi! Voltage: {current_voltage}V", flush=True)
                        with self.lock:
                            self.power_failure_detected = False
                            self.power_connected = True
                            
                            if self.power_restored_callback:
                                try:
                                    await self.power_restored_callback()
                                except Exception as e:
                                    log_error(f"Power restored callback hatası: {e}")
                        
                        print(f"✅ Güç geri geldi - sistem normale döndü", flush=True)
                        log_system("✅ Güç geri geldi - sistem normale döndü")
                    
                    # Bypass sırasında sadece voltage'ı kaydet
                    
                    # Hysteresis ile karar ver
                    voltage_status = self._evaluate_voltage_status()
                    
                    if voltage_status == "low":
                        # Düşük voltaj tespit edildi
                        consecutive_low_voltage += 1
                        warn("VOLTAGE MONITORING", f"Düşük voltaj: {current_voltage}V ({consecutive_low_voltage}/{max_consecutive_low_voltage})")
                        log_warning(f"Voltage düşük: {current_voltage}V ({consecutive_low_voltage}/{max_consecutive_low_voltage})")
                        
                        if consecutive_low_voltage >= max_consecutive_low_voltage:
                            # Elektrik kesintisi tespit edildi
                            with self.lock:
                                if not self.power_failure_detected:
                                    self.power_failure_detected = True
                                    self.power_connected = False
                                    status("VOLTAGE MONITORING", "ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!", level="err")
                                    log_error(f"⚡ VOLTAGE ELEKTRİK KESİNTİSİ TESPİT EDİLDİ! ({current_voltage}V)")
                                    
                                    if self.power_failure_callback:
                                        try:
                                            await self.power_failure_callback()
                                        except Exception as e:
                                            log_error(f"Power failure callback hatası: {e}")
                    
                    elif voltage_status == "normal":
                        # Normal voltaj - güç geri geldi
                        with self.lock:
                            if not self.power_connected:
                                # Güç geri geldi
                                self.power_connected = True
                                self.power_failure_detected = False
                                self.session_ended_due_to_power_failure = False
                                ok("VOLTAGE MONITORING", f"Güç geri geldi - Normal voltaj: {current_voltage}V")
                                log_system(f"🔌 Voltage güç geri geldi: {current_voltage}V")
                                
                                if self.power_restored_callback:
                                    try:
                                        await self.power_restored_callback()
                                    except Exception as e:
                                        log_error(f"Power restored callback hatası: {e}")
                        
                        consecutive_low_voltage = 0
                    
                    self.last_voltage = current_voltage
                    
                else:
                    # Voltage alınamadı, modbus hatası
                    consecutive_low_voltage += 1
                    warn("VOLTAGE MONITORING", f"Voltage okunamadı ({consecutive_low_voltage}/{max_consecutive_low_voltage})")
                    log_warning(f"Voltage okunamadı ({consecutive_low_voltage}/{max_consecutive_low_voltage})")
                    
                    if consecutive_low_voltage >= max_consecutive_low_voltage:
                        # Modbus hatası nedeniyle kesinti tespit edildi
                        with self.lock:
                            if not self.power_failure_detected:
                                self.power_failure_detected = True
                                self.power_connected = False
                                status("VOLTAGE MONITORING", "MODBUS HATASI - ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!", level="err")
                                log_error("⚡ VOLTAGE MODBUS HATASI - ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!")
                                
                                if self.power_failure_callback:
                                    try:
                                        await self.power_failure_callback()
                                    except Exception as e:
                                        log_error(f"Power failure callback hatası: {e}")
                
                # 0.5 saniye bekle (Modbus verisi yarım saniyede bir geliyor)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log_error(f"Voltage monitoring hatası: {e}")
                await asyncio.sleep(2.0)
    
    def _get_bus_voltage(self) -> Optional[float]:
        """Modbus'tan bus voltage değerini al"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return None
                
            # Modbus client'ın get_bus_voltage fonksiyonunu kullan
            voltage = self.modbus_client.get_bus_voltage(1)  # Slave ID 1
            return voltage
            
        except Exception as e:
            log_error(f"Bus voltage alma hatası: {e}")
            return None
    
    def _add_voltage_to_history(self, voltage: float):
        """Voltage değerini geçmişe ekle"""
        self.voltage_history.append(voltage)
        if len(self.voltage_history) > self.history_size:
            self.voltage_history.pop(0)
    
    def _evaluate_voltage_status(self) -> str:
        """Voltage geçmişine göre durumu değerlendir (hysteresis ile)"""
        if not self.voltage_history:
            return "unknown"
        
        # Son voltage değerini al
        current_voltage = self.voltage_history[-1]
        
        # Hysteresis mantığı
        if self.power_connected:
            # Şu anda güç bağlı - düşük voltaj eşiği
            if current_voltage <= self.voltage_threshold:
                return "low"
            else:
                return "normal"
        else:
            # Şu anda güç kesik - yüksek voltaj eşiği (hysteresis)
            if current_voltage >= (self.voltage_threshold + self.hysteresis_threshold):
                return "normal"
            else:
                return "low"
    
    def get_status(self) -> dict:
        """Voltage monitoring servis durumunu döndürür"""
        with self.lock:
            return {
                "is_running": self.is_running,
                "power_connected": self.power_connected,
                "power_failure_detected": self.power_failure_detected,
                "session_ended_due_to_power_failure": self.session_ended_due_to_power_failure,
                "last_voltage": self.last_voltage,
                "voltage_threshold": self.voltage_threshold,
                "voltage_history": self.voltage_history.copy(),
                "hysteresis_threshold": self.hysteresis_threshold,
                "startup_bypass_active": self.startup_bypass_active
            }


# Global voltage monitoring servis instance
voltage_power_monitoring_servis = VoltagePowerMonitoringServis()
