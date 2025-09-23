# rvm_sistemi/dimdb/istemci.py

import requests
import hmac
import hashlib
import time
import json
import uuid
from ..ayarlar import genel_ayarlar
from ..yardimcilar.gunluk_kayit import logger

# Bu anahtarın size DİM DB entegrasyonu için yetkililer tarafından sağlanması gerekir.
GIZLI_ANAHTAR = "BURAYA_GERCEK_GIZLI_ANAHTAR_GELECEK"

def _imza_olustur(body: dict) -> dict:
    """Verilen bir body için gerekli imza ve zaman damgası başlıklarını oluşturur."""
    data_string = json.dumps(body, separators=(',', ':')) # Boşluksuz JSON
    encoded_data = data_string.encode('utf-8')

    digest = hmac.new(GIZLI_ANAHTAR.encode('utf-8'), encoded_data, hashlib.sha512)

    timestamp = str(int(time.time()))
    digest.update(timestamp.encode('utf-8'))

    signature = digest.hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'RVM-DBYS-Signature-Timestamp': timestamp,
        'RVM-DBYS-Signature': signature
    }
    return headers

def accept_package_result(session_id: str, gelen_uuid: str, barcode: str, result_code: int):
    """
    Ölçülen bir ambalajın sonucunu (kabul/ret) DİM DB'ye bildirir.
    """
    endpoint = f"{genel_ayarlar.DIMDB_API_URL}/acceptPackageResult"

    # Test için varsayılan ölçüm değerleri ekleyelim
    body = {
        "guid": str(uuid.uuid4()),
        "uuid": gelen_uuid,
        "sessionId": session_id,
        "barcode": barcode,
        "measuredPackWeight": 5.90,
        "measuredPackHeight": 15.10,
        "measuredPackWidth": 5.0,
        "binId": 1 if result_code == 0 else -1,
        "result": result_code,
        "resultMessage": "Success" if result_code == 0 else "Rejected",
        "acceptedPetCount": 1,
        "acceptedGlassCount": 3,
        "acceptedAluCount": 2
    }

    try:
        headers = _imza_olustur(body)
        logger.info(f"GIDEN İSTEK: /acceptPackageResult | Barcode: {barcode}, Result: {result_code}")

        response = requests.post(endpoint, headers=headers, json=body, timeout=5)

        if response.status_code == 200:
            logger.info(f"/acceptPackageResult isteği başarıyla gönderildi.")
            return True
        else:
            logger.error(f"/acceptPackageResult isteği başarısız oldu. Status: {response.status_code}, Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"/acceptPackageResult isteği gönderilirken ağ hatası oluştu: {e}")
        return False

def get_barcode(barcode: str):
    """
    Halka okuyucu simülasyonu için DİM DB'ye bir barkod gönderir.
    """
    endpoint = f"{genel_ayarlar.DIMDB_API_URL}/getBarcode"
    body = {"barcode": barcode}

    try:
        headers = _imza_olustur(body)
        logger.info(f"GIDEN İSTEK: /getBarcode | Barcode: {barcode}")
        response = requests.post(endpoint, headers=headers, json=body, timeout=5)

        if response.status_code == 200:
            logger.info(f"/getBarcode isteği başarıyla gönderildi.")
            return True
        else:
            logger.error(f"/getBarcode isteği başarısız oldu. Status: {response.status_code}, Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"/getBarcode isteği gönderilirken ağ hatası oluştu: {e}")
        return False

def check_user_id(user_id: str):
    """Verilen bir kullanıcı kimliğini DİM DB'ye gönderir."""
    endpoint = f"{genel_ayarlar.DIMDB_API_URL}/checkUserId"
    body = {
        "guid": str(uuid.uuid4()),
        "userId": user_id
    }

    try:
        headers = _imza_olustur(body)
        logger.info(f"GIDEN İSTEK: /checkUserId | UserID: {user_id}")
        response = requests.post(endpoint, headers=headers, json=body, timeout=5)

        if response.status_code == 200:
            logger.info(f"/checkUserId isteği başarıyla gönderildi.")
            return True
        else:
            logger.error(f"/checkUserId isteği başarısız oldu. Status: {response.status_code}, Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"/checkUserId isteği gönderilirken ağ hatası oluştu: {e}")
        return False

def get_all_products():
    """
    DİM DB'den tüm ürünlerin listesini çeker.
    """
    endpoint = f"{genel_ayarlar.DIMDB_API_URL}/getAllProducts"

    body = {
        "guid": str(uuid.uuid4()),
        "rvm": "KRVM00010725",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

    try:
        headers = _imza_olustur(body)
        logger.info(f"GIDEN İSTEK: /getAllProducts")

        response = requests.post(endpoint, headers=headers, json=body, timeout=15) # Veri büyük olabileceği için timeout'u biraz artırdık

        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            logger.info(f"/getAllProducts isteği başarılı. {len(products)} adet ürün bilgisi alındı.")
            # İsterseniz tüm ürünleri loglamak için aşağıdaki satırı aktif edebilirsiniz
            # logger.debug(products) 
            return products
        else:
            logger.error(f"/getAllProducts isteği başarısız oldu. Status: {response.status_code}, Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"/getAllProducts isteği gönderilirken ağ hatası oluştu: {e}")
        return None


def send_heartbeat():
    """
    RVM'nin anlık durumunu DİM DB'ye bildiren heartbeat mesajını gönderir.
    """
    endpoint = f"{genel_ayarlar.DIMDB_API_URL}/heartbeat"
    
    # GERÇEK VERİLERLE GÜNCELLENMİŞ BODY
    body = {
        "guid": str(uuid.uuid4()),
        "rvm": "KRVM00010725",             # <-- GERÇEK SERİ NUMARASI
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "vendorName": "KapellaRvm",          # <-- GERÇEK ÜRETİCİ ADI
        "firmwareVersion": "v1.0.1",          # <-- GERÇEK YAZILIM VERSİYONU
        "state": 0,                         # 0: Operasyonel
        "stateMessage": "Sistem Normal",
        "binList": [
            # TODO: Bu bölüm, makine modülünden gelen gerçek hazne doluluk
            # bilgileriyle dinamik olarak doldurulmalıdır.
            {
                "binId": 1,
                "binContentType": "1", # 1: Pet
                "binOccupancyLevel": 0
            },
            {
                "binId": 2,
                "binContentType": "2", # 2: Cam
                "binOccupancyLevel": 0
            },
            {
                "binId": 3,
                "binContentType": "3", # 3: Alüminyum
                "binOccupancyLevel": 0
            }
        ]
    }

    try:
        headers = _imza_olustur(body)
        logger.info(f"GIDEN İSTEK: /heartbeat")

        response = requests.post(endpoint, headers=headers, json=body, timeout=10)

        if response.status_code == 200:
            logger.info(f"/heartbeat isteği başarıyla gönderildi.")
            return True
        else:
            logger.error(f"/heartbeat isteği başarısız oldu. Status: {response.status_code}, Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"/heartbeat isteği gönderilirken ağ hatası oluştu: {e}")
        return False