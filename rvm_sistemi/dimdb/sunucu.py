# rvm_sistemi/dimdb/sunucu.py

from flask import Blueprint, request, jsonify
from ..yardimcilar.gunluk_kayit import logger
from . import istemci

dimdb_api_sunucusu = Blueprint('dimdb_api_sunucusu', __name__)

@dimdb_api_sunucusu.route('/sessionStart', methods=['POST'])
def session_start():
    """
    DİM DB'den yeni bir iade oturumu başlatma isteği alır.
    ---
    tags:
      - Gelen İstekler (DİM DB -> RVM)
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            guid:
              type: string
              example: "870422ad-4de0-4faf-82fc-eaf56808e599"
            sessionId:
              type: string
              example: "RVM000101-241023-0213"
            userId:
              type: string
              example: "1dytfy3456wsf"
    responses:
      200:
        description: Oturumun başarıyla başlatıldığına dair cevap.
        schema:
          type: object
          properties:
            errorCode:
              type: integer
              example: 0
            errorMessage:
              type: string
              example: ""
    """
    data = request.get_json()
    logger.info(f"GELEN İSTEK: /sessionStart | SessionID: {data.get('sessionId')}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@dimdb_api_sunucusu.route('/acceptPackage', methods=['POST'])
def accept_package():
    """
    Halka okuyucudan geçen ambalajın barkodunu ve bilgilerini alır.
    ---
    tags:
      - Gelen İstekler (DİM DB -> RVM)
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: ["guid", "uuid", "sessionId", "barcode"]
          properties:
            guid:
              type: string
              example: "9db8da13-4f91-4c00-b1f0-0755e8696c54"
            uuid:
              type: string
              example: "9db8da13-4f94-4c02-b1f1-0755e8696c55"
            sessionId:
              type: string
              example: "RVM000101-241023-0213"
            barcode:
              type: string
              example: "9999999999901"
    responses:
      200:
        description: Ambalaj bilgilerinin başarıyla alındığına dair cevap.
        schema:
          type: object
          properties:
            errorCode:
              type: integer
              example: 0
            errorMessage:
              type: string
              example: ""
    """
    data = request.get_json()
    barcode = data.get('barcode')
    session_id = data.get('sessionId')
    uuid = data.get('uuid')
    logger.info(f"GELEN İSTEK: /acceptPackage | Barcode: {barcode}")
    logger.info("Simülasyon: Ambalaj kabul edildi, DİM DB'ye sonuç gönderiliyor...")
    istemci.accept_package_result(
        session_id=session_id,
        gelen_uuid=uuid,
        barcode=barcode,
        result_code=0
    )
    return jsonify({"errorCode": 0, "errorMessage": ""})

@dimdb_api_sunucusu.route('/sessionEnd', methods=['POST'])
def session_end():
    """
    Aktif iade oturumunu sonlandırmak için kullanılır.
    ---
    tags:
      - Gelen İstekler (DİM DB -> RVM)
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: ["guid", "sessionId", "slipData"]
          properties:
            guid:
              type: string
              example: "a7cc4aa6-a21f-438e-af90-0fa5b8ffb0eb"
            sessionId:
              type: string
              description: "Sonlandırılacak oturumun kimliği."
              example: "RVM000101-241023-0213"
            slipData:
              type: string
              description: "Fiş verisi (base64 formatında)."
              example: "iVBORw0KGgoAAAANSUhEUg..."
    responses:
      200:
        description: Oturumun başarıyla sonlandırıldığına dair cevap.
        schema:
          type: object
          properties:
            errorCode:
              type: integer
              example: 0
            errorMessage:
              type: string
              example: ""
    """
    data = request.get_json()
    logger.info(f"GELEN İSTEK: /sessionEnd | SessionID: {data.get('sessionId')}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

@dimdb_api_sunucusu.route('/stopOperation', methods=['POST'])
def stop_operation():
    """
    Ambalaj ölçüm sürecini durdurmak için kullanılır.
    ---
    tags:
      - Gelen İstekler (DİM DB -> RVM)
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: ["guid", "barcode"]
          properties:
            guid:
              type: string
              example: "9db8da13-4f91-4c00-b1f0-0755e8696c54"
            barcode:
              type: string
              description: "İşlemi durdurulacak ambalajın barkodu."
              example: "9999999999901"
    responses:
      200:
        description: İşlemin başarıyla durdurulduğuna dair cevap.
        schema:
          type: object
          properties:
            errorCode:
              type: integer
              example: 0
            errorMessage:
              type: string
              example: ""
    """
    data = request.get_json()
    logger.info(f"GELEN İSTEK: /stopOperation | Barcode: {data.get('barcode')}")
    return jsonify({"errorCode": 0, "errorMessage": ""})

# --- Test Endpoint'leri ---
@dimdb_api_sunucusu.route('/test/checkuser/<string:kullanici_id>')
def test_check_user(kullanici_id):
    logger.info(f"check_user_id testi '{kullanici_id}' için başlatıldı.")
    basarili_mi = istemci.check_user_id(kullanici_id)
    if basarili_mi:
        return f"'{kullanici_id}' için checkUserId isteği gönderildi."
    else:
        return f"'{kullanici_id}' için checkUserId isteği GÖNDERİLEMEDİ.", 500

@dimdb_api_sunucusu.route('/test/sendbarcode/<string:barkod>')
def test_send_barcode(barkod):
    logger.info(f"get_barcode testi '{barkod}' için başlatıldı.")
    basarili_mi = istemci.get_barcode(barkod)
    if basarili_mi:
        return f"'{barkod}' için getBarcode isteği gönderildi. Terminal loglarını kontrol edin."
    else:
        return f"'{barkod}' için getBarcode isteği GÖNDERİLEMEDİ.", 500