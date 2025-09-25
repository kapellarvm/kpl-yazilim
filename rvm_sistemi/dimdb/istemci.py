# rvm_sistemi/dimdb/istemci.py

import requests
import hmac
import hashlib
import time
import json
import uuid  # guid için benzersiz ID oluşturmak amacıyla

# --- GÜVENLİK VE AYARLAR ---

# Bu anahtar, DİM DB ile aranızda kararlaştırılan gizli anahtardır.
# Güvenli bir yerden (örn: config dosyası) okunmalıdır.
SECRET_KEY = "KRVM00010725"

# DİM DB Kontrol Ünitesi'nin ana adresi
BASE_URL = "http://192.168.53.1:5432"


def _generate_signature_headers(payload_body_str):
    """
    Verilen bir payload için imza ve timestamp header'larını oluşturur.
    Dokümandaki imzalama örneğine göre hazırlanmıştır.
    """
    headers = {}
    encoded_body = payload_body_str.encode('utf-8')
    
    # Zaman damgasını oluştur
    current_timestamp = str(int(time.time()))
    headers['RVM-DBYS-Signature-Timestamp'] = current_timestamp
    
    # İmzayı oluştur
    digest = hmac.new(SECRET_KEY.encode('utf-8'), encoded_body, hashlib.sha512)
    digest.update(current_timestamp.encode('utf-8'))
    
    headers['RVM-DBYS-Signature'] = digest.hexdigest()
    headers['Content-Type'] = 'application/json'
    
    return headers

# --- DİM DB'YE GÖNDERİLECEK METOTLAR ---
def send_accept_package_result(result_data):
    """
    Ölçüm sonucunu DİM DB'ye gönderir.
    Bu fonksiyon sunucu tarafından (sunucu.py) çağrılır.
    """
    print(f"Paket kabul sonucu gönderiliyor: {result_data['barcode']}")
    
    payload_str = json.dumps(result_data)
    
    try:
        headers = _generate_signature_headers(payload_str)
        response = requests.post(
            f"{BASE_URL}/acceptPackageResult", 
            data=payload_str, 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"Paket sonucu ({result_data['barcode']}) başarıyla gönderildi.")
        else:
            print(f"Paket sonucu gönderilemedi. Hata Kodu: {response.status_code}, Cevap: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Paket sonucu gönderilirken bir ağ hatası oluştu: {e}")

def send_heartbeat():
    """
    DİM DB'ye RVM'nin anlık durumunu bildiren heartbeat mesajını gönderir.
    ana.py tarafından her 60 saniyede bir çağrılır.
    """
    print("Heartbeat gönderiliyor...")
    
    # Dokümanda belirtilen heartbeat payload'ını oluştur
    payload = {
    "guid": str(uuid.uuid4()),
    "rvm": "KRVM00010725",
    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    "vendorName": "kapellarvm", # Kendi firma adınız
    "firmwareVersion": "v1.0.1",
    "state": 0,
    "stateMessage": "Sistem Normal",
    "binList": [
        {
            "binId": 1,
            "binContentType": "1",
            "binOccupancyLevel": 75
        },
        {
            "binId": 2,
            "binContentType": "2",
            "binOccupancyLevel": 50
        }
    ]
}

    # Payload'ı JSON string formatına çevir
    payload_str = json.dumps(payload)
    
    try:
        # İmza ve diğer header'ları oluştur
        headers = _generate_signature_headers(payload_str)
        
        # POST isteğini gönder
        response = requests.post(f"{BASE_URL}/heartbeat", data=payload_str, headers=headers, timeout=10)
        
        # Cevabı kontrol et
        if response.status_code == 200:
            print("Heartbeat başarıyla gönderildi.")
        else:
            print(f"Heartbeat gönderilemedi. Hata Kodu: {response.status_code}, Cevap: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Heartbeat gönderilirken bir ağ hatası oluştu: {e}")

# Bu dosyayı doğrudan test etmek için aşağıdaki bloğu kullanabilirsiniz.
if __name__ == '__main__':
    send_heartbeat()