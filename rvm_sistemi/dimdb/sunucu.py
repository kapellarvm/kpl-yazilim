from flask import Flask, request, jsonify
import uuid
import random
import threading
from rvm_sistemi.dimdb import istemci

# Flask uygulamasını oluştur
app = Flask(__name__)

@app.route('/')
def index():
    """
    Sunucunun çalışıp çalışmadığını kontrol etmek için ana sayfa.
    """
    return jsonify({
        "status": "RVM Sunucusu Aktif",
        "oturum_durumu": aktif_oturum["aktif"],
        "aktif_sessionId": aktif_oturum.get("sessionId"),
        "aktif_userId": aktif_oturum.get("userId")
    }), 200

# Aktif oturum bilgilerini saklamak için basit bir sözlük (dictionary)
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "kabul_edilen_pet": 0,
    "kabul_edilen_cam": 0,
    "kabul_edilen_alu": 0
}

def _process_package_and_send_result(data):
    """
    Bu fonksiyon, gelen paketi işler, ölçümleri simüle eder
    ve sonucu istemci üzerinden DİM DB'ye gönderir.
    """
    print(f"Paket işleniyor: {data.get('barcode')}")
    
    # --- FİZİKSEL KONTROL SİMÜLASYONU ---
    measured_weight = round(random.uniform(5.0, 6.5), 2)
    measured_height = round(random.uniform(15.0, 16.0), 2)
    measured_width = round(random.uniform(5.0, 5.8), 2)
    
    is_accepted = random.random() < 0.9
    
    if is_accepted:
        result_code = 0
        bin_id = 1
        result_message = "Ambalaj Kabul Edildi"
        aktif_oturum["kabul_edilen_pet"] += 1
    else:
        result_code = 99
        bin_id = -1
        result_message = "Ambalaj Reddedildi (Simülasyon)"
        
    print(result_message)
        
    result_payload = {
        "guid": str(uuid.uuid4()),
        "uuid": data.get("uuid"),
        "sessionId": data.get("sessionId"),
        "barcode": data.get("barcode"),
        "measuredPackWeight": measured_weight,
        "measuredPackHeight": measured_height,
        "measuredPackWidth": measured_width,
        "binId": bin_id,
        "result": result_code,
        "resultMessage": result_message,
        "acceptedPetCount": aktif_oturum["kabul_edilen_pet"],
        "acceptedGlassCount": aktif_oturum["kabul_edilen_cam"],
        "acceptedAluCount": aktif_oturum["kabul_edilen_alu"]
    }
    
    istemci.send_accept_package_result(result_payload)

@app.route('/sessionStart', methods=['POST'])
def session_start():
    """
    DİM DB'den oturum başlatma veya güncelleme isteği geldiğinde çalışır.
    """
    global aktif_oturum
    data = request.json
    print(f"Gelen sessionStart isteği: {data}")
    
    gelen_session_id = data.get("sessionId")
    gelen_user_id = data.get("userId")

    # --- YENİ MANTIK ---
    # Eğer zaten aktif bir oturum varsa, bunu bir hata olarak değil,
    # mevcut oturuma kullanıcı ataması olarak değerlendir.
    if aktif_oturum["aktif"] and aktif_oturum["sessionId"] == gelen_session_id:
        if gelen_user_id:
            aktif_oturum["userId"] = gelen_user_id
            print(f"Mevcut oturuma ({gelen_session_id}) kullanıcı atandı: {gelen_user_id}")
        return jsonify({"errorCode": 0, "errorMessage": ""})

    # Eğer tamamen farklı yeni bir oturum başlatılmaya çalışılıyorsa hata ver.
    if aktif_oturum["aktif"] and aktif_oturum["sessionId"] != gelen_session_id:
        print("Hata: Zaten aktif bir oturum varken yeni ve farklı bir oturum başlatılamaz.")
        return jsonify({"errorCode": 2, "errorMessage": "Aktif oturum var."})
    
    # Eğer aktif oturum yoksa, yeni bir oturum başlat.
    if not aktif_oturum["aktif"]:
        aktif_oturum = {
            "aktif": True,
            "sessionId": gelen_session_id,
            "userId": gelen_user_id,
            "kabul_edilen_pet": 0,
            "kabul_edilen_cam": 0,
            "kabul_edilen_alu": 0
        }
        print(f"Yeni oturum başlatıldı: {aktif_oturum['sessionId']}")
    
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/acceptPackage', methods=['POST'])
def accept_package():
    """
    DİM DB, okunan bir barkod bilgisini bu metot ile RVM'ye gönderir.
    """
    data = request.json
    print(f"Gelen acceptPackage isteği: {data}")

    if not aktif_oturum["aktif"]:
        return jsonify({"errorCode": 2, "errorMessage": "Aktif Oturum Yok"})

    processing_thread = threading.Thread(target=_process_package_and_send_result, args=(data,))
    processing_thread.start()
    
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/stopOperation', methods=['POST'])
def stop_operation():
    """
    Ölçüm sürecini durdurmak için kullanılır.
    """
    data = request.json
    print(f"Gelen stopOperation isteği: {data}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/sessionEnd', methods=['POST'])
def session_end():
    """
    Aktif depozito işlemini sonlandırmak için çağrılır.
    """
    data = request.json
    print(f"Gelen sessionEnd isteği: {data}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/updateProducts', methods=['POST'])
def update_products():
    """
    RVM'nin ürün listesini çekmesini bildirmek için kullanılır.
    """
    data = request.json
    print(f"Gelen updateProducts isteği: {data}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/resetRvm', methods=['POST'])
def reset_rvm():
    """
    Kontrol Ünitesi üzerinden RVM’i resetlemek için kullanılır.
    """
    data = request.json
    print(f"Gelen resetRvm isteği: {data}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4321, debug=True)

