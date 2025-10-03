# Global değişken - bakım Chromium process'i
bakim_chromium_process = None

def olayi_isle(olay):
    print(f"[Bakım Modu] Gelen olay: {olay}")
    # Bakım modunda yapılacak işlemler buraya eklenebilir

def bakim_moduna_gir():
    """Bakım moduna girildiğinde çalışır - Yeni Chromium penceresi açar"""
    global bakim_chromium_process
    print("[Bakım Modu] Bakım moduna giriliyor...")
    
    try:
        import subprocess
        import os
        
        bakim_url = "http://192.168.53.2:4321/bakim"
        
        # Yeni Chromium penceresi aç (kioskuser olarak, kiosk modda)
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        # Chromium'u kiosk modunda aç - arka planda çalışsın
        print(f"[DEBUG] Chromium açma komutu çalıştırılıyor...")
        bakim_chromium_process = subprocess.Popen([
            "sudo", "-u", "kioskuser",
            "env", "DISPLAY=:0", "XAUTHORITY=/home/kioskuser/.Xauthority",
            "/snap/chromium/current/usr/lib/chromium-browser/chrome",
            "--kiosk",
            "--noerrdialogs",
            "--disable-pinch",
            "--overscroll-history-navigation=0",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--disable-cache",
            "--disk-cache-size=0",
            "--disable-application-cache",
            "--incognito",
            # Çeviri aracını devre dışı bırak
            "--disable-translate",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-logging",
            "--disable-gpu-logging",
            "--silent",
            "--no-first-run",
            "--no-default-browser-check",
            bakim_url
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Hemen hata kontrolü yap
        import time
        time.sleep(0.5)
        if bakim_chromium_process.poll() is not None:
            stdout, stderr = bakim_chromium_process.communicate()
            print(f"[ERROR] Chromium başlatılamadı! Exit code: {bakim_chromium_process.returncode}")
            print(f"[ERROR] STDOUT: {stdout.decode() if stdout else 'empty'}")
            print(f"[ERROR] STDERR: {stderr.decode() if stderr else 'empty'}")
        
        print(f"[Bakım Modu] Bakım Chromium açıldı (PID: {bakim_chromium_process.pid}): {bakim_url}")
    except Exception as e:
        print(f"[Bakım Modu] Bakım Chromium açma hatası: {e}")
        bakim_chromium_process = None

def bakim_modundan_cik():
    """Bakım modundan çıkılırken çalışır - Bakım Chromium'unu kapatır"""
    global bakim_chromium_process
    print("[Bakım Modu] Bakım modundan çıkılıyor...")
    
    try:
        import subprocess
        import signal
        import time
        
        if bakim_chromium_process:
            try:
                # Process'in PID'sini al
                pid = bakim_chromium_process.pid
                print(f"[Bakım Modu] Bakım Chromium kapatılıyor (PID: {pid})...")
                
                # kioskuser'ın sahip olduğu tüm chromium process'lerini bul ve bakım process'ini kapat
                # Önce SIGTERM ile nazikçe kapat
                subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-TERM", "-f", "chromium-browser.*4321/bakim"
                ], capture_output=True, timeout=2)
                
                time.sleep(1)
                
                # Hala çalışıyorsa SIGKILL ile zorla kapat
                subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-KILL", "-f", "chromium-browser.*4321/bakim"
                ], capture_output=True, timeout=2)
                
                bakim_chromium_process = None
                print("[Bakım Modu] Bakım Chromium kapatıldı, ana ekran aktif")
            except Exception as e:
                print(f"[Bakım Modu] Process sonlandırma hatası: {e}")
        else:
            print("[Bakım Modu] Bakım Chromium zaten kapalı")
    except Exception as e:
        print(f"[Bakım Modu] Bakım kapatma hatası: {e}")