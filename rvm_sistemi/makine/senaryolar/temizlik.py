import webbrowser
import time
from ...utils.logger import log_system, log_error, log_success, log_warning

class TemizlikDurumu:
    def __init__(self):
        self.temizlik_url = "http://192.168.53.2:4321/temizlik"  # Temizlik URL'i
        self.temizlik_aktif = False
        self.temizlik_chromium_process = None  # Temizlik Chromium process'i
        
    def temizlik_moduna_gir(self, url=None):
        """Temizlik moduna girildiğinde çalışır - Yeni Chromium penceresi açar"""
        global temizlik_chromium_process
        if url:
            self.temizlik_url = url
        
        print(f"[Temizlik Modu] Temizlik moduna giriliyor... URL: {self.temizlik_url}")
        log_system(f"Temizlik moduna giriliyor: {self.temizlik_url}")
        
        try:
            import subprocess
            import os
            
            # Yeni Chromium penceresi aç (kioskuser olarak, kiosk modda)
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            
            # Chromium'u kiosk modunda aç - arka planda çalışsın
            print(f"[DEBUG] Temizlik Chromium açma komutu çalıştırılıyor...")
            self.temizlik_chromium_process = subprocess.Popen([
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
                self.temizlik_url
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Hemen hata kontrolü yap
            import time
            time.sleep(0.5)
            if self.temizlik_chromium_process.poll() is not None:
                stdout, stderr = self.temizlik_chromium_process.communicate()
                print(f"[ERROR] Temizlik Chromium başlatılamadı! Exit code: {self.temizlik_chromium_process.returncode}")
                print(f"[ERROR] STDOUT: {stdout.decode() if stdout else 'empty'}")
                print(f"[ERROR] STDERR: {stderr.decode() if stderr else 'empty'}")
                log_error(f"Temizlik Chromium başlatılamadı: {stderr.decode() if stderr else 'empty'}")
                return False
            
            print(f"[Temizlik Modu] Temizlik Chromium açıldı (PID: {self.temizlik_chromium_process.pid}): {self.temizlik_url}")
            log_success(f"Temizlik Chromium açıldı (PID: {self.temizlik_chromium_process.pid}): {self.temizlik_url}")
            
            self.temizlik_aktif = True
            log_success("Temizlik modu başlatıldı")
            return True
            
        except Exception as e:
            print(f"[Temizlik Modu] Temizlik Chromium açma hatası: {e}")
            log_error(f"Temizlik modu başlatma hatası: {e}")
            self.temizlik_chromium_process = None
            return False
    
    def temizlik_modundan_cik(self):
        """Temizlik modundan çıkılırken çalışır - Temizlik Chromium'unu kapatır"""
        global temizlik_chromium_process
        print("[Temizlik Modu] Temizlik modundan çıkılıyor...")
        log_system("Temizlik modundan çıkılıyor")
        
        try:
            import subprocess
            import signal
            import time
            
            if self.temizlik_chromium_process:
                try:
                    # Process'in PID'sini al
                    pid = self.temizlik_chromium_process.pid
                    print(f"[Temizlik Modu] Temizlik Chromium kapatılıyor (PID: {pid})...")
                    
                    # kioskuser'ın sahip olduğu tüm chromium process'lerini bul ve temizlik process'ini kapat
                    # Önce SIGTERM ile nazikçe kapat
                    subprocess.run([
                        "sudo", "-u", "kioskuser",
                        "pkill", "-TERM", "-f", "chromium-browser.*4321/temizlik"
                    ], capture_output=True, timeout=2)
                    
                    time.sleep(1)
                    
                    # Hala çalışıyorsa SIGKILL ile zorla kapat
                    subprocess.run([
                        "sudo", "-u", "kioskuser",
                        "pkill", "-KILL", "-f", "chromium-browser.*4321/temizlik"
                    ], capture_output=True, timeout=2)
                    
                    self.temizlik_chromium_process = None
                    print("[Temizlik Modu] Temizlik Chromium kapatıldı, ana ekran aktif")
                    log_system("Temizlik Chromium kapatıldı, ana ekran aktif")
                except Exception as e:
                    print(f"[Temizlik Modu] Process sonlandırma hatası: {e}")
                    log_error(f"Temizlik Chromium process sonlandırma hatası: {e}")
            else:
                print("[Temizlik Modu] Temizlik Chromium zaten kapalı")
                log_system("Temizlik Chromium zaten kapalı")
            
            self.temizlik_aktif = False
            log_success("Temizlik modu kapatıldı")
            
        except Exception as e:
            print(f"[Temizlik Modu] Temizlik kapatma hatası: {e}")
            log_error(f"Temizlik modu kapatma hatası: {e}")
    
    def olayi_isle(self, olay):
        """Temizlik modunda olay işleme"""
        if olay == "temizlik_modundan_cik":
            self.temizlik_modundan_cik()
        elif olay == "ana_ekrana_don":
            self.temizlik_modundan_cik()
    
    def modbus_mesaj(self, modbus_veri):
        """Temizlik modunda modbus mesaj işleme"""
        # Modbus verisini parse et ve temizlik ekranına gönder
        self._send_modbus_to_temizlik(modbus_veri)
    
    def _send_modbus_to_temizlik(self, modbus_veri):
        """Modbus verisini temizlik ekranına gönderir"""
        try:
            # Modbus parser'ı import et
            from ..modbus_parser import modbus_parser
            
            # Veriyi parse et
            parsed_data = modbus_parser.parse_modbus_string(modbus_veri)
            if not parsed_data:
                return
            
            motor_id = parsed_data['motor_id']
            motor_data = parsed_data['data']
            
            # Motor tipini belirle
            motor_type = "crusher" if motor_id == 1 else "breaker"
            
            # Veriyi formatla
            formatted_data = modbus_parser.format_for_display(motor_data)
            
            # WebSocket ile gerçek zamanlı güncelleme
            self._send_websocket_update(motor_type, formatted_data)
            
        except Exception as e:
            log_error(f"Temizlik Modbus gönderim hatası: {e}")
    
    def _send_websocket_update(self, motor_type, formatted_data):
        """WebSocket ile temizlik ekranına güncelleme gönder"""
        try:
            # WebSocket modülünü import et
            from ...api.endpoints.websocket import send_modbus_data_to_temizlik
            import asyncio
            
            # Asyncio event loop'u al veya oluştur
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # WebSocket mesajını gönder
            if loop.is_running():
                # Eğer loop çalışıyorsa, task olarak ekle
                asyncio.create_task(send_modbus_data_to_temizlik(motor_type, formatted_data))
            else:
                # Eğer loop çalışmıyorsa, çalıştır
                loop.run_until_complete(send_modbus_data_to_temizlik(motor_type, formatted_data))
                
        except Exception as e:
            log_error(f"Temizlik WebSocket güncelleme hatası: {e}")

def olayi_isle(olay):
    """Temizlik modunda olay işleme"""
    # Temizlik durumu instance'ını kullan
    temizlik.olayi_isle(olay)

def modbus_mesaj(modbus_veri):
    """Temizlik modunda modbus mesaj işleme"""
    # Temizlik durumu instance'ını kullan
    temizlik.modbus_mesaj(modbus_veri)

def mesaj_isle(mesaj):
    """Temizlik modunda gelen mesajları işler"""
    mesaj = mesaj.strip().lower()
    
    # Temizlik modunda mesajları işle ama durum değiştirme
    # Sadece logla ve devam et
    if mesaj.startswith("a:"):
        agirlik = float(mesaj.split(":")[1].replace(",", "."))
        print(f"[Temizlik Modu] Ağırlık verisi: {agirlik}")
    elif mesaj in ["gsi", "gso", "yso", "ysi"]:
        print(f"[Temizlik Modu] Sensör lojik: {mesaj}")
    elif mesaj.startswith("m:"):
        motor_veri = float(mesaj.split(":")[1].replace(",", "."))
        print(f"[Temizlik Modu] Motor verisi: {motor_veri}")
    elif mesaj in ["kma", "yma", "sma"]:
        print(f"[Temizlik Modu] Alarm: {mesaj}")
    elif mesaj in ["kmk", "ymk", "smk"]:
        print(f"[Temizlik Modu] Konum: {mesaj}")
    elif mesaj in ["kmh", "ymh", "smh"]:
        print(f"[Temizlik Modu] Hata: {mesaj}")
    elif mesaj in ["ykt", "skt"]:
        print(f"[Temizlik Modu] Kalibrasyon: {mesaj}")
    else:
        print(f"[Temizlik Modu] Bilinmeyen mesaj: {mesaj}")

# Global temizlik durumu instance'ı
temizlik = TemizlikDurumu()

# Global fonksiyonlar - durum_degistirici.py için
def temizlik_moduna_gir(url=None):
    """Temizlik moduna girer"""
    return temizlik.temizlik_moduna_gir(url)

def temizlik_modundan_cik():
    """Temizlik modundan çıkar"""
    return temizlik.temizlik_modundan_cik()
