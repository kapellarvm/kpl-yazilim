from flask import Flask, request, jsonify
import uuid
import threading
import time
import logging

# Projenin diğer modüllerini doğru paket yolundan import et
from ..veri_tabani import veritabani_yoneticisi
from . import istemci

# Flask'ın kendi loglarını azaltarak terminali temiz tut
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Aktif oturum bilgilerini ve kabul edilen ürünleri saklamak için
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "kabul_edilen_urunler": []
}

# Materyal ID'lerini daha okunaklı hale getirmek için bir sözlük
MATERIAL_MAP = {
    1: "PET",
    2: "Cam (Glass)",
    3: "Alüminyum (Alu)"
}

def is_session_active():
    """Oturumun aktif olup olmadığını kontrol eder."""
    return aktif_oturum["aktif"]

def _process_package_and_send_result(data):
    """
    Bu fonksiyon, gelen paketin barkodunu veritabanında doğrular
    ve sonucu istemci üzerinden DİM DB'ye gönderir.
    """
    barcode = data.get('barcode')
    print(f"Paket işleniyor: {barcode}")

    # --- BARKOD DOĞRULAMA ---
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(barcode)

    if urun_bilgisi:
        # Barkod veritabanında bulundu, ürünü kabul et
        material_id = urun_bilgisi['material']
        material_name = MATERIAL_MAP.get(material_id, "Bilinmeyen")
        
        # --- GÜNCELLEME: Terminal çıktısı daha detaylı hale getirildi ---
        print(f"   -> ONAYLANDI: Barkod ({barcode}) veritabanında bulundu. Materyal: {material_name} (ID: {material_id})")
        # -----------------------------------------------------------------

        result_code = 0
        bin_id = material_id
        result_message = "Ambalaj Kabul Edildi (Veritabanı Doğrulandı)"
        
        aktif_oturum["kabul_edilen_urunler"].append({
            "barcode": urun_bilgisi['barcode'],
            "material": material_id,
            "count": 1,
            "weight": 0
        })
    else:
        # Barkod veritabanında bulunamadı, ürünü reddet
        print(f"   -> REDDEDİLDİ: Barkod ({barcode}) veritabanında bulunamadı.")
        result_code = 15
        bin_id = -1
        result_message = "Ambalaj Reddedildi (Barkod Tanınmıyor)"
        
    # Oturumdaki toplam ürün sayılarını hesapla
    pet_sayisi = sum(1 for urun in aktif_oturum["kabul_edilen_urunler"] if urun['material'] == 1)
    cam_sayisi = sum(1 for urun in aktif_oturum["kabul_edilen_urunler"] if urun['material'] == 2)
    alu_sayisi = sum(1 for urun in aktif_oturum["kabul_edilen_urunler"] if urun['material'] == 3)
        
    # DİM DB'ye gönderilecek sonuç payload'ını oluştur
    result_payload = {
        "guid": str(uuid.uuid4()),
        "uuid": data.get("uuid"),
        "sessionId": data.get("sessionId"),
        "barcode": barcode,
        "measuredPackWeight": 0.0,
        "measuredPackHeight": 0.0,
        "measuredPackWidth": 0.0,
        "binId": bin_id,
        "result": result_code,
        "resultMessage": result_message,
        "acceptedPetCount": pet_sayisi,
        "acceptedGlassCount": cam_sayisi,
        "acceptedAluCount": alu_sayisi
    }
    
    istemci.send_accept_package_result(result_payload)

# --- SUNUCU METOTLARI ---

@app.route('/', methods=['GET'])
def status_check():
    """Sunucunun çalışıp çalışmadığını kontrol etmek için basit bir endpoint."""
    return jsonify({
        "status": "RVM sunucusu çalışıyor",
        "session_active": aktif_oturum["aktif"],
        "session_id": aktif_oturum["sessionId"]
    })

