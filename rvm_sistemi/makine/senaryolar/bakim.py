# Global değişken - bakım Chromium process'i
bakim_chromium_process = None

# Bakım modu durum sınıfı
class BakimDurumu:
    def __init__(self):
        # Sensör verileri
        self.agirlik = None
        self.uzunluk_motor_verisi = None
        
        # Lojik durumlar
        self.gsi_lojik = False
        self.gso_lojik = False
        self.yso_lojik = False
        self.ysi_lojik = False
        
        # Alarm durumları
        self.konveyor_alarm = False
        self.yonlendirici_alarm = False
        self.seperator_alarm = False
        
        # Konum durumları
        self.konveyor_konumda = False
        self.yonlendirici_konumda = False
        self.seperator_konumda = False
        
        # Hata durumları
        self.konveyor_hata = False
        self.yonlendirici_hata = False
        self.seperator_hata = False
        self.konveyor_adim_problem = False
        
        # Kalibrasyon durumları
        self.yonlendirici_kalibrasyon = False
        self.seperator_kalibrasyon = False

# Global bakım durumu
bakim_durumu = BakimDurumu()

def olayi_isle(olay):
    #print(f"[Bakım Modu] Gelen olay: {olay}")
    # Mesajı işle
    mesaj_isle(olay)

def modbus_mesaj(modbus_verisi):
    """Modbus verilerini işler - geriye dönük uyumluluk için"""
    #print(f"[Bakım Modu] Modbus verisi: {modbus_verisi}")
    # Modbus verileri artık durum_degistirici.py'de işleniyor

def bakim_moduna_gir(bakim_url="http://192.168.53.2:4321/bakim"):
    """Bakım moduna girildiğinde çalışır - Yeni Chromium penceresi açar"""
    global bakim_chromium_process
    print(f"[Bakım Modu] Bakım moduna giriliyor... URL: {bakim_url}")
    
    try:
        import subprocess
        import os
        
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





def mesaj_isle(mesaj):
    """Bakım modunda gelen mesajları işler"""
    mesaj = mesaj.strip().lower()
    #print(f"[Bakım Modu] Mesaj işleniyor: {mesaj}")
    
    # Ağırlık verisi
    if mesaj.startswith("a:"):
        bakim_durumu.agirlik = float(mesaj.split(":")[1].replace(",", "."))
        print(f"[Bakım Modu] Ağırlık güncellendi: {bakim_durumu.agirlik}")
        _send_sensor_data_to_websocket()
    
    # Sensör lojik durumları
    elif mesaj == "gsi":
        bakim_durumu.gsi_lojik = True
        print("[Bakım Modu] GSI lojik aktif")
    elif mesaj == "gso":
        bakim_durumu.gso_lojik = True
        print("[Bakım Modu] GSO lojik aktif")
    elif mesaj == "yso":
        bakim_durumu.yso_lojik = True
        print("[Bakım Modu] YSO lojik aktif")
    elif mesaj == "ysi":
        bakim_durumu.ysi_lojik = True
        print("[Bakım Modu] YSI lojik aktif")
    
    # Motor verisi
    elif mesaj.startswith("m:"):
        bakim_durumu.uzunluk_motor_verisi = float(mesaj.split(":")[1].replace(",", "."))
        print(f"[Bakım Modu] Motor verisi güncellendi: {bakim_durumu.uzunluk_motor_verisi}")
    
    # Alarm durumları
    elif mesaj == "kma":
        bakim_durumu.konveyor_alarm = True
        print("[Bakım Modu] Konveyor alarm aktif")
        _send_alarm_to_websocket()
    elif mesaj == "yma":
        bakim_durumu.yonlendirici_alarm = True
        print("[Bakım Modu] Yönlendirici alarm aktif")
        _send_alarm_to_websocket()
    elif mesaj == "sma":
        bakim_durumu.seperator_alarm = True
        print("[Bakım Modu] Klape alarm aktif")
        _send_alarm_to_websocket()
    
    # Konum durumları (bu mesajlar aynı zamanda alarm temizleme de yapıyor)
    elif mesaj == "kmk":
        bakim_durumu.konveyor_konumda = True
        bakim_durumu.konveyor_alarm = False  # Konum mesajı alarmı da temizler
        print("[Bakım Modu] Konveyor konumda - alarm temizlendi")
        _send_alarm_to_websocket()
    elif mesaj == "ymk":
        bakim_durumu.yonlendirici_konumda = True
        bakim_durumu.yonlendirici_alarm = False  # Konum mesajı alarmı da temizler
        print("[Bakım Modu] Yönlendirici konumda - alarm temizlendi")
        _send_alarm_to_websocket()
    elif mesaj == "smk":  
        bakim_durumu.seperator_konumda = True
        bakim_durumu.seperator_alarm = False  # Konum mesajı alarmı da temizler
        print("[Bakım Modu] Klape konumda - alarm temizlendi")
        _send_alarm_to_websocket()
    
    # Hata durumları
    elif mesaj == "kmh":
        bakim_durumu.konveyor_hata = True
        print("[Bakım Modu] Konveyor hata")
    elif mesaj == "ymh":  
        bakim_durumu.yonlendirici_hata = True
        print("[Bakım Modu] Yönlendirici hata")
    elif mesaj == "smh":  
        bakim_durumu.seperator_hata = True
        print("[Bakım Modu] Klape hata")
    elif mesaj == "kmp":  
        bakim_durumu.konveyor_adim_problem = True
        print("[Bakım Modu] Konveyor adım problemi")
    
    # Kalibrasyon durumları
    elif mesaj == "ykt":
        bakim_durumu.yonlendirici_kalibrasyon = True
        print("[Bakım Modu] Yönlendirici kalibrasyon")
    elif mesaj == "skt":  
        bakim_durumu.seperator_kalibrasyon = True
        print("[Bakım Modu] Klape kalibrasyon")
    

