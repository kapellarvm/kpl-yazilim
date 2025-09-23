# ana.py
import threading
import time
from flask import Flask, jsonify
from flasgger import Swagger
from rvm_sistemi.yardimcilar.gunluk_kayit import logger
from rvm_sistemi.ayarlar import genel_ayarlar
from rvm_sistemi.veri_tabani import veritabani_yonetici
from rvm_sistemi.dimdb.sunucu import dimdb_api_sunucusu
from rvm_sistemi.dimdb import istemci

# 1. Flask uygulamasını oluştur
app = Flask(__name__)

# 2. ÖNCE, tüm API adreslerini içeren Blueprint'i kaydet
app.register_blueprint(dimdb_api_sunucusu)

# 3. SONRA, tüm adresleri görebilmesi için Swagger'ı başlat
swagger = Swagger(app)

# Bu endpoint ana dosyada olduğu için Swagger bunu her zaman görür
@app.route('/')
def index():
    """
    Ana Sayfa
    Bu endpoint, RVM sisteminin çalışıp çalışmadığını kontrol etmek için basit bir cevap döner.
    ---
    responses:
      200:
        description: Sistemin çalıştığını belirten bir mesaj.
    """
    logger.info("Ana endpoint'e istek geldi.")
    return jsonify({"mesaj": "RVM Sistemi Aktif"})

def baslat():
    """Sistemin başlangıç fonksiyonlarını çalıştırır."""
    veritabani_yonetici.init_db()
    logger.info("Veritabanı altyapısı kontrol edildi ve hazır.")
    logger.info(f"RVM Sistemi {genel_ayarlar.RVM_API_PORT} portunda başlatılıyor...")

def heartbeat_dongusu():
    """Her 60 saniyede bir heartbeat gönderen döngü."""
    logger.info("Heartbeat döngüsü başladı. İlk gönderim 60 saniye sonra yapılacak.")
    while True:
        time.sleep(60)
        istemci.send_heartbeat()
#print(app.url_map)
if __name__ == "__main__":
    baslat()

    heartbeat_thread = threading.Thread(target=heartbeat_dongusu, daemon=True)
    heartbeat_thread.start()
    logger.info("Arka plan heartbeat servisi başlatıldı.")

    app.run(host='0.0.0.0', port=genel_ayarlar.RVM_API_PORT, debug=True, use_reloader=False)