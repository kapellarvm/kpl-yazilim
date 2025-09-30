#!/usr/bin/env python3
"""
Hızlı sistem testi için basit script
"""
import sys
import os

# Projeyi Python yoluna ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test fonksiyonlarını import et
try:
    from rvm_sistemi.makine.senaryolar.oturum_var import test_sistem_durumu, sistem_durumunu_sifirla
    
    print("═" * 80)
    print("🔧 RVM Sistem Hızlı Test")
    print("═" * 80)
    
    # Sistem durumunu kontrol et
    test_sistem_durumu()
    
    print("\n" + "─" * 80)
    print("🛠️ Kullanılabilir Komutlar:")
    print("python3 hizli_test.py reset     - Sistemi sıfırla")
    print("python3 hizli_test.py durum     - Durum kontrolü")
    print("─" * 80)
    
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) > 1:
        komut = sys.argv[1].lower()
        
        if komut == "reset":
            print("\n🔄 Sistem sıfırlanıyor...")
            sistem_durumunu_sifirla()
            print("✅ Sistem sıfırlandı!")
            
        elif komut == "durum":
            print("\n📊 Detaylı durum kontrolü:")
            test_sistem_durumu()
            
        else:
            print(f"\n❌ Bilinmeyen komut: {komut}")
            
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    print("🔧 Lütfen önce projeyi düzgün kurduğunuzdan emin olun.")