@app.route('/sessionStart', methods=['POST'])
def session_start():
    """DİM DB'den oturum başlatma/güncelleme isteği geldiğinde çalışır."""
    global aktif_oturum
    data = request.json
    print(f"Gelen {request.path} isteği: {data}")

    if aktif_oturum["aktif"] and data.get("sessionId") == aktif_oturum["sessionId"]:
        aktif_oturum["userId"] = data.get("userId")
        print(f"Mevcut oturum güncellendi. Yeni UserId: {aktif_oturum['userId']}")
        print(f"✅ İstek ({request.path}) başarıyla işlendi. Kod: 200")
        return jsonify({"errorCode": 0, "errorMessage": ""})

    if aktif_oturum["aktif"]:
        print("Hata: Zaten aktif bir oturum varken yeni oturum başlatılamaz.")
        return jsonify({"errorCode": 2, "errorMessage": "Aktif oturum var."})

    aktif_oturum = {
        "aktif": True,
        "sessionId": data.get("sessionId"),
        "userId": data.get("userId"),
        "kabul_edilen_urunler": []
    }
    print(f"Yeni oturum başlatıldı: {aktif_oturum['sessionId']}")
    print(f"✅ İstek ({request.path}) başarıyla işlendi. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/acceptPackage', methods=['POST'])
def accept_package():
    """DİM DB, okunan bir barkod bilgisini bu metot ile RVM'ye gönderir."""
    data = request.json
    print(f"Gelen {request.path} isteği: {data}")

    if not aktif_oturum["aktif"]:
        return jsonify({"errorCode": 2, "errorMessage": "Aktif Oturum Yok"})

    processing_thread = threading.Thread(target=_process_package_and_send_result, args=(data,))
    processing_thread.start()
    
    print(f"✅ İstek ({request.path}) alındı ve işleme yönlendirildi. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/sessionEnd', methods=['POST'])
def session_end():
    """DİM DB'den oturumu sonlandırma isteği geldiğinde çalışır."""
    global aktif_oturum
    data = request.json
    print(f"Gelen {request.path} isteği: {data}")
    
    if not aktif_oturum["aktif"] or aktif_oturum["sessionId"] != data.get("sessionId"):
        return jsonify({"errorCode": 2, "errorMessage": "Aktif veya geçerli bir oturum bulunamadı."})
    
    handle_graceful_shutdown()
    
    print(f"✅ İstek ({request.path}) başarıyla işlendi. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

def handle_graceful_shutdown():
    """
    Aktif oturumun işlem özetini (transactionResult) DİM-DB'ye gönderir
    ve yerel oturum durumunu temizler.
    """
    global aktif_oturum
    if not aktif_oturum["aktif"]:
        return

    print("Oturum sonlandırılıyor, işlem özeti hazırlanıyor...")
    
    containers = {}
    for urun in aktif_oturum["kabul_edilen_urunler"]:
        barcode = urun["barcode"]
        if barcode not in containers:
            containers[barcode] = {
                "barcode": barcode,
                "material": urun["material"],
                "count": 0,
                "weight": 0
            }
        containers[barcode]["count"] += 1

    transaction_payload = {
        "guid": str(uuid.uuid4()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "rvm": istemci.RVM_ID,
        "id": aktif_oturum["sessionId"] + "-tx",
        "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "sessionId": aktif_oturum["sessionId"],
        "userId": aktif_oturum["userId"],
        "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "containerCount": len(aktif_oturum["kabul_edilen_urunler"]),
        "containers": list(containers.values())
    }
    
    istemci.send_transaction_result(transaction_payload)
    
    aktif_oturum = {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "kabul_edilen_urunler": []
    }
    print("Yerel oturum temizlendi.")

@app.route('/stopOperation', methods=['POST'])
def stop_operation():
    print(f"Gelen {request.path} isteği: {request.json}")
    print(f"✅ İstek ({request.path}) başarıyla işlendi. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/updateProducts', methods=['POST'])
def update_products():
    print(f"Gelen {request.path} isteği: {request.json}")
    threading.Thread(target=istemci.get_all_products_and_save).start()
    print(f"✅ İstek ({request.path}) alındı ve ürünler güncelleniyor. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@app.route('/resetRvm', methods=['POST'])
def reset_rvm():
    print(f"Gelen {request.path} isteği: {request.json}")
    print(f"✅ İstek ({request.path}) başarıyla işlendi. Kod: 200")
    return jsonify({"errorCode": 0, "errorMessage": ""})

