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
        
        # SDS sensör verileri
        self.sds_giris = {"gerilim": 0.0, "akim": 0.0, "saglik": "Normal"}
        self.sds_plastik = {"gerilim": 0.0, "akim": 0.0, "saglik": "Normal"}
        self.sds_cam = {"gerilim": 0.0, "akim": 0.0, "saglik": "Normal"}
        self.sds_metal = {"gerilim": 0.0, "akim": 0.0, "saglik": "Normal"}
        self.sds_led = {"gerilim": 0.0, "akim": 0.0, "saglik": "Normal"}
        
        # Doluluk oranları
        self.doluluk_plastik = 0
        self.doluluk_metal = 0
        self.doluluk_cam = 0

# Global bakım durumu
bakim_durumu = BakimDurumu()

def olayi_isle(olay):
    #print(f"[Bakım Modu] Gelen olay: {olay}")
    # Mesajı işle
    mesaj_isle(olay)

def modbus_mesaj(modbus_verisi):
    """Modbus verilerini işler - geriye dönük uyumluluk için"""
    #print(f"[Bakım Modu] Modbus verisi: {modbus_verisi}")
    # Modbus verileri durum_degistirici.py'de işleniyor

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
    print(f"[Bakım Modu] Mesaj işleniyor: '{mesaj}' (uzunluk: {len(mesaj)})")
    
    # Ağırlık verisi
    if mesaj.startswith("a:"):
        bakim_durumu.agirlik = float(mesaj.split(":")[1].replace(",", "."))
        print(f"[Bakım Modu] Ağırlık güncellendi: {bakim_durumu.agirlik}")
        _send_sensor_data_to_websocket()
        
        # WebSocket ölçüm bildirimi kaldırıldı - sadece manuel kontrol
    
    # SDS sensör verileri
    elif mesaj.startswith("sdgo#") or mesaj.startswith("sdpu#") or mesaj.startswith("sdcu#") or mesaj.startswith("sdmu#") or mesaj.startswith("sdle#"):
        _parse_sds_data(mesaj)
    
    # Doluluk oranı verileri
    elif mesaj.startswith("do#"):
        _parse_doluluk_data(mesaj)
    
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
        bakim_durumu.konveyor_alarm = True  # Hata durumunda alarm LED'i kırmızı olsun
        print("[Bakım Modu] Konveyor hata")
        _send_alarm_to_websocket()
    elif mesaj == "ymh":  
        bakim_durumu.yonlendirici_hata = True
        bakim_durumu.yonlendirici_alarm = True  # Hata durumunda alarm LED'i kırmızı olsun
        print("[Bakım Modu] Yönlendirici hata")
        _send_alarm_to_websocket()
    elif mesaj == "smh":  
        bakim_durumu.seperator_hata = True
        bakim_durumu.seperator_alarm = True  # Hata durumunda alarm LED'i kırmızı olsun
        print("[Bakım Modu] Klape hata")
        _send_alarm_to_websocket()
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
    
    # Sensör mesajları (kapak durumları)
    elif mesaj == "g/msup":
        print("[Bakım Modu] Üst kapak açık")
        _send_sensor_message_to_websocket("g/msup")
    elif mesaj == "g/msua":
        print("[Bakım Modu] Üst kapak kapalı")
        _send_sensor_message_to_websocket("g/msua")
    elif mesaj == "g/msap":
        print("[Bakım Modu] Alt kapak açık")
        _send_sensor_message_to_websocket("g/msap")
    elif mesaj == "g/msaa":
        print("[Bakım Modu] Alt kapak kapalı")
        _send_sensor_message_to_websocket("g/msaa")
    

def _send_sensor_message_to_websocket(message):
    """Sensör mesajlarını WebSocket ile bakım ekranına gönderir"""
    try:
        from ...api.endpoints.websocket import send_sensor_message_to_bakim
        import asyncio
        
        # Asyncio event loop'u al veya oluştur
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # WebSocket mesajını gönder
        if loop.is_running():
            asyncio.create_task(send_sensor_message_to_bakim(message))
        else:
            loop.run_until_complete(send_sensor_message_to_bakim(message))
            
    except Exception as e:
        print(f"[Bakım Modu] WebSocket sensör mesajı gönderim hatası: {e}")

