import sys
import os

# Add the parent directory to the path to import seri_deneme
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'seri'))

from seri_deneme import main as seri_deneme_main

def oturum_var_main():
    """
    Oturum var senaryosu - seri_deneme.py'daki main fonksiyonunu çağırır
    """
    print("🔄 Oturum var senaryosu başlatılıyor...")
    print("📡 Seri deneme modülü çağrılıyor...")
    
    try:
        # seri_deneme.py'daki main fonksiyonunu çağır
        seri_deneme_main()
    except Exception as e:
        print(f"❌ Hata oluştu: {e}")

if __name__ == "__main__":
    oturum_var_main()
