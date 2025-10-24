"""
RVM Konfigürasyon Yönetimi
Bu dosya RVM'ye özel konfigürasyon değerlerini yönetir.
"""
import os
from typing import Optional
from dotenv import load_dotenv

class RVMConfig:
    """RVM konfigürasyon sınıfı"""
    
    def __init__(self):
        # .env dosyasının varlığını kontrol et
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        
        if not os.path.exists(env_file_path):
            self._interactive_setup()
        else:
            # .env dosyası varsa yükle
            load_dotenv()
            self.SECRET_KEY = os.getenv('RVM_SECRET_KEY', 'null')
            self.RVM_ID = os.getenv('RVM_ID', '')
            self.BASE_URL = os.getenv('RVM_BASE_URL', 'http://192.168.53.1:5432')
            self.MAKINE_SINIFI = os.getenv('RVM_MAKINE_SINIFI', '')
            
            # Eğer RVM_ID veya MAKINE_SINIFI boşsa tekrar kurulum yap
            if not self.RVM_ID or not self.MAKINE_SINIFI:
                self._interactive_setup()
    
    def _interactive_setup(self):
        """İnteraktif kurulum süreci"""
        self._print_header()
        self._print_welcome()
        
        # RVM ID girişi
        self.RVM_ID = self._get_rvm_id()
        
        # Makine sınıfı seçimi
        self.MAKINE_SINIFI = self._get_makine_sinifi()
        
        # Kurulum onayı
        self._confirm_setup()
        
        # Kurulumu tamamla
        self._complete_setup()
    
    def _print_header(self):
        """Kurulum başlığını yazdırır"""
        print("\n" + "="*60)
        print("🚀 RVM KURULUM SİSTEMİ")
        print("="*60)
    
    def _print_welcome(self):
        """Hoş geldin mesajını yazdırır"""
        print("\n📋 KURULUM BAŞLATILIYOR")
        print("─" * 30)
        print("Lütfen kurulum yapınız!")
        print("─" * 30)
        print()
    
    def _get_rvm_id(self):
        """RVM ID girişi ve doğrulama"""
        while True:
            print("\n🔑 RVM ID GİRİŞİ")
            print("─" * 20)
            
            rvm_id = input("\n💻 RVM ID kodunu giriniz: ").strip()
            
            if not rvm_id:
                print("\n❌ RVM ID boş olamaz!")
                print("🔄 Lütfen tekrar deneyin...\n")
                continue
            
            print(f"\n📝 Girdiğiniz kod: {rvm_id}")
            print("─" * 30)
            
            while True:
                confirm = input("✅ Doğru mu? (y/n): ").strip().lower()
                if confirm == 'y':
                    print(f"\n🎯 RVM ID onaylandı: {rvm_id}")
                    print("─" * 30)
                    return rvm_id
                elif confirm == 'n':
                    print("\n🔄 Yeni RVM ID giriniz...\n")
                    break
                else:
                    print("⚠️  Lütfen 'y' veya 'n' giriniz!")
    
    def _get_makine_sinifi(self):
        """Makine sınıfı seçimi ve doğrulama"""
        while True:
            print("\n🏭 MAKİNE SINIFI SEÇİMİ")
            print("─" * 25)
            print("\n1️⃣  KPL-04 (CAM KIRICI VAR)")
            print("2️⃣  KPL-05 (CAM KIRICI YOK)")
            print("─" * 25)
            
            secim = input("\n💻 Makine sınıfını seçiniz (1 veya 2): ").strip()
            
            if secim == "1":
                makine_sinifi = "KPL-04"
                print(f"\n📝 Seçilen makine sınıfı: {makine_sinifi} (CAM KIRICI VAR)")
                print("─" * 40)
                
                while True:
                    confirm = input("✅ Doğru mu? (y/n): ").strip().lower()
                    if confirm == 'y':
                        print(f"\n🎯 Makine sınıfı onaylandı: {makine_sinifi}")
                        print("─" * 40)
                        return makine_sinifi
                    elif confirm == 'n':
                        print("\n🔄 Yeni makine sınıfı seçiniz...\n")
                        break
                    else:
                        print("⚠️  Lütfen 'y' veya 'n' giriniz!")
                        
            elif secim == "2":
                makine_sinifi = "KPL-05"
                print(f"\n📝 Seçilen makine sınıfı: {makine_sinifi} (CAM KIRICI YOK)")
                print("─" * 40)
                
                while True:
                    confirm = input("✅ Doğru mu? (y/n): ").strip().lower()
                    if confirm == 'y':
                        print(f"\n🎯 Makine sınıfı onaylandı: {makine_sinifi}")
                        print("─" * 40)
                        return makine_sinifi
                    elif confirm == 'n':
                        print("\n🔄 Yeni makine sınıfı seçiniz...\n")
                        break
                    else:
                        print("⚠️  Lütfen 'y' veya 'n' giriniz!")
            else:
                print("\n❌ Geçersiz seçim! Lütfen 1 veya 2 giriniz.")
                print("🔄 Tekrar deneyin...\n")
    
    def _confirm_setup(self):
        """Kurulum onayı"""
        print("\n📋 KURULUM ÖZETİ")
        print("─" * 20)
        print(f"\n🏷️  RVM ID: {self.RVM_ID}")
        print(f"🏭 MAKİNE SINIFI: {self.MAKINE_SINIFI}")
        print("🔐 SECRET KEY: null")
        print("🌐 BASE URL: http://192.168.53.1:5432")
        print("\n─" * 3)
        
        while True:
            confirm_setup = input("🚀 Kurulumu tamamlamak istiyor musunuz? (y/n): ").strip().lower()
            if confirm_setup == 'y':
                print("─" * 30)
                break
            elif confirm_setup == 'n':
                print("\n❌ Kurulum iptal edildi!")
                print("👋 Çıkılıyor...")
                exit(1)
            else:
                print("⚠️  Lütfen 'y' veya 'n' giriniz!")
    
    def _complete_setup(self):
        """Kurulumu tamamlar"""
        print("\n⚙️  KURULUM YAPILIYOR")
        print("─" * 25)
        
        # Dosya oluşturma animasyonu
        print("\n📁 .env dosyası oluşturuluyor...")
        import time
        time.sleep(0.5)
        print("🔧 Konfigürasyon ayarlanıyor...")
        time.sleep(0.5)
        print("💾 Değerler kaydediliyor...")
        time.sleep(0.5)
        
        self._create_env_file()
        
        print("\n" + "="*60)
        print("✅ KURULUM TAMAMLANDI!")
        print("="*60)
        
        print(f"\n🎯 RVM ID: {self.RVM_ID}")
        print(f"🏭 MAKİNE SINIFI: {self.MAKINE_SINIFI}")
        print("📁 Konfigürasyon dosyası: .env")
        print("🚀 Sistem başlatılıyor...")
        print("\n─" * 3)
        print("🎉 Hoş geldiniz! RVM sistemi hazır.")
        print("─" * 30)
        print("="*60)
    
    def _create_env_file(self):
        """Konfigürasyon dosyasını oluşturur"""
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        
        # Varsayılan değerler
        self.SECRET_KEY = 'null'
        self.BASE_URL = 'http://192.168.53.1:5432'
        
        # .env dosyasını oluştur
        content = f"""# RVM Konfigürasyonu
# Bu dosya otomatik oluşturulmuştur

RVM_ID={self.RVM_ID}
RVM_MAKINE_SINIFI={self.MAKINE_SINIFI}
RVM_SECRET_KEY={self.SECRET_KEY}
RVM_BASE_URL={self.BASE_URL}
"""
        
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Environment variables'ları yükle
        load_dotenv()
    
    def get_config_dict(self) -> dict:
        """Konfigürasyonu dictionary olarak döndürür"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'RVM_ID': self.RVM_ID,
            'MAKINE_SINIFI': self.MAKINE_SINIFI,
            'BASE_URL': self.BASE_URL
        }

# Global konfigürasyon instance'ı
config = RVMConfig()
