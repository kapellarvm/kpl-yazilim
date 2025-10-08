#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus Veri Parser
GA500 Modbus verilerini parse edip bakım ekranına gönderir
"""

import json
import re
from typing import Dict, Optional, Any

class ModbusParser:
    """Modbus verilerini parse eden sınıf"""
    
    def __init__(self):
        self.parsed_data = {
            's1': {},  # Ezici motor (ID: 1)
            's2': {}   # Kırıcı motor (ID: 2)
        }
    
    def parse_modbus_string(self, modbus_string: str) -> Optional[Dict[str, Any]]:
        """
        Modbus string'ini parse eder
        Format: "s1:freq_ref:25.0,freq_out:24.8,current:2.1,status:ÇALIŞIYOR"
        """
        try:
            # Regex ile veriyi parse et
            pattern = r's(\d+):(.+)'
            match = re.match(pattern, modbus_string)
            
            if not match:
                return None
            
            slave_id = int(match.group(1))
            data_string = match.group(2)
            
            # Veri çiftlerini parse et
            data_pairs = data_string.split(',')
            parsed_data = {}
            
            for pair in data_pairs:
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    
                    # Sayısal değerleri dönüştür
                    if key in ['freq_ref', 'freq_out', 'voltage', 'current', 'power', 'dc_voltage', 'temperature']:
                        try:
                            parsed_data[key] = float(value)
                        except ValueError:
                            parsed_data[key] = 0.0
                    else:
                        # String değerler
                        parsed_data[key] = value
            
            # Slave ID'ye göre sakla
            motor_key = f's{slave_id}'
            self.parsed_data[motor_key] = parsed_data
            
            return {
                'motor_id': slave_id,
                'motor_key': motor_key,
                'data': parsed_data
            }
            
        except Exception as e:
            print(f"Modbus parse hatası: {e}")
            return None
    
    def get_motor_data(self, motor_id: int) -> Dict[str, Any]:
        """Belirli motor ID'si için veri döndürür"""
        motor_key = f's{motor_id}'
        return self.parsed_data.get(motor_key, {})
    
    def get_all_data(self) -> Dict[str, Any]:
        """Tüm motor verilerini döndürür"""
        return self.parsed_data
    
    def get_crusher_data(self) -> Dict[str, Any]:
        """Ezici motor (s1) verilerini döndürür"""
        return self.parsed_data.get('s1', {})
    
    def get_breaker_data(self) -> Dict[str, Any]:
        """Kırıcı motor (s2) verilerini döndürür"""
        return self.parsed_data.get('s2', {})
    
    def format_for_display(self, motor_data: Dict[str, Any]) -> Dict[str, str]:
        """Veriyi ekran gösterimi için formatlar"""
        if not motor_data:
            return {}
        
        formatted = {}
        
        # Frekans değerleri
        formatted['set_freq'] = f"{motor_data.get('freq_ref', 0):.1f} Hz"
        formatted['out_freq'] = f"{motor_data.get('freq_out', 0):.1f} Hz"
        
        # Elektriksel değerler
        formatted['voltage'] = f"{motor_data.get('voltage', 0):.1f} V"
        formatted['current'] = f"{motor_data.get('current', 0):.1f} A"
        formatted['power'] = f"{motor_data.get('power', 0):.1f} W"
        formatted['bus_voltage'] = f"{motor_data.get('dc_voltage', 0):.1f} V"
        
        # Sıcaklık
        formatted['temperature'] = f"{motor_data.get('temperature', 0):.1f} °C"
        
        # Durum bilgileri
        formatted['status'] = motor_data.get('status', 'DURUYOR')
        formatted['direction'] = motor_data.get('direction', 'DURUYOR')
        formatted['ready'] = motor_data.get('ready', 'HAYIR')
        formatted['fault'] = motor_data.get('fault', 'YOK')
        
        return formatted
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Motor durumlarının özetini döndürür"""
        crusher = self.get_crusher_data()
        breaker = self.get_breaker_data()
        
        return {
            'crusher': {
                'running': crusher.get('status') == 'ÇALIŞIYOR',
                'ready': crusher.get('ready') == 'EVET',
                'fault': crusher.get('fault') == 'VAR',
                'current': crusher.get('current', 0),
                'temperature': crusher.get('temperature', 0)
            },
            'breaker': {
                'running': breaker.get('status') == 'ÇALIŞIYOR',
                'ready': breaker.get('ready') == 'EVET',
                'fault': breaker.get('fault') == 'VAR',
                'current': breaker.get('current', 0),
                'temperature': breaker.get('temperature', 0)
            }
        }

# Global parser instance
modbus_parser = ModbusParser()
