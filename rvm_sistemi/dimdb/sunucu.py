# rvm_sistemi/dimdb/sunucu.py

from flask import Flask, request, jsonify

# Flask uygulamasını oluştur
app = Flask(__name__)

# Aktif oturum bilgilerini saklamak için basit bir sözlük (dictionary)
# Bu yapı, RVM'nin anlık durumunu tutacak.
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "kabul_edilen_pet": 0,
    "kabul_edilen_cam": 0,
    "kabul_edilen_alu": 0
}

@app.route('/sessionStart', methods=['POST'])
def session_start():
    """
    DİM DB'den oturum başlatma isteği geldiğinde çalışır.
    Gelen sessionId ve userId bilgilerini saklamalıyız.
    """
    global aktif_oturum
    data = request.json
    print(f"Gelen sessionStart isteği: {data}")

    # Eğer zaten aktif bir oturum varsa, hata dön.
    if aktif_oturum["aktif"]:
        print("Hata: Zaten aktif bir oturum varken yeni oturum başlatılamaz.")
        response = {
            "errorCode": 2,  # Dokümandaki "Aktif oturum var" hata kodu
            "errorMessage": "Aktif oturum var."
        }
        return jsonify(response)

    # Oturum bilgilerini güncelle ve sayaçları sıfırla
    aktif_oturum = {
        "aktif": True,
        "sessionId": data.get("sessionId"),
        "userId": data.get("userId"),
        "kabul_edilen_pet": 0,
        "kabul_edilen_cam": 0,
        "kabul_edilen_alu": 0
    }
    
    print(f"Yeni oturum başlatıldı: {aktif_oturum['sessionId']}")

    # DİM DB'ye başarılı cevabı dön
    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

@app.route('/acceptPackage', methods=['POST'])
def accept_package():
    """
    DİM DB, okunan bir barkod bilgisini bu metot ile RVM'ye gönderir.
    """
    data = request.json
    print(f"Gelen acceptPackage isteği: {data}")

    # TODO: RVM'nin fiziksel sensörlerini (ağırlık, boyut vb.) tetikleme ve 
    # ölçüm yapma mantığı burada olacak.
    # Ölçüm sonucuna göre DİM DB'ye `acceptPackageResult` çağrısı yapılacak.

    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

@app.route('/stopOperation', methods=['POST'])
def stop_operation():
    """
    Ölçüm sürecini durdurmak için kullanılır.
    """
    data = request.json
    print(f"Gelen stopOperation isteği: {data}")
    # TODO: Mevcut ölçüm işlemini durdurma mantığı eklenecek.
    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

@app.route('/sessionEnd', methods=['POST'])
def session_end():
    """
    Aktif depozito işlemini sonlandırmak için çağrılır.
    """
    data = request.json
    print(f"Gelen sessionEnd isteği: {data}")
    # TODO: Oturumu sonlandırma ve `transactionResult` gönderme mantığı tetiklenecek.
    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

@app.route('/updateProducts', methods=['POST'])
def update_products():
    """
    RVM'nin ürün listesini çekmesini bildirmek için kullanılır.
    """
    data = request.json
    print(f"Gelen updateProducts isteği: {data}")
    # TODO: istemci.py üzerinden `getAllProducts` metodunu çağırma mantığı eklenecek.
    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

@app.route('/resetRvm', methods=['POST'])
def reset_rvm():
    """
    Kontrol Ünitesi üzerinden RVM’i resetlemek için kullanılır.
    """
    data = request.json
    print(f"Gelen resetRvm isteği: {data}")
    # TODO: RVM'yi yeniden başlatma komutları eklenecek.
    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)


if __name__ == '__main__':
    # Sunucuyu başlat. 
    # host='0.0.0.0' ayarı, ağdaki diğer cihazların (DİM DB) erişebilmesi için gereklidir.
    # Dokümanda belirtilen RVM IP adresi 192.168.53.2 ve port 4321'dir.
    app.run(host='0.0.0.0', port=4321, debug=True)
