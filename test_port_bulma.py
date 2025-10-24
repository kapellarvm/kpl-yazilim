#!/usr/bin/env python3
"""
Port bulma testi - USB reset mekanizmasını test eder
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import log_system, log_success, log_error

def test_port_bulma():
    """Port bulma ve USB reset mekanizmasını test et"""
    print("\n" + "="*60)
    print("PORT BULMA TESTİ")
    print("="*60 + "\n")
    
    yonetici = KartHaberlesmeServis()
    
    # Test 1: Normal bağlantı
    print("TEST 1: Normal bağlantı denemesi")
    basarili, mesaj, portlar = yonetici.baglan(
        try_usb_reset=True, 
        max_retries=2, 
        kritik_kartlar=["motor", "sensor"]
    )
    
    print(f"\nSONUÇ:")
    print(f"  Başarılı: {basarili}")
    print(f"  Mesaj: {mesaj}")
    print(f"  Bulunan portlar: {portlar}")
    
    if not basarili:
        print("\n⚠️  Port bulunamadı! USB reset mekanizması çalışmadı.")
    else:
        print("\n✅ Portlar başarıyla bulundu!")
        
    print("\n" + "="*60)

if __name__ == "__main__":
    test_port_bulma()
