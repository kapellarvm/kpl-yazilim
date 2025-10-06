from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uuid
import time
import asyncio
import threading
from contextlib import asynccontextmanager

# Projenin diğer modüllerini doğru paket yolundan import et
from ..makine.durum_degistirici import durum_makinesi # Merkezi durum makinesini import et
from ..makine import kart_referanslari  # Merkezi kart referansları
from ..makine.senaryolar import oturum_var  # Oturum yönetimi için
from . import istemci

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlatma
    print("RVM Sunucusu başlatılıyor...")
    
    # DİM-DB bildirim fonksiyonu artık direkt import ile kullanılıyor
    
    # Heartbeat sistemini başlat
    await start_heartbeat()
    
    yield
    
    # Uygulama kapatılırken heartbeat'i durdur
    await stop_heartbeat()
    print("\nUygulama kapatılıyor...")
    
app = FastAPI(title="RVM Sunucusu", lifespan=lifespan)

# Log filtreleme middleware'i
@app.middleware("http")
async def log_filter(request: Request, call_next):
    # Sistem durumu isteklerini loglamayı atla
    if request.url.path == "/api/sistem-durumu":
        # Sessizce işle
        response = await call_next(request)
        return response
    else:
        # Diğer istekleri normal logla
        response = await call_next(request)
        return response

# Static dosyalar\u0131 serve et (iste\u011fe ba\u011fl\u0131)
try:
    import os
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    print(f"Static dosya yolu: {static_path}")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
        print("Static dosyalar ba\u015far\u0131yla y\u00fcklendi.")
    else:
        print(f"Static klas\u00f6r bulunamad\u0131: {static_path}")
except Exception as e:
    print(f"Static dosyalar y\u00fcklenemedi: {e}")

# --- Pydantic Modelleri ve Oturum Yönetimi ---
class SessionStartRequest(BaseModel): guid: str; sessionId: str; userId: str
class AcceptPackageRequest(BaseModel): guid: str; uuid: str; sessionId: str; barcode: str
class SessionEndRequest(BaseModel): guid: str; sessionId: str; slipData: str
class StopOperationRequest(BaseModel): guid: str; barcode: str
class UpdateProductsRequest(BaseModel): guid: str; rvm: str; timestamp: str
class ResetRvmRequest(BaseModel): guid: str; rvm: str; timestamp: str

