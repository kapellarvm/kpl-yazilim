import httpx
import hmac
import hashlib
import time
import json
import uuid

# Projenin diğer modüllerini doğru paket yolundan import et
# Bu dosya 'dimdb' paketi içinde olduğu için, bir üst dizindeki 'veri_tabani' paketine
# göreceli (relative) yoldan erişiyoruz.
from ..veri_tabani import veritabani_yoneticisi
from ..utils.logger import log_dimdb, log_error, log_success, log_warning, log_system

# --- GÜVENLİK VE AYARLAR ---
SECRET_KEY = "testkpl"
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

async def _send_request(endpoint, payload, timeout=10.0):
    """DİM-DB'ye güvenli bir POST isteği gönderen asenkron yardımcı fonksiyon."""
    url = f"{BASE_URL}/{endpoint}"
    payload_str = json.dumps(payload)
    headers = _generate_signature_headers(payload_str)
    
    print(f"İstek gönderiliyor: {url}")
    log_dimdb(f"İstek gönderiliyor: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, content=payload_str, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            print(f"✅ İstek ({endpoint}) başarıyla gönderildi. Kod: 200")
            log_success(f"İstek ({endpoint}) başarıyla gönderildi. Kod: 200")
            # getAllProducts json cevabı döner, diğerleri sadece başarı durumu
            return response.json() if "getAllProducts" in endpoint else True
        else:
            print(f"İstek ({endpoint}) gönderilemedi. Hata: {response.status_code}, Cevap: {response.text}")
            log_error(f"İstek ({endpoint}) gönderilemedi. Hata: {response.status_code}, Cevap: {response.text}")
            return None if "getAllProducts" in endpoint else False
            
    except httpx.RequestError as e:
        print(f"İstek ({endpoint}) gönderilirken ağ hatası oluştu: {e}")
        log_error(f"İstek ({endpoint}) gönderilirken ağ hatası oluştu: {e}")
        return None if "getAllProducts" in endpoint else False

# --- DİM DB'YE GÖNDERİLECEK METOTLAR ---

async def send_heartbeat():
    """DİM DB'ye RVM'nin anlık durumunu bildirir."""
    print("Heartbeat gönderiliyor...")
    log_dimdb("Heartbeat gönderiliyor...")
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
    await _send_request("heartbeat", payload)

async def send_accept_package_result(result_data):
    """Ölçüm sonucunu DİM DB'ye gönderir."""
    print(f"Paket kabul sonucu gönderiliyor: {result_data['barcode']}")
    await _send_request("acceptPackageResult", result_data)

async def send_transaction_result(transaction_data):
    """Oturum işlem özetini DİM DB'ye gönderir."""
    print(f"İşlem sonucu (transaction) gönderiliyor: {transaction_data['sessionId']}")
    await _send_request("transactionResult", transaction_data)

async def send_alarm(alarm_code, alarm_message):
    """DİM DB'ye RVM'de oluşan alarm durumlarını bildirir."""
    print(f"Alarm gönderiliyor: {alarm_code} - {alarm_message}")
    payload = {
        "guid": str(uuid.uuid4()),
        "rvm": RVM_ID,
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "alarmCode": alarm_code,
        "alarmMessage": alarm_message
    }
    await _send_request("alarm", payload)

async def get_all_products_and_save():
    """DİM-DB'den ürün listesini alır ve yerel veritabanına kaydeder."""
    print("Ürün listesi isteniyor...")
    payload = {
        "guid": str(uuid.uuid4()),
        "rvm": RVM_ID,
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    # Bu istek uzun sürebileceği için zaman aşımı süresini artırıyoruz.
    response_data = await _send_request("getAllProducts", payload, timeout=60.0)
    
    if response_data and 'products' in response_data:
        products = response_data['products']
        print(f"Başarılı: {len(products)} adet ürün bilgisi alındı.")
        veritabani_yoneticisi.urunleri_kaydet(products)
    else:
        print("Ürün listesi alınamadı veya gelen veri boş.")

