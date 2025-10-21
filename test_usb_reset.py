#!/usr/bin/env python3
"""
USB reset test scripti
"""
import subprocess
import time
import os

def test_usb_reset():
    """USB reset mekanizmasını test et"""
    print("USB RESET TEST BAŞLIYOR")
    print("="*50)
    
    # Mevcut portları göster
    print("\n1. MEVCUT PORTLAR:")
    result = subprocess.run(["ls", "-la", "/dev/ttyUSB*"], capture_output=True, text=True)
    print(result.stdout if result.returncode == 0 else "Port bulunamadı")
    
    # USB cihazlarını göster
    print("\n2. USB CİHAZLARI:")
    result = subprocess.run(["lsusb"], capture_output=True, text=True)
    ch340_lines = [line for line in result.stdout.split('\n') if 'CH340' in line]
    for line in ch340_lines:
        print(line)
    
    # USB reset scriptini çalıştır
    print("\n3. USB RESET ÇALIŞTIRILYOR...")
    script_path = "rvm_sistemi/makine/seri/usb_reset_all.sh"
    if os.path.exists(script_path):
        result = subprocess.run([f"echo 'kapellarvm' | sudo -S {script_path}"], 
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ USB reset başarılı!")
            # Sadece önemli satırları göster
            for line in result.stdout.split('\n'):
                if any(x in line for x in ['✅', '📊', 'port sayısı:', '/dev/ttyUSB']):
                    print(f"  {line}")
        else:
            print(f"❌ USB reset hatası: {result.stderr}")
    else:
        print(f"❌ Script bulunamadı: {script_path}")
    
    # Sonuç portları göster
    print("\n4. RESET SONRASI PORTLAR:")
    time.sleep(2)
    result = subprocess.run(["ls", "-la", "/dev/ttyUSB*"], capture_output=True, text=True)
    print(result.stdout if result.returncode == 0 else "Port bulunamadı")
    
    print("\n" + "="*50)
    print("TEST TAMAMLANDI")

if __name__ == "__main__":
    test_usb_reset()