# NOT: Paket işleme ve oturum yönetimi artık oturum_var.py'de yapılıyor
# NOT: DogrulamaServisi artık kullanılmıyor, doğrulama oturum_var.py'de yapılıyor

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
        
        # DEBUG: Paket sonucu bilgilerini göster
        print(f"\n🔍 [PACKAGE DEBUG] Barkod: {barcode}")
        print(f"🔍 [PACKAGE DEBUG] Ağırlık: {agirlik}g")
        print(f"🔍 [PACKAGE DEBUG] Materyal: {materyal_turu}")
        print(f"🔍 [PACKAGE DEBUG] Uzunluk: {uzunluk}mm")
        print(f"🔍 [PACKAGE DEBUG] Genişlik: {genislik}mm")
        print(f"🔍 [PACKAGE DEBUG] Sonuç: {'Kabul' if kabul_edildi else 'Red'} (Kod: {sebep_kodu})")
        print(f"🔍 [PACKAGE DEBUG] Mesaj: {sebep_mesaji}")
        print(f"🔍 [PACKAGE DEBUG] Mevcut sayılar - PET: {pet_sayisi}, CAM: {cam_sayisi}, ALU: {alu_sayisi}")
        
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
        
        await istemci.send_accept_package_result(result_payload)
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
        # DEBUG: Detaylı bilgileri göster
        #print(f"\n🔍 [TRANSACTION DEBUG] Oturum: {oturum_var.sistem.aktif_oturum['sessionId']}")
        #print(f"🔍 [TRANSACTION DEBUG] Kullanıcı: {oturum_var.sistem.aktif_oturum['userId']}")
        #print(f"🔍 [TRANSACTION DEBUG] Toplam kabul edilen ürün sayısı: {len(oturum_var.sistem.onaylanan_urunler)}")
        
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
        
        # DEBUG: Konteyner bilgilerini göster
        #print(f"🔍 [TRANSACTION DEBUG] Konteyner sayısı: {len(containers)}")
        for barcode, container in containers.items():
            #print(f"🔍 [TRANSACTION DEBUG] - {barcode}: {container['count']} adet, {container['weight']}g, materyal: {container['material']}")
        
        transaction_payload = {
            "guid": str(uuid.uuid4()),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "rvm": istemci.RVM_ID,
            "id": oturum_var.sistem.aktif_oturum["sessionId"] + "-tx",
            "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "sessionId": oturum_var.sistem.aktif_oturum["sessionId"],
            "userId": oturum_var.sistem.aktif_oturum["userId"],
            "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "containerCount": len(oturum_var.sistem.onaylanan_urunler),
            "containers": list(containers.values())
        }
        
        # DEBUG: Gönderilecek payload'ı göster
       ''' print(f"🔍 [TRANSACTION DEBUG] Gönderilecek payload:")
        print(f"🔍 [TRANSACTION DEBUG] - RVM ID: {transaction_payload['rvm']}")
        print(f"🔍 [TRANSACTION DEBUG] - Session ID: {transaction_payload['sessionId']}")
        print(f"🔍 [TRANSACTION DEBUG] - User ID: {transaction_payload['userId']}")
        print(f"🔍 [TRANSACTION DEBUG] - Container Count: {transaction_payload['containerCount']}")
        print(f"🔍 [TRANSACTION DEBUG] - Timestamp: {transaction_payload['timestamp']}")
        '''
        
        await istemci.send_transaction_result(transaction_payload)
        print(f"✅ [DİM-DB] Transaction result başarıyla gönderildi: {oturum_var.sistem.aktif_oturum['sessionId']}")
        
    except Exception as e:
        print(f"❌ [DİM-DB] Transaction result gönderme hatası: {e}")
        import traceback
        print(f"❌ [DİM-DB] Hata detayı: {traceback.format_exc()}")

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
            await istemci.send_heartbeat()
            await asyncio.sleep(60)  # 30 saniye bekle
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ [DİM-DB] Heartbeat hatası: {e}")
            await asyncio.sleep(60)  # Hata durumunda da 30 saniye bekle

# --- API Uç Noktaları (Endpoints) ---

@app.post("/sessionStart")
async def session_start(data: SessionStartRequest):
    print(f"Gelen /sessionStart isteği: {data.model_dump_json()}")
    
    # oturum_var.py'deki oturum durumunu kontrol et
    if oturum_var.sistem.aktif_oturum["aktif"]:
       return {"errorCode": 2, "errorMessage": "Aktif oturum var."}

    # sunucu.py'deki oturum başlatma fonksiyonunu çağır
    oturum_baslat(data.sessionId, data.userId)
    
    # Durum makinesini güncelle
    durum_makinesi.durum_degistir("oturum_var")
    
    print(f"✅ /sessionStart isteği kabul edildi. Yeni oturum: {data.sessionId}")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/acceptPackage")
async def accept_package(data: AcceptPackageRequest):
    if durum_makinesi.durum != "oturum_var":
        print(f"UYARI: Makine '{durum_makinesi.durum}' durumundayken paket kabul edilemez.")
        return {"errorCode": 3, "errorMessage": "Makine paket kabul etmeye hazır değil."}

    print(f"Gelen /acceptPackage isteği: {data.barcode}")
    
    # Barkodu oturum_var.py'ye gönder - tüm doğrulama ve DİM-DB bildirimi orada yapılacak
    oturum_var.barkod_verisi_al(data.barcode)
    
    return {"errorCode": 0, "errorMessage": "Package processing started"}

