# DİM-DB Sunucu - Sadece DİM-DB işlemleri
# Diğer API endpoint'leri artık rvm_sistemi.api paketinde

from ..makine.senaryolar import oturum_var
from . import dimdb_istemcisi
import uuid
import time
import asyncio

# --- DİM-DB BİLDİRİM FONKSİYONLARI ---

async def send_package_result(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji):
    """Her ürün doğrulaması sonrası DİM-DB'ye paket sonucunu gönderir"""
    if not oturum_var.sistem.aktif_oturum["aktif"]:
        print("⚠️ [DİM-DB] Aktif oturum yok, paket sonucu gönderilmedi")
        return
    
    try:
        # UUID'yi al
        paket_uuid = oturum_var.sistem.aktif_oturum["paket_uuid_map"].get(barcode, str(uuid.uuid4()))
        
        # Kabul edilen ürün sayılarını hesapla
        pet_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 1)
        cam_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 2)
        alu_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 3)
        
        result_payload = {
            "guid": str(uuid.uuid4()),
            "uuid": paket_uuid,
            "sessionId": oturum_var.sistem.aktif_oturum["sessionId"],
            "barcode": barcode,
            "measuredPackWeight": float(agirlik),
            "measuredPackHeight": float(uzunluk),
            "measuredPackWidth": float(genislik),
            "binId": materyal_turu if kabul_edildi else -1,
            "result": sebep_kodu,
            "resultMessage": sebep_mesaji,
            "acceptedPetCount": pet_sayisi,
            "acceptedGlassCount": cam_sayisi,
            "acceptedAluCount": alu_sayisi
        }
        
        await dimdb_istemcisi.send_accept_package_result(result_payload)
        print(f"✅ [DİM-DB] Paket sonucu başarıyla gönderildi: {barcode} - {'Kabul' if kabul_edildi else 'Red'}")
        
    except Exception as e:
        print(f"❌ [DİM-DB] Paket sonucu gönderme hatası: {e}")
        import traceback
        print(f"❌ [DİM-DB] Hata detayı: {traceback.format_exc()}")

def send_package_result_sync(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji):
    """Thread-safe DİM-DB paket sonucu gönderimi"""
    try:
        # Yeni event loop oluştur ve çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_package_result(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji))
        finally:
            loop.close()
    except Exception as e:
        print(f"❌ [DİM-DB SYNC] Hata: {e}")

def dimdb_bildirim_gonder(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji):
    """DİM-DB'ye bildirim gönderir"""
    try:
        send_package_result_sync(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji)
    except Exception as e:
        print(f"❌ [DİM-DB BİLDİRİM] Hata: {e}")

async def send_transaction_result():
    """Oturum sonlandığında DİM-DB'ye transaction result gönderir"""
    if not oturum_var.sistem.aktif_oturum["aktif"]:
        print("⚠️ [DİM-DB] Aktif oturum yok, transaction result gönderilmedi")
        return
    
    try:
        # Kabul edilen ürünleri konteyner formatına dönüştür
        containers = {}
        for urun in oturum_var.sistem.onaylanan_urunler:
            barcode = urun["barkod"]
            if barcode not in containers:
                containers[barcode] = {
                    "barcode": barcode,
                    "material": urun["materyal_turu"],
                    "count": 0,
                    "weight": 0
                }
            containers[barcode]["count"] += 1
            containers[barcode]["weight"] += urun["agirlik"]
        
        transaction_payload = {
            "guid": str(uuid.uuid4()),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "rvm": dimdb_istemcisi.RVM_ID,
            "id": oturum_var.sistem.aktif_oturum["sessionId"] + "-tx",
            "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "sessionId": oturum_var.sistem.aktif_oturum["sessionId"],
            "userId": oturum_var.sistem.aktif_oturum["userId"],
            "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "containerCount": len(oturum_var.sistem.onaylanan_urunler),
            "containers": list(containers.values())
        }
        
        await dimdb_istemcisi.send_transaction_result(transaction_payload)
        print(f"✅ [DİM-DB] Transaction result başarıyla gönderildi: {oturum_var.sistem.aktif_oturum['sessionId']}")
        
        # Kullanıcı puan özeti
        pet_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 1)
        cam_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 2)
        alu_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 3)
        
        print(f"📊 [OTURUM PUAN ÖZETİ] *********** Kullanıcı: {oturum_var.sistem.aktif_oturum['userId']} | PET: {pet_sayisi} puan | CAM: {cam_sayisi} puan | ALÜMİNYUM: {alu_sayisi} puan *************")
        
    except Exception as e:
        print(f"❌ [DİM-DB] Transaction result gönderme hatası: {e}")
        import traceback
        print(f"❌ [DİM-DB] Hata detayı: {traceback.format_exc()}")

# --- OTURUM YÖNETİMİ FONKSİYONLARI ---

def oturum_baslat(session_id, user_id):
    """DİM-DB'den gelen oturum başlatma"""
    oturum_var.sistem.aktif_oturum = {
        "aktif": True,
        "sessionId": session_id,
        "userId": user_id,
        "paket_uuid_map": {}
    }
    
    print(f"✅ [OTURUM] DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

def oturum_sonlandir():
    """Oturumu sonlandır - DİM-DB bildirimi sunucu tarafından yapılacak"""
    from ..makine.uyari_yoneticisi import uyari_yoneticisi
    
    uyari_yoneticisi.uyari_kapat()
    oturum_var.sistem.sensor_ref.tare()
    
    if not oturum_var.sistem.aktif_oturum["aktif"]:
        print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
        return

    print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {oturum_var.sistem.aktif_oturum['sessionId']}")
    
    # Oturumu temizle
    oturum_var.sistem.aktif_oturum = {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    }
    
    oturum_var.sistem.onaylanan_urunler.clear()
    print(f"🧹 [OTURUM] Yerel oturum temizlendi")

# Heartbeat sistemi
heartbeat_task = None

async def start_heartbeat():
    """Heartbeat sistemini başlatır"""
    global heartbeat_task
    if heartbeat_task is None:
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        print("✅ [DİM-DB] Heartbeat sistemi başlatıldı")

async def stop_heartbeat():
    """Heartbeat sistemini durdurur"""
    global heartbeat_task
    if heartbeat_task:
        heartbeat_task.cancel()
        heartbeat_task = None
        print("🛑 [DİM-DB] Heartbeat sistemi durduruldu")

async def heartbeat_loop():
    """60 saniyede bir heartbeat gönderir"""
    while True:
        try:
            await dimdb_istemcisi.send_heartbeat()
            await asyncio.sleep(60)  # 60 saniye bekle
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ [DİM-DB] Heartbeat hatası: {e}")
            await asyncio.sleep(60)  # Hata durumunda da 60 saniye bekle