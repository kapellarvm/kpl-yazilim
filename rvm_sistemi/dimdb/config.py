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
        # .env dosyasının varlığını kontrol et
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if not os.path.exists(env_file_path):
            self._print_setup_instructions()
            raise ValueError("Konfigürasyon dosyası bulunamadı")
        
        if not self.SECRET_KEY:
            self._print_setup_instructions()
            raise ValueError("SECRET_KEY boş olamaz")
        if not self.RVM_ID:
            self._print_setup_instructions()
            raise ValueError("RVM_ID boş olamaz")
        if not self.BASE_URL:
            self._print_setup_instructions()
            raise ValueError("BASE_URL boş olamaz")
    
    def _print_setup_instructions(self):
        """Kurulum talimatlarını terminale yazdırır"""
        print("\n" + "="*60)
        print("🚨 RVM KONFIGÜRASYON HATASI!")
        print("="*60)
        print("❌ Konfigürasyon dosyası bulunamadı veya eksik değerler var.")
        print("\n📋 KURULUM TALİMATLARI:")
        print("1️⃣  Örnek konfigürasyon dosyasını kopyalayın:")
        print("    cp .env.example .env")
        print("\n2️⃣  .env dosyasını düzenleyin:")
        print("    nano .env")
        print("\n3️⃣  Aşağıdaki değerleri girin:")
        print("    RVM_ID=KRVM00010725          # RVM'nizin benzersiz kimliği")
        print("    RVM_SECRET_KEY=your_key      # Güvenlik anahtarı")
        print("    RVM_BASE_URL=http://192.168.53.1:5432  # DİM-DB sunucu adresi")
        print("\n4️⃣  Sistemi yeniden başlatın")
        print("\n💡 Her RVM için farklı RVM_ID kullanın!")
        print("="*60)
    
    def get_config_dict(self) -> dict:
        """Konfigürasyonu dictionary olarak döndürür"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'RVM_ID': self.RVM_ID,
            'BASE_URL': self.BASE_URL
        }

# Global konfigürasyon instance'ı
config = RVMConfig()