@app.post("/sessionEnd")
async def session_end(data: SessionEndRequest):
    print(f"Gelen /sessionEnd isteği: {data.model_dump_json()}")
    
    # oturum_var.py'deki oturum durumunu kontrol et
    if not oturum_var.sistem.aktif_oturum["aktif"] or oturum_var.sistem.aktif_oturum["sessionId"] != data.sessionId:
        return {"errorCode": 2, "errorMessage": "Aktif veya geçerli bir oturum bulunamadı."}
    
    # DİM-DB'ye transaction result gönder
    await send_transaction_result()
    
    # sunucu.py'deki oturum sonlandırma fonksiyonunu çağır
    oturum_sonlandir()
    
    # Durum makinesini güncelle
    durum_makinesi.durum_degistir("oturum_yok")
    
    print(f"✅ /sessionEnd isteği kabul edildi. Oturum kapatıldı: {data.sessionId}")
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/maintenanceMode")
async def maintenanceMode():
    print("Bakım Modu Aktif")
    # DÜZELTME: Doğru nesne ve metot adını kullan
    durum_makinesi.durum_degistir("bakim")
    return {"errorCode": 0, "errorMessage": "Bakım moduna geçildi"}

@app.post("/stopOperation")
async def stop_operation(data: StopOperationRequest):
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/updateProducts")
async def update_products(data: UpdateProductsRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(istemci.get_all_products_and_save)
    return {"errorCode": 0, "errorMessage": ""}

@app.post("/resetRvm")
async def reset_rvm(data: ResetRvmRequest):
    return {"errorCode": 0, "errorMessage": ""}

# --- GÜNCELLEME GEÇMİŞİ API ENDPOINT'LERİ ---

@app.get("/api/guncelleme-gecmisi")
async def guncelleme_gecmisi(limit: int = 10):
    """Son N adet ürün güncelleme geçmişini döndürür"""
    from ..veri_tabani import veritabani_yoneticisi
    gecmis = veritabani_yoneticisi.guncelleme_gecmisini_getir(limit)
    return {"status": "success", "data": gecmis, "count": len(gecmis)}

@app.get("/api/son-guncelleme")
async def son_guncelleme():
    """En son yapılan ürün güncellemesi bilgisini döndürür"""
    from ..veri_tabani import veritabani_yoneticisi
    bilgi = veritabani_yoneticisi.son_guncelleme_bilgisi()
    if bilgi:
        return {"status": "success", "data": bilgi}
    else:
        return {"status": "error", "message": "Henüz güncelleme yapılmadı"}

@app.get("/api/guncelleme-istatistikleri")
async def guncelleme_istatistikleri():
    """Ürün güncellemeleri hakkında istatistik bilgisi döndürür"""
    from ..veri_tabani import veritabani_yoneticisi
    istatistikler = veritabani_yoneticisi.guncelleme_istatistikleri()
    return {"status": "success", "data": istatistikler}

# --- BAKIM EKRANI API ENDPOINT'LERİ ---

@app.get("/")
async def ana_sayfa():
    """Test endpoint'i"""
    return {"message": "RVM Sunucusu çalışıyor!", "bakim_ekrani": "/bakim"}

@app.get("/bakim")
async def bakim_ekrani():
    """Bakım ekranı HTML sayfasını döndürür"""
    import os
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "bakim.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Bakım ekranı dosyası bulunamadı</h1>", status_code=404)

@app.get("/uyari")
async def uyari_ekrani(mesaj: str = "Lütfen şişeyi alınız", sure: int = 2):
    """Uyarı ekranı HTML sayfasını döndürür"""
    import os
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uyari.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Mesaj ve süre parametrelerini HTML'e aktar
            html_content = html_content.replace("{{MESAJ}}", mesaj)
            html_content = html_content.replace("{{SURE}}", str(sure))
            return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Uyarı: {mesaj}</h1><p>{sure} saniye sonra kapanacak</p>", status_code=404)

