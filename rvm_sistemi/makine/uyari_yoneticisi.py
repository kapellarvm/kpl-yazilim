"""
Bağımsız Uyarı Yöneticisi
Durum makinesinden bağımsız olarak çalışır
"""

import subprocess
import os
import time
import threading
from typing import Optional

class UyariYoneticisi:
    def __init__(self):
        self.uyari_chromium_process: Optional[subprocess.Popen] = None
        self.uyari_timer: Optional[threading.Timer] = None
        self.aktif_uyari = False
        
    def uyari_goster(self, mesaj: str = "Lütfen şişeyi alınız", sure: int = 2) -> bool:
        """Hızlı uyarı gösterir - belirtilen süre sonra otomatik kapanır"""
        print(f"[Uyarı Yöneticisi] Uyarı gösteriliyor: {mesaj}")
        
        # Eğer zaten aktif uyarı varsa, önce onu kapat
        if self.aktif_uyari:
            self.uyari_kapat()
            time.sleep(0.1)  # Kısa bekleme
        
        try:
            uyari_url = f"http://192.168.53.2:4321/uyari?mesaj={mesaj}&sure={sure}"
            
            # Yeni Chromium penceresi aç (kioskuser olarak, kiosk modda)
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            
            # Chromium'u kiosk modunda aç - optimize edilmiş parametreler
            print(f"[DEBUG] Uyarı Chromium açma komutu çalıştırılıyor...")
            self.uyari_chromium_process = subprocess.Popen([
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
                # Hızlı açılış için ek optimizasyonlar
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-translate",
                "--disable-logging",
                "--disable-gpu-logging",
                "--silent",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--enable-gpu-rasterization",
                "--enable-zero-copy",
                "--ignore-gpu-blacklist",
                "--ignore-gpu-blocklist",
                "--enable-gpu",
                "--enable-accelerated-2d-canvas",
                "--enable-accelerated-mjpeg-decode",
                "--enable-native-gpu-memory-buffers",
                "--enable-gpu-memory-buffer-video-frames",
                uyari_url
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Hızlı hata kontrolü yap
            time.sleep(0.1)
            if self.uyari_chromium_process.poll() is not None:
                stdout, stderr = self.uyari_chromium_process.communicate()
                print(f"[ERROR] Uyarı Chromium başlatılamadı! Exit code: {self.uyari_chromium_process.returncode}")
                print(f"[ERROR] STDOUT: {stdout.decode() if stdout else 'empty'}")
                print(f"[ERROR] STDERR: {stderr.decode() if stderr else 'empty'}")
                return False
            
            print(f"[Uyarı Yöneticisi] Uyarı Chromium açıldı (PID: {self.uyari_chromium_process.pid}): {uyari_url}")
            
            # Timer başlat - belirtilen süre sonra otomatik kapat
            self.uyari_timer = threading.Timer(sure, self.uyari_kapat)
            self.uyari_timer.start()
            self.aktif_uyari = True
            print(f"[Uyarı Yöneticisi] {sure} saniye sonra otomatik kapanacak")
            return True
            
        except Exception as e:
            print(f"[Uyarı Yöneticisi] Uyarı Chromium açma hatası: {e}")
            self.uyari_chromium_process = None
            return False

    def uyari_kapat(self) -> bool:
        """Uyarı ekranını kapatır"""
        print("[Uyarı Yöneticisi] Uyarı ekranı kapatılıyor...")
        
        try:
            if self.uyari_chromium_process:
                try:
                    # Process'in PID'sini al
                    pid = self.uyari_chromium_process.pid
                    print(f"[Uyarı Yöneticisi] Uyarı Chromium kapatılıyor (PID: {pid})...")
                    
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
                    
                    self.uyari_chromium_process = None
                    print("[Uyarı Yöneticisi] Uyarı Chromium kapatıldı")
                except Exception as e:
                    print(f"[Uyarı Yöneticisi] Process sonlandırma hatası: {e}")
            else:
                print("[Uyarı Yöneticisi] Uyarı Chromium zaten kapalı")
                
            # Timer'ı temizle
            if self.uyari_timer:
                self.uyari_timer.cancel()
                self.uyari_timer = None
                
            self.aktif_uyari = False
            return True
            
        except Exception as e:
            print(f"[Uyarı Yöneticisi] Uyarı kapatma hatası: {e}")
            return False

    def uyari_durumu(self) -> dict:
        """Uyarı durumunu döndürür"""
        return {
            "aktif": self.aktif_uyari,
            "process_pid": self.uyari_chromium_process.pid if self.uyari_chromium_process else None,
            "timer_aktif": self.uyari_timer is not None
        }

    def tum_uyarilari_kapat(self):
        """Tüm uyarıları kapatır (acil durum için)"""
        print("[Uyarı Yöneticisi] Tüm uyarılar kapatılıyor...")
        self.uyari_kapat()

# Global uyarı yöneticisi instance'ı
uyari_yoneticisi = UyariYoneticisi()