def _send_alarm_to_websocket():
    """Alarm durumlarını WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ...api.endpoints.websocket import send_alarm_data_to_bakim
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

def _parse_sds_data(mesaj):
    """SDS sensör verilerini parse eder"""
    try:
        # Mesajı temizle ve büyük harfe çevir
        mesaj = mesaj.strip().upper()
        
        
        # Her sensör verisini ayrı ayrı işle
        if "SDGO#" in mesaj:
            _parse_single_sds_sensor(mesaj, "sdgo", "giris")
        if "SDPU#" in mesaj:
            _parse_single_sds_sensor(mesaj, "sdpu", "plastik")
        if "SDCU#" in mesaj:
            _parse_single_sds_sensor(mesaj, "sdcu", "cam")
        if "SDMU#" in mesaj:
            _parse_single_sds_sensor(mesaj, "sdmu", "metal")
        if "SDLE#" in mesaj:
            _parse_single_sds_sensor(mesaj, "sdle", "led")
            
        # WebSocket'e gönder
        _send_sds_data_to_websocket()
        
    except Exception as e:
        print(f"[Bakım Modu] SDS parse hatası: {e}")

def _parse_single_sds_sensor(mesaj, sensor_prefix, sensor_key):
    """Tek bir SDS sensör verisini parse eder"""
    try:
        # Sensör verisini bul
        start_idx = mesaj.find(f"{sensor_prefix.upper()}#")
        if start_idx == -1:
            return
            
        # Sonraki # işaretini bul
        end_idx = mesaj.find("#", start_idx + len(sensor_prefix) + 1)
        if end_idx == -1:
            end_idx = len(mesaj)
            
        sensor_data = mesaj[start_idx:end_idx]
        
        # Veriyi parse et: g:23.10*a:8.80*sd:Normal
        gerilim = 0.0
        akim = 0.0
        saglik = "Normal"
        
        # Gerilim (g:)
        g_idx = sensor_data.find("G:")
        if g_idx != -1:
            g_end = sensor_data.find("*", g_idx)
            if g_end == -1:
                g_end = len(sensor_data)
            try:
                gerilim = float(sensor_data[g_idx+2:g_end])
            except:
                gerilim = 0.0
                
        # Akım (a:)
        a_idx = sensor_data.find("A:")
        if a_idx != -1:
            a_end = sensor_data.find("*", a_idx)
            if a_end == -1:
                a_end = len(sensor_data)
            try:
                akim = float(sensor_data[a_idx+2:a_end])
            except:
                akim = 0.0
                
        # Sağlık durumu (sd:)
        sd_idx = sensor_data.find("SD:")
        if sd_idx != -1:
            sd_end = sensor_data.find("*", sd_idx)
            if sd_end == -1:
                sd_end = len(sensor_data)
            saglik = sensor_data[sd_idx+3:sd_end]
        
        # Bakım durumuna kaydet
        if sensor_key == "giris":
            bakim_durumu.sds_giris = {"gerilim": gerilim, "akim": akim, "saglik": saglik}
        elif sensor_key == "plastik":
            bakim_durumu.sds_plastik = {"gerilim": gerilim, "akim": akim, "saglik": saglik}
        elif sensor_key == "cam":
            bakim_durumu.sds_cam = {"gerilim": gerilim, "akim": akim, "saglik": saglik}
        elif sensor_key == "metal":
            bakim_durumu.sds_metal = {"gerilim": gerilim, "akim": akim, "saglik": saglik}
        elif sensor_key == "led":
            bakim_durumu.sds_led = {"gerilim": gerilim, "akim": akim, "saglik": saglik}
            
        
        
    except Exception as e:
        print(f"[Bakım Modu] {sensor_key} SDS parse hatası: {e}")

def _send_sds_data_to_websocket():
    """SDS sensör verilerini WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ...api.endpoints.websocket import send_sds_data_to_bakim
        import asyncio
        
        # SDS verisini hazırla
        sds_data = {
            'sds_giris': bakim_durumu.sds_giris,
            'sds_plastik': bakim_durumu.sds_plastik,
            'sds_cam': bakim_durumu.sds_cam,
            'sds_metal': bakim_durumu.sds_metal,
            'sds_led': bakim_durumu.sds_led
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
            asyncio.create_task(send_sds_data_to_bakim(sds_data))
        else:
            # Eğer loop çalışmıyorsa, çalıştır
            loop.run_until_complete(send_sds_data_to_bakim(sds_data))
        
    except Exception as e:
        print(f"[Bakım Modu] WebSocket SDS gönderim hatası: {e}")

def _parse_doluluk_data(mesaj):
    """Doluluk oranı verilerini parse eder"""
    try:
        # Mesajı temizle: "do#c:100.00#p:100.00#m:100.00"
        mesaj = mesaj.strip().upper()
        print(f"[Bakım Modu] Doluluk verisi parse ediliyor: {mesaj}")
        
        # Cam doluluk (c:)
        if "#C:" in mesaj:
            cam_start = mesaj.find("#C:") + 3
            cam_end = mesaj.find("#", cam_start)
            if cam_end == -1:
                cam_end = len(mesaj)
            try:
                cam_value = mesaj[cam_start:cam_end]
                bakim_durumu.doluluk_cam = int(float(cam_value))
                print(f"[Bakım Modu] Cam doluluk: {bakim_durumu.doluluk_cam}% (ham: {cam_value})")
            except Exception as e:
                print(f"[Bakım Modu] Cam parse hatası: {e}")
                bakim_durumu.doluluk_cam = 0
        else:
            print(f"[Bakım Modu] Cam verisi bulunamadı")
        
        # Plastik doluluk (p:)
        if "#P:" in mesaj:
            plastik_start = mesaj.find("#P:") + 3
            plastik_end = mesaj.find("#", plastik_start)
            if plastik_end == -1:
                plastik_end = len(mesaj)
            try:
                plastik_value = mesaj[plastik_start:plastik_end]
                bakim_durumu.doluluk_plastik = int(float(plastik_value))
                print(f"[Bakım Modu] Plastik doluluk: {bakim_durumu.doluluk_plastik}% (ham: {plastik_value})")
            except Exception as e:
                print(f"[Bakım Modu] Plastik parse hatası: {e}")
                bakim_durumu.doluluk_plastik = 0
        else:
            print(f"[Bakım Modu] Plastik verisi bulunamadı")
        
        # Metal doluluk (m:)
        if "#M:" in mesaj:
            metal_start = mesaj.find("#M:") + 3
            metal_end = mesaj.find("#", metal_start)
            if metal_end == -1:
                metal_end = len(mesaj)
            try:
                metal_value = mesaj[metal_start:metal_end]
                bakim_durumu.doluluk_metal = int(float(metal_value))
                print(f"[Bakım Modu] Metal doluluk: {bakim_durumu.doluluk_metal}% (ham: {metal_value})")
            except Exception as e:
                print(f"[Bakım Modu] Metal parse hatası: {e}")
                bakim_durumu.doluluk_metal = 0
        else:
            print(f"[Bakım Modu] Metal verisi bulunamadı")
        
        print(f"[Bakım Modu] Parse sonucu - Cam: {bakim_durumu.doluluk_cam}%, Plastik: {bakim_durumu.doluluk_plastik}%, Metal: {bakim_durumu.doluluk_metal}%")
        
        # WebSocket'e gönder
        _send_doluluk_data_to_websocket()
        
    except Exception as e:
        print(f"[Bakım Modu] Doluluk parse hatası: {e}")

def _send_doluluk_data_to_websocket():
    """Doluluk verilerini WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ...api.endpoints.websocket import send_doluluk_data_to_bakim
        import asyncio
        
        # Doluluk verisini hazırla
        doluluk_data = {
            'plastik': bakim_durumu.doluluk_plastik,
            'metal': bakim_durumu.doluluk_metal,
            'cam': bakim_durumu.doluluk_cam
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
            asyncio.create_task(send_doluluk_data_to_bakim(doluluk_data))
        else:
            # Eğer loop çalışmıyorsa, çalıştır
            loop.run_until_complete(send_doluluk_data_to_bakim(doluluk_data))
        
    except Exception as e:
        print(f"[Bakım Modu] WebSocket doluluk gönderim hatası: {e}")

def _send_sensor_data_to_websocket():
    """Sensör verilerini WebSocket ile bakım ekranına gönderir"""
    try:
        # WebSocket modülünü import et
        from ...api.endpoints.websocket import send_sensor_data_to_bakim
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

def _send_measurement_status_to_websocket(is_measuring):
    """Ölçüm durumunu WebSocket ile bakım ekranına gönder"""
    try:
        from ...api.endpoints.websocket import send_measurement_status_to_bakim
        import asyncio
        
        # Asyncio event loop'u al veya oluştur
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # WebSocket mesajını gönder
        if loop.is_running():
            asyncio.create_task(send_measurement_status_to_bakim(is_measuring))
        else:
            loop.run_until_complete(send_measurement_status_to_bakim(is_measuring))
            
    except Exception as e:
        print(f"[Bakım Modu] WebSocket ölçüm durumu gönderim hatası: {e}")

def get_bakim_durumu():
    """Bakım durumunu döndürür"""
    return bakim_durumu