@app.post("/api/motor/konveyor-ileri")
async def konveyor_ileri():
    """Konveyörü ileri hareket ettirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.konveyor_ileri()
        return {"status": "success", "message": "Konveyör ileri hareket ediyor"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/konveyor-geri")
async def konveyor_geri():
    """Konveyörü geri hareket ettirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.konveyor_geri()
        return {"status": "success", "message": "Konveyör geri hareket ediyor"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/konveyor-dur")
async def konveyor_dur():
    """Konveyörü durdurur"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.konveyor_dur()
        return {"status": "success", "message": "Konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/motorlari-aktif")
async def motorlari_aktif():
    """Motorları aktif eder"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.motorlari_aktif_et()
        return {"status": "success", "message": "Motorlar aktif edildi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/motorlari-iptal")
async def motorlari_iptal():
    """Motorları iptal eder"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.motorlari_iptal_et()
        return {"status": "success", "message": "Motorlar iptal edildi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/yonlendirici-plastik")
async def yonlendirici_plastik():
    """Yönlendiriciyi plastik pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.yonlendirici_plastik()
        # Yönlendirici işleminden sonra konveyörü durdur
        import asyncio
        await asyncio.sleep(0.7)  # 200ms bekleme (gömülü sistem için)
        motor.konveyor_dur()
        return {"status": "success", "message": "Yönlendirici plastik pozisyonunda, konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/yonlendirici-cam")
async def yonlendirici_cam():
    """Yönlendiriciyi cam pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.yonlendirici_cam()
        # Yönlendirici işleminden sonra konveyörü durdur
        import asyncio
        await asyncio.sleep(0.7)  # 200ms bekleme (gömülü sistem için)
        motor.konveyor_dur()
        return {"status": "success", "message": "Yönlendirici cam pozisyonunda, konveyör durduruldu"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/klape-metal")
async def klape_metal():
    """Klapeyi metal pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.klape_metal()
        return {"status": "success", "message": "Klape metal pozisyonunda"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.post("/api/motor/klape-plastik")
async def klape_plastik():
    """Klapeyi plastik pozisyonuna getirir"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_gonder()  # Önce parametreleri gönder
        import time
        time.sleep(0.1)
        motor.klape_plastik()
        return {"status": "success", "message": "Klape plastik pozisyonunda"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

class MotorParametreleri(BaseModel):
    konveyor_hizi: int = None
    yonlendirici_hizi: int = None
    klape_hizi: int = None

@app.post("/api/motor/parametreler")
async def motor_parametreleri(params: MotorParametreleri):
    """Motor hızlarını ayarlar"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.parametre_degistir(
            konveyor=params.konveyor_hizi, 
            yonlendirici=params.yonlendirici_hizi, 
            klape=params.klape_hizi
        )
        motor.parametre_gonder()
        return {"status": "success", "message": "Parametreler güncellendi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

@app.get("/api/sistem-durumu")
async def sistem_durumu():
    """Sistem durumunu döndürür"""
    motor_baglanti = False
    sensor_baglanti = False
    motor_hizlari = {"konveyor": 0, "yonlendirici": 0, "klape": 0}
    
    # Motor kontrolü
    motor = kart_referanslari.motor_al()
    if motor:
        try:
            motor_baglanti = motor.getir_saglik_durumu()
            motor_hizlari = {
                "konveyor": motor.konveyor_hizi,
                "yonlendirici": motor.yonlendirici_hizi,
                "klape": motor.klape_hizi
            }
        except:
            pass
    
    # Sensör kontrolü
    sensor = kart_referanslari.sensor_al()
    if sensor:
        try:
            sensor_baglanti = sensor.getir_saglik_durumu()
        except:
            pass
    
    return {
        "motor_baglanti": motor_baglanti,
        "sensor_baglanti": sensor_baglanti,
        "mevcut_durum": durum_makinesi.durum,
        "motor_hizlari": motor_hizlari
    }

@app.post("/api/bakim-modu")
async def bakim_modu(aktif: bool):
    """Bakım modunu aktif/pasif eder"""
    try:
        if aktif:
            durum_makinesi.durum_degistir("bakim")
            return {"status": "success", "message": "Bakım modu aktif edildi"}
        else:
            durum_makinesi.durum_degistir("oturum_yok")
            return {"status": "success", "message": "Bakım modu pasif edildi, sistem normal moda döndü"}
    except Exception as e:
        return {"status": "error", "message": f"Bakım modu hatası: {str(e)}"}

class BakimModuRequest(BaseModel):
    aktif: bool

@app.post("/api/bakim-modu-ayarla")
async def bakim_modu_ayarla(request: BakimModuRequest):
    """Bakım modunu aktif/pasif eder"""
    try:
        if request.aktif:
            # Durum makinesine bakım moduna geç - otomatik ekran değişimi yapılacak
            durum_makinesi.durum_degistir("bakim")
            return {"status": "success", "message": "Bakım modu aktif edildi, ekran açıldı", "durum": "bakim"}
        else:
            # Durum makinesine normal moda geç - otomatik ana ekrana dönülecek
            durum_makinesi.durum_degistir("oturum_yok")
            return {"status": "success", "message": "Bakım modu pasif edildi, ana ekrana dönüldü", "durum": "oturum_yok"}
    except Exception as e:
        return {"status": "error", "message": f"Bakım modu hatası: {str(e)}"}

class BakimUrlRequest(BaseModel):
    url: str

@app.post("/api/bakim-url-ayarla")
async def bakim_url_ayarla(request: BakimUrlRequest):
    """Bakım ekranı URL'ini ayarlar"""
    try:
        durum_makinesi.bakim_url = request.url
        return {"status": "success", "message": f"Bakım URL'i güncellendi: {request.url}"}
    except Exception as e:
        return {"status": "error", "message": f"URL ayarlama hatası: {str(e)}"}

@app.get("/api/bakim-url")
async def bakim_url_getir():
    """Mevcut bakım URL'ini döndürür"""
    return {"status": "success", "url": durum_makinesi.bakim_url}

class UyariRequest(BaseModel):
    mesaj: str = "Lütfen şişeyi alınız"
    sure: int = 2

@app.post("/api/uyari-goster")
async def uyari_goster(request: UyariRequest):
    """Hızlı uyarı gösterir - belirtilen süre sonra otomatik kapanır"""
    try:
        from ..makine.uyari_yoneticisi import uyari_yoneticisi
        
        # Uyarıyı göster
        basarili = uyari_yoneticisi.uyari_goster(request.mesaj, request.sure)
        
        if basarili:
            return {"status": "success", "message": f"Uyarı gösterildi: {request.mesaj}", "sure": request.sure}
        else:
            return {"status": "error", "message": "Uyarı gösterilemedi"}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı hatası: {str(e)}"}

@app.get("/api/uyari-durumu")
async def uyari_durumu():
    """Uyarı durumunu döndürür"""
    try:
        from ..makine.uyari_yoneticisi import uyari_yoneticisi
        durum = uyari_yoneticisi.uyari_durumu()
        return {"status": "success", "uyari_durumu": durum}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı durumu hatası: {str(e)}"}

@app.post("/api/uyari-kapat")
async def uyari_kapat():
    """Aktif uyarıyı kapatır"""
    try:
        from ..makine.uyari_yoneticisi import uyari_yoneticisi
        basarili = uyari_yoneticisi.uyari_kapat()
        if basarili:
            return {"status": "success", "message": "Uyarı kapatıldı"}
        else:
            return {"status": "error", "message": "Uyarı kapatılamadı"}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı kapatma hatası: {str(e)}"}

@app.post("/api/sistem-reset")
async def sistem_reset():
    """Portları kapatıp yeniden port araması yapar"""
    try:
        motor = kart_referanslari.motor_al()
        sensor = kart_referanslari.sensor_al()
        
        # Kartları durdur
        if motor:
            motor.dinlemeyi_durdur()
        if sensor:
            sensor.dinlemeyi_durdur()
        
        # Kısa bekleme
        import time
        time.sleep(1)
        
        # Port yöneticisi ile yeniden ara
        from ..makine.seri.port_yonetici import KartHaberlesmeServis
        from ..makine.seri.sensor_karti import SensorKart
        from ..makine.seri.motor_karti import MotorKart
        
        yonetici = KartHaberlesmeServis()
        basarili, mesaj, portlar = yonetici.baglan()
        
        if basarili and "sensor" in portlar and "motor" in portlar:
            # Yeni kartları oluştur
            yeni_sensor = SensorKart(portlar["sensor"], cihaz_adi="sensor")
            yeni_sensor.dinlemeyi_baslat()
            
            yeni_motor = MotorKart(portlar["motor"], cihaz_adi="motor")
            yeni_motor.dinlemeyi_baslat()
            
            # Referansları güncelle
            kart_referanslari.motor_referansini_ayarla(yeni_motor)
            kart_referanslari.sensor_referansini_ayarla(yeni_sensor)
            
            # Kısa bekleme sonrası motorları aktif et
            time.sleep(0.5)
            yeni_motor.motorlari_aktif_et()
            time.sleep(0.2)
            yeni_motor.parametre_gonder()  # Hız parametrelerini gönder
            
            return {"status": "success", "message": "Sistem başarıyla resetlendi, portlar yeniden bağlandı ve motorlar aktif edildi"}
        else:
            return {"status": "error", "message": f"Port bulunamadı: {mesaj}"}
            
    except Exception as e:
        return {"status": "error", "message": f"Reset hatası: {str(e)}"}

class AlarmRequest(BaseModel):
    alarmCode: int
    alarmMessage: str

@app.post("/api/alarm-gonder")
async def alarm_gonder(request: AlarmRequest):
    """DİM DB'ye alarm bildirimi gönderir"""
    try:
        await istemci.send_alarm(request.alarmCode, request.alarmMessage)
        return {"status": "success", "message": f"Alarm gönderildi: {request.alarmMessage}"}
    except Exception as e:
        return {"status": "error", "message": f"Alarm gönderme hatası: {str(e)}"}

# --- SENSÖR KARTI API ENDPOINT'LERİ ---

@app.post("/api/sensor/led-ac")
async def sensor_led_ac():
    """Sensör LED'ini açar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.led_ac()
        return {"status": "success", "message": "LED açıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/led-kapat")
async def sensor_led_kapat():
    """Sensör LED'ini kapatır"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.led_kapat()
        return {"status": "success", "message": "LED kapatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/loadcell-olc")
async def sensor_loadcell_olc():
    """Loadcell ölçümü yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.loadcell_olc()
        return {"status": "success", "message": "Loadcell ölçümü başlatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/teach")
async def sensor_teach():
    """Gyro sensör teach yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.teach()
        return {"status": "success", "message": "Gyro sensör teach başlatıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/tare")
async def sensor_tare():
    """Loadcell tare (sıfırlama) yapar"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.tare()
        return {"status": "success", "message": "Loadcell tare yapıldı"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/sensor/agirlik-olc")
async def sensor_agirlik_olc():
    """Loadcell ağırlık ölçümü yapar - gsi, gso komutlarını gönderir"""
    try:
        sensor = kart_referanslari.sensor_al()
        if not sensor:
            return {"status": "error", "message": "Sensör bağlantısı yok"}
        
        # Sensör portuna erişim
        if not sensor.seri_port or not sensor.seri_port.is_open:
            return {"status": "error", "message": "Sensör portu açık değil"}
        
        import time
        
        # Seri port buffer'ını temizle
        sensor.seri_port.reset_input_buffer()
        time.sleep(0.1)
        
        # gsi komutu gönder (ağırlık ölçüm başlat)
        sensor.seri_port.write(b"gsi\n")
        sensor.seri_port.flush()
        time.sleep(0.1)
        
        # gso komutu gönder (ağırlık ölçüm oku)
        sensor.seri_port.write(b"gso\n")
        sensor.seri_port.flush()
        time.sleep(0.3)
        
        # Gelen tüm mesajları oku
        mesajlar = []
        max_tries = 30
        for i in range(max_tries):
            if sensor.seri_port.in_waiting > 0:
                try:
                    line = sensor.seri_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        mesajlar.append(line)
                        print(f"[SENSOR API] Ağırlık mesajı [{i}]: {line}")
                        # "a:" mesajını bulduk mu?
                        if line.startswith("a:"):
                            # Biraz daha bekle başka mesaj var mı diye
                            time.sleep(0.1)
                            # Kalan mesajları da oku
                            while sensor.seri_port.in_waiting > 0:
                                extra_line = sensor.seri_port.readline().decode('utf-8', errors='ignore').strip()
                                if extra_line:
                                    mesajlar.append(extra_line)
                                    print(f"[SENSOR API] Ek mesaj: {extra_line}")
                            break
                except Exception as read_error:
                    print(f"[SENSOR API] Okuma hatası: {read_error}")
            time.sleep(0.05)
        
        print(f"[SENSOR API] Toplam {len(mesajlar)} mesaj alındı: {mesajlar}")
        
        # Mesajları döndür, JavaScript tarafında parse edilecek
        return {
            "status": "success", 
            "mesajlar": mesajlar,
            "message": f"{len(mesajlar)} mesaj alındı"
        }
    except Exception as e:
        import traceback
        print(f"[SENSOR API] Hata detayı: {traceback.format_exc()}")
        return {"status": "error", "message": f"Ağırlık ölçüm hatası: {str(e)}"}

@app.post("/api/sensor-card/reset")
async def sensor_card_reset():
    """Sensör kartını resetler"""
    sensor = kart_referanslari.sensor_al()
    if sensor:
        sensor.reset()
        return {"status": "success", "message": "Sensör kartı resetlendi"}
    return {"status": "error", "message": "Sensör bağlantısı yok"}

@app.post("/api/motor-card/reset")
async def motor_card_reset():
    """Motor kartını resetler"""
    motor = kart_referanslari.motor_al()
    if motor:
        motor.reset()
        return {"status": "success", "message": "Motor kartı resetlendi"}
    return {"status": "error", "message": "Motor bağlantısı yok"}

class MotorHizRequest(BaseModel):
    motor: str
    hiz: int

@app.post("/api/motor/hiz-ayarla")
async def motor_hiz_ayarla(request: MotorHizRequest):
    """Motor hızını ayarlar"""
    try:
        motor = kart_referanslari.motor_al()
        if not motor:
            return {"status": "error", "message": "Motor bağlantısı yok"}
        
        # Hız değerini ters çevir (gömülü sistem ters çalışıyor: düşük değer = hızlı)
        ters_hiz = 100 - request.hiz
        
        # Motor hızını ayarla
        if request.motor == "konveyor":
            motor.konveyor_hiz_ayarla(ters_hiz)
        elif request.motor == "yonlendirici":
            motor.yonlendirici_hiz_ayarla(ters_hiz)
        elif request.motor == "klape":
            motor.klape_hiz_ayarla(ters_hiz)
        else:
            return {"status": "error", "message": "Geçersiz motor adı"}
        
        return {"status": "success", "message": f"{request.motor} motor hızı {request.hiz}% olarak ayarlandı"}
    except Exception as e:
        return {"status": "error", "message": f"Hız ayarlama hatası: {str(e)}"}

# Global sensör değerleri
sensor_son_deger = {"agirlik": 0, "mesaj": "Henüz ölçüm yapılmadı"}

def sensor_callback(mesaj):
    """Sensör kartından gelen mesajları işler"""
    global sensor_son_deger
    #print(f"[SENSOR CALLBACK] Gelen mesaj: {mesaj}")
    
    # Mesajı kaydet
    sensor_son_deger["mesaj"] = mesaj
    
    # Ağırlık değerini parse et - farklı formatları destekle
    #import re
    
    # Format 1: "a:262.62" veya "a:-1.79" gibigit
    #if mesaj.startswith("a:"):
    #    try:
    #        agirlik_str = mesaj.replace("a:", "").strip()
    #        sensor_son_deger["agirlik"] = float(agirlik_str)
            #print(f"[SENSOR] Ağırlık parse edildi: {sensor_son_deger['agirlik']} gram")
    #    except ValueError:
            #print(f"[SENSOR] Ağırlık parse hatası: {mesaj}")
    
    # Format 2: "loadcell" veya "gr" içeren mesajlar
    #elif "loadcell" in mesaj.lower() or "gr" in mesaj.lower():
    #    sayilar = re.findall(r'-?\d+\.?\d*', mesaj)
    #    if sayilar:
     #       sensor_son_deger["agirlik"] = float(sayilar[0])
            #print(f"[SENSOR] Ağırlık parse edildi: {sensor_son_deger['agirlik']} gram")

@app.get("/api/sensor/son-deger")
async def sensor_son_deger_getir():
    """Sensörden gelen son değeri döndürür"""
    return {"status": "success", "data": sensor_son_deger}

# Sensör referansını ayarla fonksiyonunu güncelle
def sensor_referansi_callback_ile_ayarla(sensor_instance):
    """Sensör referansını callback ile birlikte ayarlar"""
    sensor_instance.callback = sensor_callback
    kart_referanslari.sensor_referansini_ayarla(sensor_instance)

