import requests
import hmac
import hashlib
import time
import json
import uuid

from ..veri_tabani import veritabani_yoneticisi

# --- GÜVENLİK VE AYARLAR ---
SECRET_KEY = "KRVM00010725"
RVM_ID = "KRVM00010925"
BASE_URL = "http://192.168.53.1:5432"

def _generate_signature_headers(payload_body_str):
    """Verilen bir payload için imza ve timestamp header'larını oluşturur."""
    headers = {}
    encoded_body = payload_body_str.encode('utf-8')
    current_timestamp = str(int(time.time()))
    headers['RVM-DBYS-Signature-Timestamp'] = current_timestamp
    
    digest = hmac.new(SECRET_KEY.encode('utf-8'), encoded_body, hashlib.sha512)
    digest.update(current_timestamp.encode('utf-8'))
    
    headers['RVM-DBYS-Signature'] = digest.hexdigest()
    headers['Content-Type'] = 'application/json'
    return headers

def _send_request(endpoint, payload, timeout=10):
    """DİM-DB'ye güvenli bir POST isteği gönderen yardımcı fonksiyon."""
    url = f"{BASE_URL}/{endpoint}"
    payload_str = json.dumps(payload)
    try:
        headers = _generate_signature_headers(payload_str)
        # --- GÜNCELLEME: Zaman aşımı yazısı kaldırıldı ---
        print(f"İstek gönderiliyor: {url}")
        # ---------------------------------------------
        response = requests.post(url, data=payload_str, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            # --- GÜNCELLEME: Başarılı log mesajına yeşil tik ve kod eklendi ---
            print(f"✅ İstek ({endpoint}) başarıyla gönderildi. Kod: {response.status_code}")
            # -----------------------------------------------------------------
            return response.json() if endpoint == "getAllProducts" else True
        else:
            print(f"❌ İstek ({endpoint}) gönderilemedi. Hata: {response.status_code}, Cevap: {response.text}")
            return None if endpoint == "getAllProducts" else False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ İstek ({endpoint}) gönderilirken ağ hatası oluştu: {e}")
        return None if endpoint == "getAllProducts" else False

# --- DİM DB'YE GÖNDERİLECEK METOTLAR ---

def send_heartbeat():
    """DİM DB'ye RVM'nin anlık durumunu bildirir."""
    print("Heartbeat gönderiliyor...")
    payload = {
        "guid": str(uuid.uuid4()),
        "rvm": RVM_ID,
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "vendorName": "Kapellarvm", 
        "firmwareVersion": "v1.0.1",
        "state": 0,
        "stateMessage": "Sistem Normal",
        "binList": [
            {"binId": 1, "binContentType": "1", "binOccupancyLevel": 0},
            {"binId": 2, "binContentType": "2", "binOccupancyLevel": 0},
            {"binId": 3, "binContentType": "3", "binOccupancyLevel": 0}
        ]
    }
    _send_request("heartbeat", payload)

def send_accept_package_result(result_data):
    """Ölçüm sonucunu DİM DB'ye gönderir."""
    print(f"Paket kabul sonucu gönderiliyor: {result_data['barcode']}")
    _send_request("acceptPackageResult", result_data)

def send_transaction_result(transaction_data):
    """Oturum işlem özetini DİM DB'ye gönderir."""
    print(f"İşlem sonucu (transaction) gönderiliyor: {transaction_data['sessionId']}")
    _send_request("transactionResult", transaction_data)

def get_all_products_and_save():
    """DİM-DB'den ürün listesini alır ve yerel veritabanına kaydeder."""
    payload = {
        "guid": str(uuid.uuid4()),
        "rvm": RVM_ID,
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    # Bu istek uzun sürebileceği için zaman aşımını 60 saniye yapalım
    response_data = _send_request("getAllProducts", payload, timeout=60)
    
    if response_data and 'products' in response_data:
        products = response_data['products']
        print(f"Başarılı: {len(products)} adet ürün bilgisi alındı.")
        veritabani_yoneticisi.urunleri_kaydet(products)
    else:
        print("Ürün listesi alınamadı veya gelen veri boş.")

