"""
GA500 Modbus Modülü
Ubuntu ortamında çalışan GA500 sürücü kontrol modülü
"""

from .modbus_istemci import GA500ModbusClient

__all__ = ['GA500ModbusClient']