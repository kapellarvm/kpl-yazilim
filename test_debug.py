#!/usr/bin/env python3
"""
Test script for debugging the RVM system deadlock issue
"""

# Bu script'i test ederken kullanın
from rvm_sistemi.makine.senaryolar.oturum_var import *

def test_deadlock_scenario():
    """Deadlock senaryosunu simüle eder"""
    print("🧪 [TEST] Deadlock senaryosu başlıyor...")
    
    # 1. Normal başlangıç
    print("\n=== 1. Normal başlangıç ===")
    sistem_durumu_goster()
    
    # 2. Barkod geldi ama diğer veriler gelmedi
    print("\n=== 2. Sadece barkod gönder ===")
    barkod_verisi_al("TEST123")
    
    # 3. Sistem durumunu kontrol et
    print("\n=== 3. Durum kontrolü ===")
    sistem_durumu_goster()
    
    # 4. 11 saniye sonra timeout tetikle
    print("\n=== 4. Timeout simülasyonu ===")
    import time
    global son_aktivite_zamani
    son_aktivite_zamani = time.time() - 11  # 11 saniye önce ayarla
    timeout_kontrol()
    
    # 5. Zorla sıfırlama test et
    print("\n=== 5. Zorla sıfırlama testi ===")
    zorla_sistem_sifirla()
    
    # 6. Yeni barkod gönder
    print("\n=== 6. Yeni barkod testi ===")
    barkod_verisi_al("TEST456")

if __name__ == "__main__":
    test_deadlock_scenario()