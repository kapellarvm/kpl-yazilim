# Global değişken - uyarı Chromium process'i
uyari_chromium_process = None
uyari_timer = None

def olayi_isle(olay):
    print(f"[Uyarı Modu] Gelen olay: {olay}")
    # Uyarı modunda yapılacak işlemler buraya eklenebilir

def uyari_goster(mesaj="Lütfen şişeyi alınız", sure=2):
    """Hızlı uyarı gösterir - 2 saniye sonra otomatik kapanır"""
    global uyari_chromium_process, uyari_timer
    print(f"[Uyarı Modu] Uyarı gösteriliyor: {mesaj}")
    
    try:
        import subprocess
        import os
        import threading
        import time
        
        uyari_url = f"http://192.168.53.2:4321/uyari?mesaj={mesaj}&sure={sure}"
        
        # Yeni Chromium penceresi aç (kioskuser olarak, kiosk modda)
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        # Chromium'u kiosk modunda aç - ULTRA HIZLI + GÖLGELENMESİZ
        print(f"[DEBUG] Uyarı Chromium açma komutu çalıştırılıyor...")
        uyari_chromium_process = subprocess.Popen([
            "sudo", "-u", "kioskuser",
            "env", "DISPLAY=:0", "XAUTHORITY=/home/kioskuser/.Xauthority",
            "/snap/chromium/current/usr/lib/chromium-browser/chrome",
            "--kiosk",
            "--window-size=1920,1080",  # Sabit window size hızlandırır
            "--start-fullscreen",
            "--app=" + uyari_url,  # App mode - window switching'i önler
            # GÖLGELENMEYİ ÖNLEMEK İÇİN WINDOW MANAGEMENT
            "--disable-backgrounding-occluded-windows",
            "--disable-background-timer-throttling", 
            "--disable-renderer-backgrounding",
            "--disable-background-networking",
            "--disable-background-mode",
            "--force-color-profile=generic-rgb",
            "--disable-composited-antialiasing", 
            # GPU VE RENDERING OPTİMİZASYONU
            "--force-gpu-rasterization",
            "--enable-zero-copy",
            "--enable-gpu-rasterization",
            "--enable-accelerated-2d-canvas",
            "--enable-gpu",
            "--ignore-gpu-blacklist",
            "--ignore-gpu-blocklist",
            "--enable-gpu-compositing",
            "--enable-accelerated-video-decode",
            # WINDOW FOCUS VE VISIBILITY OPTİMİZASYONU
            "--disable-features=VizDisplayCompositor,PaintHolding",
            "--disable-blink-features=PaintHolding",
            "--blink-settings=preferredColorScheme=0",
            "--disable-web-security",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            # SMOOTH RENDERING
            "--enable-smooth-scrolling",
            "--disable-frame-rate-limit",
            "--max-gum-fps=60",
            # HIZLI YÜKLENMİŞ İÇİN
            "--no-first-run",
            "--no-default-browser-check",
            "--noerrdialogs",
            "--disable-pinch",
            "--overscroll-history-navigation=0",
            # CACHE VE NETWORK OPTİMİZASYONU
            "--aggressive-cache-discard",
            "--disable-cache",
            "--disk-cache-size=0",
            "--media-cache-size=0",
            "--disable-application-cache",
            "--disable-offline-load-stale-cache",
            # EKSİK RENDER BLOKLARINI ÖNLEYİCİ
            "--disable-ipc-flooding-protection",
            "--disable-sync",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-translate",
            "--disable-features=TranslateUI",
            # LOGGING VE DEBUG KAPATMA
            "--disable-logging",
            "--disable-gpu-logging",
            "--silent",
            # MEMORY VE PERFORMANCE
            "--max_old_space_size=512",
            "--memory-pressure-off",
            # INSTANT LOADING
            "--enable-fast-unload",
            "--no-sandbox",  # Hızlı başlatma için
            "--disable-setuid-sandbox",
            # GÖLGELENMEYİ ÖNLEMEK İÇİN EK PARAMETRELER
            "--disable-background-media-suspend",
            "--disable-low-res-tiling",
            "--disable-threaded-animation",
            "--force-device-scale-factor=1",
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Hızlı hata kontrolü yap
        time.sleep(0.1)
        if uyari_chromium_process.poll() is not None:
            stdout, stderr = uyari_chromium_process.communicate()
            print(f"[ERROR] Uyarı Chromium başlatılamadı! Exit code: {uyari_chromium_process.returncode}")
            print(f"[ERROR] STDOUT: {stdout.decode() if stdout else 'empty'}")
            print(f"[ERROR] STDERR: {stderr.decode() if stderr else 'empty'}")
            return
        
        print(f"[Uyarı Modu] Uyarı Chromium açıldı (PID: {uyari_chromium_process.pid}): {uyari_url}")
        
        # Window focus için ekstra optimizasyon - gölgelenmeyi önler
        try:
            time.sleep(0.05)  # Çok kısa bekleme - window'un tam açılması için
            # Window'u öne çıkarmak için wmctrl kullan (eğer yüklüyse)
            subprocess.run([
                "sudo", "-u", "kioskuser",
                "env", "DISPLAY=:0", "XAUTHORITY=/home/kioskuser/.Xauthority",
                "xdotool", "search", "--onlyvisible", "--class", "chrome", 
                "windowactivate", "--sync"
            ], capture_output=True, timeout=0.5)
        except:
            pass  # wmctrl veya xdotool yoksa görmezden gel
        
        # Timer başlat - belirtilen süre sonra otomatik kapat
        uyari_timer = threading.Timer(sure, uyari_kapat)
        uyari_timer.start()
        print(f"[Uyarı Modu] {sure} saniye sonra otomatik kapanacak")
        
    except Exception as e:
        print(f"[Uyarı Modu] Uyarı Chromium açma hatası: {e}")
        uyari_chromium_process = None

def uyari_kapat():
    """Uyarı ekranını kapatır"""
    global uyari_chromium_process, uyari_timer
    print("[Uyarı Modu] Uyarı ekranı kapatılıyor...")
    
    try:
        import subprocess
        import time
        
        if uyari_chromium_process:
            try:
                # Process'in PID'sini al
                pid = uyari_chromium_process.pid
                print(f"[Uyarı Modu] Uyarı Chromium kapatılıyor (PID: {pid})...")
                
                # kioskuser'ın sahip olduğu tüm chromium process'lerini bul ve uyarı process'ini kapat
                # Önce SIGTERM ile nazikçe kapat
                subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-TERM", "-f", "chromium-browser.*4321/uyari"
                ], capture_output=True, timeout=2)
                
                time.sleep(0.5)
                
                # Hala çalışıyorsa SIGKILL ile zorla kapat
                subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-KILL", "-f", "chromium-browser.*4321/uyari"
                ], capture_output=True, timeout=2)
                
                uyari_chromium_process = None
                print("[Uyarı Modu] Uyarı Chromium kapatıldı")
            except Exception as e:
                print(f"[Uyarı Modu] Process sonlandırma hatası: {e}")
        else:
            print("[Uyarı Modu] Uyarı Chromium zaten kapalı")
            
        # Timer'ı temizle
        if uyari_timer:
            uyari_timer.cancel()
            uyari_timer = None
            
    except Exception as e:
        print(f"[Uyarı Modu] Uyarı kapatma hatası: {e}")

def uyari_moduna_gir():
    """Uyarı moduna girildiğinde çalışır - Bu fonksiyon durum makinesi için"""
    print("[Uyarı Modu] Uyarı moduna giriliyor...")
    # Uyarı modu için özel işlemler buraya eklenebilir

def uyari_modundan_cik():
    """Uyarı modundan çıkılırken çalışır - Uyarı Chromium'unu kapatır"""
    uyari_kapat()
