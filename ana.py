# ana.py

import sys
import threading
import time
import schedule

# PySide6 ve WebEngine modüllerini import et
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot

# Projenin diğer modüllerini import et
from rvm_sistemi.dimdb import sunucu, istemci

# --- ARAYÜZ TANIMLAMALARI ---

# URL'deki yazım hatası düzeltildi
DARPHANE_UI_URL = "http://192.168.53.1:5432"

class ArayuzPenceresi(QMainWindow):
    """
    Ana uygulama penceresini oluşturan ve WebView'i barındıran sınıf.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KAPELLA-RVM Sistemi")
        self.showFullScreen()

        self.webview = QWebEngineView(self)
        self.setCentralWidget(self.webview)
        
        # --- HATA KONTROLÜ EKLENDİ ---
        # Sayfa yüklemesi bittiğinde (başarılı ya da başarısız)
        # 'sayfa_yuklendi' fonksiyonunu çağır.
        self.webview.loadFinished.connect(self.sayfa_yuklendi)

        print(f"Darphane arayüzü yükleniyor: {DARPHANE_UI_URL}")
        self.webview.setUrl(QUrl(DARPHANE_UI_URL))

    @Slot(bool)
    def sayfa_yuklendi(self, basarili):
        """
        WebView yüklemesi tamamlandığında tetiklenir.
        """
        if basarili:
            print("Darphane arayüzü başarıyla yüklendi.")
        else:
            print("!!! HATA: Darphane arayüzü yüklenemedi.")
            print("Olası Sebepler:")
            print("1. DİM DB Kontrol Ünitesi'nin açık ve ağa bağlı olduğundan emin olun.")
            print("2. URL'nin doğru olduğundan emin olun: " + DARPHANE_UI_URL)
            print("3. Güvenlik duvarı (Firewall) programın ağ erişimini engelliyor olabilir.")


# --- ARKA PLAN GÖREVLERİ ---

def run_web_server():
    """
    DİM DB'den gelen istekleri dinleyecek olan Flask sunucusunu başlatır.
    """
    print("Web sunucusu başlatılıyor...")
    sunucu.app.run(host='0.0.0.0', port=4321, debug=False, use_reloader=False)

def start_periodic_tasks():
    """
    Periyodik olarak çalışması gereken istemci görevlerini yönetir.
    """
    print("Periyodik görevler zamanlanıyor...")
    schedule.every(60).seconds.do(istemci.send_heartbeat)

    while True:
        schedule.run_pending()
        time.sleep(1)

# --- ANA UYGULAMA GİRİŞ NOKTASI ---

if __name__ == '__main__':
    print("RVM Sistemi Ana Uygulaması Başlatılıyor...")

    # Arka plan görevleri için thread'leri başlat
    server_thread = threading.Thread(target=run_web_server, name="WebServerThread")
    server_thread.daemon = True
    server_thread.start()

    tasks_thread = threading.Thread(target=start_periodic_tasks, name="PeriodicTasksThread")
    tasks_thread.daemon = True
    tasks_thread.start()

    # Ana Thread'de Grafik Arayüzünü Başlat
    app = QApplication(sys.argv)
    pencere = ArayuzPenceresi()
    pencere.show()
    sys.exit(app.exec())