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
        from urllib.parse import quote
        
        # URL encoding ile Türkçe karakterleri düzgün encode et
        mesaj_encoded = quote(mesaj)
        uyari_url = f"http://192.168.53.2:4321/uyari?mesaj={mesaj_encoded}&sure={sure}"
        print(f"[DEBUG] Uyarı URL'i: {uyari_url}")
        
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
            "--disable-search-engine-choice-screen",  # Google arama engelleyici
            "--disable-features=SearchSuggestions",  # Arama önerilerini kapat
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
        
        # Timer başlat - sadece sure > 0 ise otomatik kapat
        if sure > 0:
            uyari_timer = threading.Timer(sure, uyari_kapat)
            uyari_timer.start()
            print(f"[Uyarı Modu] {sure} saniye sonra otomatik kapanacak")
        else:
            print(f"[Uyarı Modu] Manuel kapanma modu - olay bazlı kapanacak")
        
    except Exception as e:
        print(f"[Uyarı Modu] Uyarı Chromium açma hatası: {e}")
        uyari_chromium_process = None

def uyari_kapat():
    """Uyarı ekranını kapatır - AGRESİF KAPATMA STRATEJİSİ"""
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

                # ✅ STRATEJI 1: Spesifik uyarı pattern'i ile kapat
                result = subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-TERM", "-f", "chromium-browser.*4321/uyari"
                ], capture_output=True, timeout=2)
                print(f"[Uyarı Modu] SIGTERM sonuç: returncode={result.returncode}")

                time.sleep(0.5)

                # SIGKILL ile zorla kapat
                result = subprocess.run([
                    "sudo", "-u", "kioskuser",
                    "pkill", "-KILL", "-f", "chromium-browser.*4321/uyari"
                ], capture_output=True, timeout=2)
                print(f"[Uyarı Modu] SIGKILL sonuç: returncode={result.returncode}")

                time.sleep(0.3)

                # ✅ STRATEJI 2: wmctrl ile window kapat
                try:
                    subprocess.run([
                        "sudo", "-u", "kioskuser",
                        "bash", "-c",
                        "DISPLAY=:0 wmctrl -c 'Uyarı' 2>/dev/null || true"
                    ], capture_output=True, timeout=2)
                    print("[Uyarı Modu] wmctrl ile window kapatma denendi")
                except Exception as e:
                    print(f"[Uyarı Modu] wmctrl hatası (göz ardı edilebilir): {e}")

                # ✅ STRATEJI 3: Son çare - PID ile kapat
                try:
                    result = subprocess.run([
                        "bash", "-c",
                        "ps aux | grep -E 'kioskuser.*chromium.*uyari' | grep -v grep | awk '{print $2}'"
                    ], capture_output=True, text=True, timeout=2)

                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        print(f"[Uyarı Modu] Bulunan uyarı PID'leri: {pids}")
                        for uyari_pid in pids:
                            if uyari_pid:
                                try:
                                    subprocess.run(["sudo", "kill", "-9", uyari_pid], timeout=1)
                                    print(f"[Uyarı Modu] PID {uyari_pid} SIGKILL ile kapatıldı")
                                except Exception:
                                    pass
                    else:
                        print("[Uyarı Modu] Uyarı process'i bulunamadı (zaten kapalı)")
                except Exception as e:
                    print(f"[Uyarı Modu] Process arama hatası: {e}")

                uyari_chromium_process = None
                print("[Uyarı Modu] ✅ Uyarı Chromium kapatma işlemi tamamlandı")
            except Exception as e:
                print(f"[Uyarı Modu] Process sonlandırma hatası: {e}")
        else:
            print("[Uyarı Modu] Uyarı Chromium process referansı yok")

            # Zombi process kontrolü
            try:
                result = subprocess.run([
                    "bash", "-c",
                    "ps aux | grep -E 'kioskuser.*chromium.*uyari' | grep -v grep | awk '{print $2}'"
                ], capture_output=True, text=True, timeout=2)

                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    print(f"[Uyarı Modu] Zombi uyarı process'leri bulundu: {pids}")
                    for uyari_pid in pids:
                        if uyari_pid:
                            try:
                                subprocess.run(["sudo", "kill", "-9", uyari_pid], timeout=1)
                                print(f"[Uyarı Modu] Zombi PID {uyari_pid} temizlendi")
                            except Exception:
                                pass
                else:
                    print("[Uyarı Modu] Hiçbir uyarı process'i çalışmıyor")
            except Exception as e:
                print(f"[Uyarı Modu] Zombi process kontrolü hatası: {e}")

        # Timer'ı temizle
        if uyari_timer:
            uyari_timer.cancel()
            uyari_timer = None

        print("[Uyarı Modu] ✅ Uyarı kapatma tamamlandı")

    except Exception as e:
        print(f"[Uyarı Modu] ❌ Uyarı kapatma hatası: {e}")

def uyari_moduna_gir():
    """Uyarı moduna girildiğinde çalışır - Bu fonksiyon durum makinesi için"""
    print("[Uyarı Modu] Uyarı moduna giriliyor...")
    # Uyarı modu için özel işlemler buraya eklenebilir

def uyari_modundan_cik():
    """Uyarı modundan çıkılırken çalışır - Uyarı Chromium'unu kapatır"""
    uyari_kapat()
