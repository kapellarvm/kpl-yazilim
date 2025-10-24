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
        
    def uyari_goster(self, mesaj: str = "Lütfen şişeyi alınız", sure: int = 2, suresiz: bool = False) -> bool:
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
            
            # Timer başlat - süresiz değilse belirtilen süre sonra otomatik kapat
            if not suresiz:
                self.uyari_timer = threading.Timer(sure, self.uyari_kapat)
                self.uyari_timer.start()
                print(f"[Uyarı Yöneticisi] {sure} saniye sonra otomatik kapanacak")
            else:
                print(f"[Uyarı Yöneticisi] Süresiz uyarı - manuel kapatma gerekli")
            
            self.aktif_uyari = True
            return True
            
        except Exception as e:
            print(f"[Uyarı Yöneticisi] Uyarı Chromium açma hatası: {e}")
            self.uyari_chromium_process = None
            return False

    def uyari_kapat(self) -> bool:
        """Uyarı ekranını kapatır - AGRESİF KAPATMA STRATEJİSİ"""
        print("[Uyarı Yöneticisi] Uyarı ekranı kapatılıyor...")

        try:
            if self.uyari_chromium_process:
                try:
                    # Process'in PID'sini al
                    pid = self.uyari_chromium_process.pid
                    print(f"[Uyarı Yöneticisi] Uyarı Chromium kapatılıyor (PID: {pid})...")

                    # ✅ STRATEJI 1: Spesifik uyarı pattern'i ile kapat
                    result = subprocess.run([
                        "sudo", "-u", "kioskuser",
                        "pkill", "-TERM", "-f", "chromium-browser.*4321/uyari"
                    ], capture_output=True, timeout=2)
                    print(f"[Uyarı Yöneticisi] SIGTERM sonuç: returncode={result.returncode}")

                    time.sleep(0.5)

                    # SIGKILL ile zorla kapat
                    result = subprocess.run([
                        "sudo", "-u", "kioskuser",
                        "pkill", "-KILL", "-f", "chromium-browser.*4321/uyari"
                    ], capture_output=True, timeout=2)
                    print(f"[Uyarı Yöneticisi] SIGKILL sonuç: returncode={result.returncode}")

                    time.sleep(0.3)

                    # ✅ STRATEJI 2: Hala çalışıyorsa, tüm uyarı window'larını kapat (wmctrl ile)
                    try:
                        subprocess.run([
                            "sudo", "-u", "kioskuser",
                            "bash", "-c",
                            "DISPLAY=:0 wmctrl -c 'Uyarı' 2>/dev/null || true"
                        ], capture_output=True, timeout=2)
                        print("[Uyarı Yöneticisi] wmctrl ile window kapatma denendi")
                    except Exception as e:
                        print(f"[Uyarı Yöneticisi] wmctrl hatası (göz ardı edilebilir): {e}")

                    # ✅ STRATEJI 3: Son çare - tüm kioskuser chromium process'lerinden uyarı URL'li olanları kapat
                    try:
                        # Chromium process'lerini listele ve uyarı URL'li olanları bul
                        result = subprocess.run([
                            "bash", "-c",
                            "ps aux | grep -E 'kioskuser.*chromium.*uyari' | grep -v grep | awk '{print $2}'"
                        ], capture_output=True, text=True, timeout=2)

                        if result.stdout.strip():
                            pids = result.stdout.strip().split('\n')
                            print(f"[Uyarı Yöneticisi] Bulunan uyarı PID'leri: {pids}")
                            for uyari_pid in pids:
                                if uyari_pid:
                                    try:
                                        subprocess.run(["sudo", "kill", "-9", uyari_pid], timeout=1)
                                        print(f"[Uyarı Yöneticisi] PID {uyari_pid} SIGKILL ile kapatıldı")
                                    except Exception:
                                        pass
                        else:
                            print("[Uyarı Yöneticisi] Uyarı process'i bulunamadı (zaten kapalı)")
                    except Exception as e:
                        print(f"[Uyarı Yöneticisi] Process arama hatası: {e}")

                    self.uyari_chromium_process = None
                    print("[Uyarı Yöneticisi] ✅ Uyarı Chromium kapatma işlemi tamamlandı")
                except Exception as e:
                    print(f"[Uyarı Yöneticisi] Process sonlandırma hatası: {e}")
            else:
                print("[Uyarı Yöneticisi] Uyarı Chromium process referansı yok")

                # Yine de çalışan uyarı process'leri olabilir, kontrol et
                try:
                    result = subprocess.run([
                        "bash", "-c",
                        "ps aux | grep -E 'kioskuser.*chromium.*uyari' | grep -v grep | awk '{print $2}'"
                    ], capture_output=True, text=True, timeout=2)

                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        print(f"[Uyarı Yöneticisi] Zombi uyarı process'leri bulundu: {pids}")
                        for uyari_pid in pids:
                            if uyari_pid:
                                try:
                                    subprocess.run(["sudo", "kill", "-9", uyari_pid], timeout=1)
                                    print(f"[Uyarı Yöneticisi] Zombi PID {uyari_pid} temizlendi")
                                except Exception:
                                    pass
                    else:
                        print("[Uyarı Yöneticisi] Hiçbir uyarı process'i çalışmıyor")
                except Exception as e:
                    print(f"[Uyarı Yöneticisi] Zombi process kontrolü hatası: {e}")

            # Timer'ı temizle
            if self.uyari_timer:
                self.uyari_timer.cancel()
                self.uyari_timer = None

            self.aktif_uyari = False
            print("[Uyarı Yöneticisi] ✅ Uyarı kapatma tamamlandı - aktif_uyari=False")
            return True

        except Exception as e:
            print(f"[Uyarı Yöneticisi] ❌ Uyarı kapatma hatası: {e}")
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
