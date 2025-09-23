# ana.py
import sys
import threading
import time
from flask import Flask, jsonify
from flasgger import Swagger
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

from rvm_sistemi.yardimcilar.gunluk_kayit import logger
from rvm_sistemi.ayarlar import genel_ayarlar
from rvm_sistemi.veri_tabani import veritabani_yonetici
from rvm_sistemi.dimdb.sunucu import dimdb_api_sunucusu
from rvm_sistemi.dimdb import istemci

# --- 1. ARAYÜZ (GUI) SINIFI ---
class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kapella RVM Arayüzü")
        self.setGeometry(0, 0, 1080, 1920)
        self.webview = QWebEngineView()
        dim_db_url = genel_ayarlar.DIMDB_API_URL
        self.webview.setUrl(QUrl(dim_db_url))
        self.setCentralWidget(self.webview)

# --- 2. ARKA PLAN GÖREVLERİ ---
def baslat_sunucu():
    """Flask sunucusunu başlatan fonksiyon (thread içinde çalışacak)."""
    # use_reloader=False ayarı, thread ile çalışırken önemlidir
    app.run(host='0.0.0.0', port=genel_ayarlar.RVM_API_PORT, debug=True, use_reloader=False)

def heartbeat_dongusu():
    """Her 60 saniyede bir heartbeat gönderen döngü."""
    logger.info("Heartbeat döngüsü başladı. İlk gönderim 60 saniye sonra yapılacak.")
    while True:
        time.sleep(60)
        istemci.send_heartbeat()

# --- 3. ANA UYGULAMA KURULUMU ---
if __name__ == "__main__":
    # Flask uygulamasını ve Blueprint'i yapılandır
    app = Flask(__name__)
    app.register_blueprint(dimdb_api_sunucusu)
    swagger = Swagger(app)

    # Başlangıç fonksiyonlarını çalıştır
    veritabani_yonetici.init_db()
    logger.info("Veritabanı altyapısı kontrol edildi ve hazır.")

    # Arka plan servislerini ayrı thread'lerde başlat
    # Heartbeat servisi
    heartbeat_thread = threading.Thread(target=heartbeat_dongusu, daemon=True)
    heartbeat_thread.start()
    logger.info("Arka plan heartbeat servisi başlatıldı.")
    
    # Flask sunucu servisi
    flask_thread = threading.Thread(target=baslat_sunucu, daemon=True)
    flask_thread.start()
    logger.info(f"Arka plan Flask sunucusu {genel_ayarlar.RVM_API_PORT} portunda başlatıldı.")

    # Arayüzü (GUI) ana thread'de başlat
    # Bu her zaman en sonda olmalıdır çünkü programı bloklar.
    gui_app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(gui_app.exec())