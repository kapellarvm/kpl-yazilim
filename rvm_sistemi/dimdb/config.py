"""
RVM Konfigürasyon Yönetimi
Bu dosya RVM'ye özel konfigürasyon değerlerini yönetir.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class RVMConfig:
    """RVM konfigürasyon sınıfı"""
    
    def __init__(self):
        # Environment variables'dan değerleri al, yoksa varsayılan değerleri kullan
        self.SECRET_KEY = os.getenv('RVM_SECRET_KEY', 'testkpl')
        self.RVM_ID = os.getenv('RVM_ID', 'KRVM00010725')
        self.BASE_URL = os.getenv('RVM_BASE_URL', 'http://192.168.53.1:5432')
        
        # Konfigürasyon doğrulama
        self._validate_config()
    
    def _validate_config(self):
        """Konfigürasyon değerlerini doğrular"""
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY boş olamaz")
        if not self.RVM_ID:
            raise ValueError("RVM_ID boş olamaz")
        if not self.BASE_URL:
            raise ValueError("BASE_URL boş olamaz")
    
    def get_config_dict(self) -> dict:
        """Konfigürasyonu dictionary olarak döndürür"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'RVM_ID': self.RVM_ID,
            'BASE_URL': self.BASE_URL
        }

# Global konfigürasyon instance'ı
config = RVMConfig()
