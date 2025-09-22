
from flask import Blueprint, request, jsonify
from ..yardimcilar.gunluk_kayit import logger

# Flask Blueprint'i, bu API rotalarını ana uygulamadan ayırmak için kullanıyoruz.
# Bu, tüm DIM-DB'den gelen istekler için ana yönlendiricimiz olacak.
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

    # TODO: Gelen sessionId ve userId ile makine durumunu "çalışıyor" moduna geçir.

    response = {
        "errorCode": 0,
        "errorMessage": ""
    }
    return jsonify(response)

# /acceptPackage, /sessionEnd, /stopOperation gibi diğer metotlar buraya eklenecek...