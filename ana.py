# ana.py
from flask import Flask, jsonify
from flasgger import Swagger
from rvm_sistemi.yardimcilar.gunluk_kayit import logger
from rvm_sistemi.ayarlar import genel_ayarlar, sabitler
from rvm_sistemi.veri_tabani import veritabani_yonetici
from rvm_sistemi.dimdb.sunucu import dimdb_api_sunucusu 

# 1. Flask uygulamasını oluştur
app = Flask(__name__)

# 2. Flasgger (Swagger) yapılandırmasını yap
swagger = Swagger(app)

app.register_blueprint(dimdb_api_sunucusu)

@app.route('/')
def index():
    """
    Ana Sayfa
    Bu endpoint, RVM sisteminin çalışıp çalışmadığını kontrol etmek için basit bir cevap döner.
    ---
    responses:
      200:
        description: Sistemin çalıştığını belirten bir mesaj.
        schema:
          type: object
          properties:
            mesaj:
              type: string
              example: RVM Sistemi Aktif
    """
    logger.info("Ana endpoint'e istek geldi.")
    return jsonify({"mesaj": "RVM Sistemi Aktif"})


def baslat():
    """Sistemin başlangıç fonksiyonlarını çalıştırır."""
    veritabani_yonetici.init_db()
    logger.info("Veritabanı altyapısı kontrol edildi ve hazır.")
    logger.info("RVM Sistemi başlatılıyor...")
    logger.info(f"DİM DB API Adresi: {genel_ayarlar.DIMDB_API_URL}")

if __name__ == "__main__":
    baslat()
    # 3. Flask uygulamasını çalıştır
    app.run(host='0.0.0.0', port=genel_ayarlar.RVM_API_PORT, debug=True)