def _send_alarm_to_websocket():
    """Alarm durumlarını WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ..api.endpoints.websocket import send_alarm_data_to_bakim
        import asyncio
        
        # Alarm verisini hazırla
        alarm_data = {
            'konveyor_alarm': bakim_durumu.konveyor_alarm,
            'yonlendirici_alarm': bakim_durumu.yonlendirici_alarm,
            'seperator_alarm': bakim_durumu.seperator_alarm
        }
        
        # Asyncio event loop'u al veya oluştur
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # WebSocket mesajını gönder
        if loop.is_running():
            # Eğer loop çalışıyorsa, task olarak ekle
            asyncio.create_task(send_alarm_data_to_bakim(alarm_data))
        else:
            # Eğer loop çalışmıyorsa, çalıştır
            loop.run_until_complete(send_alarm_data_to_bakim(alarm_data))
        
        # print(f"[Bakım Modu] Alarm verisi WebSocket'e gönderildi: {alarm_data}")
        
    except Exception as e:
        print(f"[Bakım Modu] WebSocket alarm gönderim hatası: {e}")

def _send_sensor_data_to_websocket():
    """Sensör verilerini WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ..api.endpoints.websocket import send_sensor_data_to_bakim
        import asyncio
        
        # Sensör verisini hazırla
        sensor_data = {
            'agirlik': bakim_durumu.agirlik,
            'uzunluk_motor_verisi': bakim_durumu.uzunluk_motor_verisi
        }
        
        # Asyncio event loop'u al veya oluştur
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # WebSocket mesajını gönder
        if loop.is_running():
            # Eğer loop çalışıyorsa, task olarak ekle
            asyncio.create_task(send_sensor_data_to_bakim(sensor_data))
        else:
            # Eğer loop çalışmıyorsa, çalıştır
            loop.run_until_complete(send_sensor_data_to_bakim(sensor_data))
        
        # print(f"[Bakım Modu] Sensör verisi WebSocket'e gönderildi: {sensor_data}")
        
    except Exception as e:
        print(f"[Bakım Modu] WebSocket sensör gönderim hatası: {e}")

def get_bakim_durumu():
    """Bakım durumunu döndürür"""
    return bakim_durumu